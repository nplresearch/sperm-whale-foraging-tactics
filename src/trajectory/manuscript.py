"""In-memory manuscript trajectory summaries and figure helpers."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from dswp.classification import classify_gmm
from trajectory.analysis import (
    analyze_release,
    fit_powerlaw,
    load_trajectory,
    loglog_slope,
    msd_curve,
    step_lengths,
)


def pooled_steps(index_csv: str | Path) -> np.ndarray:
    index = pd.read_csv(index_csv)
    values = []
    for row in index.itertuples(index=False):
        if row.max_depth_m < 600:
            continue
        xyz = load_trajectory(Path(index_csv).parent / row.file)
        steps = step_lengths(
            xyz[int(row.foraging_start_index) : int(row.foraging_end_index)]
        )
        if len(steps) >= 30:
            values.append(steps)
    return np.concatenate(values) if values else np.array([], dtype=float)


def manuscript_summary(index_csv: str | Path) -> dict:
    per_dive, population, timescale = analyze_release(index_csv)
    per_individual = per_dive.groupby("individual_id", as_index=False)[
        ["mu", "alpha_msd"]
    ].median()
    steps = pooled_steps(index_csv)
    return {
        "per_dive": per_dive,
        "per_individual": per_individual,
        "timescale": timescale,
        "pooled_fit": fit_powerlaw(steps),
        "pooled_steps": steps,
        "population": population,
        "index_csv": Path(index_csv),
    }


def phase_summary(index_csv: str | Path) -> pd.DataFrame:
    index = pd.read_csv(index_csv)
    out = index[
        [
            "trajectory_id",
            "individual_id",
            "foraging_start_index",
            "foraging_end_index",
            "n_samples",
        ]
    ].copy()
    out["pre_foraging_samples"] = out.foraging_start_index
    out["foraging_samples"] = out.foraging_end_index - out.foraging_start_index
    out["post_foraging_samples"] = out.n_samples - out.foraging_end_index
    return out


def representative_path(
    index_csv: str | Path, trajectory_id: str | None = None
) -> tuple[pd.DataFrame, np.ndarray]:
    index = pd.read_csv(index_csv)
    row = (
        index.iloc[0]
        if trajectory_id is None
        else index[index.trajectory_id == trajectory_id].iloc[0]
    )
    xyz = load_trajectory(Path(index_csv).parent / row.file)
    return row.to_frame().T.reset_index(drop=True), xyz


def surface_threshold_sensitivity(
    index_csv: str | Path,
    thresholds=(5.0, 10.0, 20.0, 30.0, 50.0, 100.0),
) -> pd.DataFrame:
    """Recompute MSD slopes on the longest run deeper than each threshold."""
    index = pd.read_csv(index_csv)
    rows = []
    for row in index.itertuples(index=False):
        xyz = load_trajectory(Path(index_csv).parent / row.file)
        for threshold in thresholds:
            indices = np.flatnonzero(xyz[:, 2] >= threshold)
            groups = np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)
            run = max(groups, key=len) if groups else np.array([], dtype=int)
            if len(run) >= 50:
                rows.append(
                    {
                        "threshold_m": threshold,
                        "trajectory_id": row.trajectory_id,
                        **loglog_slope(
                            msd_curve(
                                xyz[run],
                                fs_hz=row.sampling_rate_hz,
                                max_fraction=0.5,
                            )
                        ),
                    }
                )
    return pd.DataFrame(rows)


def buzz_centred_msd_by_type(
    events: pd.DataFrame,
    labels: pd.DataFrame | None = None,
    *,
    label_column: str | None = None,
) -> dict:
    """Validate inputs and attach registered or explicitly supplied labels."""
    required = {
        "event_id",
        "trajectory_id",
        "individual_id",
        "buzz_start_s",
        "ramp_up_duration_s",
        "avg_speed_3d_m_s",
    }
    if not required.issubset(events.columns):
        return {
            "supported": False,
            "reason": f"missing columns: {sorted(required - set(events))}",
        }
    labelled = events.drop(columns=["buzz_type"], errors="ignore").copy()
    provenance = "registered_gmm"
    if labels is None:
        labelled["buzz_type"] = classify_gmm(labelled)
    else:
        label_column = label_column or (
            "legacy_buzz_type" if "legacy_buzz_type" in labels else "buzz_type"
        )
        required_labels = {"event_id", label_column}
        if not required_labels.issubset(labels):
            return {
                "supported": False,
                "reason": f"label table is missing: {sorted(required_labels - set(labels))}",
            }
        labelled = labelled.merge(
            labels[["event_id", label_column]].rename(columns={label_column: "buzz_type"}),
            on="event_id",
            how="left",
            validate="one_to_one",
        )
        provenance = label_column
    return {"supported": True, "events": labelled, "label_provenance": provenance}


def buzz_centred_results(
    events: pd.DataFrame,
    index_csv: str | Path,
    *,
    labels: pd.DataFrame | None = None,
    label_column: str | None = None,
    time_origin: str = "dive_local",
    window_s: float = 30.0,
    minimum_per_type: int = 5,
) -> dict:
    """Reproduce the SI ensemble MSD and paired per-whale lag tests.

    Squared displacement is measured relative to position at buzz onset over a
    ``+-window_s`` interval. Curves are averaged across buzzes within each
    individual and type; paired Wilcoxon tests compare those individual curves.

    ``time_origin='legacy_subtract_dive_start'`` is a forensic mode for the
    manuscript notebook, which subtracted dive start from already dive-local
    click times. It is retained only to explain the published eight-whale result.
    """
    labelled = buzz_centred_msd_by_type(
        events, labels=labels, label_column=label_column
    )
    if not labelled["supported"]:
        return {**labelled, "curves": pd.DataFrame(), "paired_tests": pd.DataFrame()}
    index_path = Path(index_csv)
    if time_origin not in {"dive_local", "legacy_subtract_dive_start"}:
        raise ValueError("unsupported buzz time origin")
    if (
        time_origin == "legacy_subtract_dive_start"
        and "deployment_buzz_start_s" not in labelled["events"]
    ):
        raise ValueError("legacy time-origin audit requires deployment_buzz_start_s")
    index = pd.read_csv(index_path).set_index("trajectory_id")
    per_individual: dict[str, dict[str, list[np.ndarray]]] = defaultdict(
        lambda: {"A": [], "B": []}
    )
    sampling_rates = set()
    classified = labelled["events"][labelled["events"]["buzz_type"].isin(["A", "B"])]
    for trajectory_id, group in classified.groupby("trajectory_id", sort=False):
        if trajectory_id not in index.index:
            continue
        metadata = index.loc[trajectory_id]
        fs_hz = float(metadata.sampling_rate_hz)
        sampling_rates.add(fs_hz)
        half_window = int(round(window_s * fs_hz))
        xyz = load_trajectory(index_path.parent / metadata.file)
        for event in group.itertuples(index=False):
            center_time_s = float(event.buzz_start_s)
            if time_origin == "legacy_subtract_dive_start":
                inferred_dive_start_s = (
                    float(event.deployment_buzz_start_s) - float(event.buzz_start_s)
                )
                center_time_s -= inferred_dive_start_s
            center = int(round(center_time_s * fs_hz))
            if center - half_window < 0 or center + half_window >= len(xyz):
                continue
            segment = xyz[center - half_window : center + half_window + 1]
            if not np.isfinite(segment).all():
                continue
            displacement_sq = np.sum((segment - segment[half_window]) ** 2, axis=1)
            per_individual[event.individual_id][event.buzz_type].append(displacement_sq)
    if len(sampling_rates) > 1:
        raise ValueError("buzz-centred aggregation requires one common sampling rate")
    if not sampling_rates:
        return {
            "supported": True,
            "curves": pd.DataFrame(),
            "paired_tests": pd.DataFrame(),
            "n_individuals": 0,
        }
    fs_hz = sampling_rates.pop()
    half_window = int(round(window_s * fs_hz))
    lag_axis = np.arange(-half_window, half_window + 1) / fs_hz
    curve_rows = []
    retained = []
    curves = {}
    for individual_id, by_type in sorted(per_individual.items()):
        if min(len(by_type["A"]), len(by_type["B"])) < minimum_per_type:
            continue
        retained.append(individual_id)
        curves[individual_id] = {}
        for buzz_type in ("A", "B"):
            curve = np.mean(np.asarray(by_type[buzz_type]), axis=0)
            curves[individual_id][buzz_type] = curve
            curve_rows.extend(
                {
                    "individual_id": individual_id,
                    "buzz_type": buzz_type,
                    "lag_s": float(lag_s),
                    "msd_m2": float(msd),
                    "n_buzzes": len(by_type[buzz_type]),
                }
                for lag_s, msd in zip(lag_axis, curve)
            )
    test_rows = []
    lag_samples = np.unique(
        np.asarray([1, 5, fs_hz, 2 * fs_hz, 5 * fs_hz, 10 * fs_hz, 20 * fs_hz, 30 * fs_hz], int)
    )
    for lag in lag_samples:
        if lag > half_window or len(retained) < 5:
            continue
        a_values = np.asarray([curves[w]["A"][half_window + lag] for w in retained])
        b_values = np.asarray([curves[w]["B"][half_window + lag] for w in retained])
        p_value = (
            1.0
            if np.allclose(a_values, b_values)
            else float(stats.wilcoxon(a_values, b_values).pvalue)
        )
        test_rows.append(
            {
                "lag_s": float(lag / fs_hz),
                "median_A_m2": float(np.median(a_values)),
                "median_B_m2": float(np.median(b_values)),
                "wilcoxon_p": p_value,
                "n_pairs": len(retained),
            }
        )
    return {
        "supported": True,
        "curves": pd.DataFrame(curve_rows),
        "paired_tests": pd.DataFrame(test_rows),
        "n_individuals": len(retained),
        "minimum_per_type": minimum_per_type,
        "window_s": window_s,
        "label_provenance": labelled["label_provenance"],
        "time_origin": time_origin,
    }


def plot_manuscript_panels(
    summary: dict,
    xyz: np.ndarray,
    surface: pd.DataFrame,
    buzz_msd: dict | None = None,
) -> dict:
    """Create supported manuscript/SI plots in memory; never save files."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    per_dive = summary["per_dive"]
    steps = (
        summary["pooled_steps"]
        if "pooled_steps" in summary
        else pooled_steps(summary["index_csv"])
    )
    if len(steps):
        axes[0, 0].loglog(
            np.sort(steps), np.arange(1, len(steps) + 1)[::-1], ".", ms=2
        )
        axes[0, 0].set_title("Pooled step-length tail")
    axes[0, 1].hist(per_dive["mu"].dropna(), bins=25)
    axes[0, 1].set_title("Dive-level mu")
    axes[0, 2].hist(per_dive["alpha_msd"].dropna(), bins=25)
    axes[0, 2].set_title("Dive-level alpha")
    axes[1, 0].plot(xyz[:, 0], xyz[:, 1], lw=0.4)
    axes[1, 0].set_title("Representative path (top-down projection)")
    if not surface.empty:
        surface.groupby("threshold_m")["alpha_msd"].median().plot(
            ax=axes[1, 1], marker="o"
        )
        axes[1, 1].set_title("Surface-threshold sensitivity")
    if buzz_msd and not buzz_msd["curves"].empty:
        curves = buzz_msd["curves"]
        for buzz_type, color in (("A", "#2A92D5"), ("B", "#D56D2A")):
            selected = curves[curves.buzz_type.eq(buzz_type)]
            for _, group in selected.groupby("individual_id"):
                axes[1, 2].plot(group.lag_s, group.msd_m2, color=color, alpha=0.2, lw=0.5)
            median = selected.groupby("lag_s").msd_m2.median()
            axes[1, 2].plot(median.index, median, color=color, lw=2, label=f"Type {buzz_type}")
        axes[1, 2].set(title="Buzz-centred ensemble MSD", xlabel="Lag from onset (s)", ylabel="MSD (m2)")
        axes[1, 2].legend(frameon=False)
    fig.suptitle("Supported manuscript trajectory panels")
    fig.tight_layout()
    return {"figure": fig, "axes": axes}
