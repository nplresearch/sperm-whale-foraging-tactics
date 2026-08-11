"""CETI 2024 validation using publication-safe, buzz-level derived data only.

This module deliberately has no reader for tag archives, audio, or raw sensor
streams.  It accepts a small table of per-buzz summaries and produces the
corner-classification, kinematic comparisons, and within-dive sequence summary.
"""
from __future__ import annotations

from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

FEATURE_COLUMNS = [
    "unit_id", "dive_id", "buzz_order_in_dive", "has_kinematics", "n_clicks",
    "buzz_duration_s", "ramp_up_duration_s", "median_click_rate_hz",
    "max_click_rate_hz", "depth_mean_m", "depth_max_dive_m", "speed_3d_mps",
    "vertical_speed_mps", "roll_speed_radps", "pre_buzz_vertical_speed_mps",
    "post_buzz_pause_s", "vertical_direction_before", "vertical_direction_after",
    "straightness_before_10m", "straightness_after_10m",
    "straightness_before_20m", "straightness_after_20m", "time_to_next_buzz_s",
    "path_to_next_buzz_m",
]

# This is intentionally conservative: no source identifiers, timestamps, locations,
# raw-stream samples, demographics, or arbitrary extra columns are allowed.
FORBIDDEN_NAME = re.compile(r"audio|wav|pressure|imu|acceler|magnet|gps|latitude|longitude|"
                            r"tag_id|whale|animal|name|sex|age|date|time_abs|start_time|"
                            r"end_time|path$|filepath|source_file|raw", re.I)


def _sequential_tokens(values: pd.Series, prefix: str) -> pd.Series:
    """Replace source labels with release-local sequential pseudonyms.

    Unsalted hashes are inappropriate here: source deployment labels follow a
    small, predictable namespace and could be recovered by enumeration.
    Sequential labels preserve grouping without retaining a cryptographic
    fingerprint of a source identifier. The private crosswalk is deliberately
    neither returned nor written.
    """
    unique = sorted(values.astype(str).unique())
    width = max(3, len(str(len(unique))))
    mapping = {
        value: f"{prefix}{index:0{width}d}"
        for index, value in enumerate(unique, 1)
    }
    return values.astype(str).map(mapping)


def export_sanitized_ceti2024(source_csv: str | Path, destination_csv: str | Path) -> pd.DataFrame:
    """Make the reviewed CETI publication table from a *derived* legacy CSV.

    The input must be the existing ``ceti2024_buzz_features.csv`` output, not a
    MATLAB/tag archive. Original IDs are replaced with release-local sequential
    labels; absolute buzz clock times are discarded. This function is provided
    for a data steward to run and review locally before adding the resulting CSV.
    """
    src = pd.read_csv(source_csv)
    required = {"tag_id", "dive_number", "buzz_order_in_dive", "has_movement",
                "buzz_duration", "duration_start", "median_click_rate", "max_click_rate",
                "max_depth_dive", "avg_depth", "avg_speed_3d_hybrid",
                "avg_vertical_speed", "avg_roll_speed_total", "pre_buzz_vvel",
                "post_buzz_pause", "vsign_before", "vsign_after",
                "straightness_before_10m", "straightness_after_10m",
                "straightness_before_20m", "straightness_after_20m", "interbuzz_dt",
                "interbuzz_path3d", "n_clicks"}
    missing = required - set(src.columns)
    if missing:
        raise ValueError(f"Not a recognised derived CETI feature table; missing {sorted(missing)}")
    source_dive = (
        src["tag_id"].astype(str) + "::" + src["dive_number"].astype(str)
    )
    out = pd.DataFrame({
        "unit_id": _sequential_tokens(src["tag_id"], "U"),
        "dive_id": _sequential_tokens(source_dive, "V"),
        "buzz_order_in_dive": src["buzz_order_in_dive"], "has_kinematics": src["has_movement"],
        "n_clicks": src["n_clicks"], "buzz_duration_s": src["buzz_duration"],
        "ramp_up_duration_s": src["duration_start"], "median_click_rate_hz": src["median_click_rate"],
        "max_click_rate_hz": src["max_click_rate"], "depth_mean_m": src["avg_depth"],
        "depth_max_dive_m": src["max_depth_dive"], "speed_3d_mps": src["avg_speed_3d_hybrid"],
        "vertical_speed_mps": src["avg_vertical_speed"], "roll_speed_radps": src["avg_roll_speed_total"],
        "pre_buzz_vertical_speed_mps": src["pre_buzz_vvel"], "post_buzz_pause_s": src["post_buzz_pause"],
        "vertical_direction_before": src["vsign_before"], "vertical_direction_after": src["vsign_after"],
        "straightness_before_10m": src["straightness_before_10m"], "straightness_after_10m": src["straightness_after_10m"],
        "straightness_before_20m": src["straightness_before_20m"], "straightness_after_20m": src["straightness_after_20m"],
        "time_to_next_buzz_s": src["interbuzz_dt"], "path_to_next_buzz_m": src["interbuzz_path3d"],
    })
    validate_publication_table(out)
    destination = Path(destination_csv)
    destination.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(destination, index=False)
    return out


def validate_publication_table(df: pd.DataFrame) -> None:
    """Reject schema drift and obvious sensitive columns before analysis/export."""
    unexpected = set(df.columns) - set(FEATURE_COLUMNS)
    bad = [c for c in df.columns if FORBIDDEN_NAME.search(c)]
    missing = set(FEATURE_COLUMNS) - set(df.columns)
    if unexpected or bad or missing:
        raise ValueError(f"Unsafe/invalid CETI table (unexpected={sorted(unexpected)}, forbidden={bad}, missing={sorted(missing)})")
    if df[["unit_id", "dive_id"]].isna().any().any() or not df["buzz_order_in_dive"].ge(1).all():
        raise ValueError("Opaque IDs and positive within-dive sequence numbers are required.")


def classify_corner(df: pd.DataFrame, n_per_class: int | None = None) -> pd.Series:
    """Classify rank-space extremes: A = short/slow; B = long/fast.

    The smaller CETI data do not support treating a two-component GMM as the
    primary result.  This pre-specified robustness classifier labels only the
    non-overlapping extreme corners; middle observations remain unclassified.
    """
    valid = df.dropna(subset=["ramp_up_duration_s", "speed_3d_mps"]).copy()
    n = len(valid)
    if n < 4:
        raise ValueError("At least four kinematic buzzes are required.")
    n_per_class = n // 2 if n_per_class is None else n_per_class
    r1 = valid["ramp_up_duration_s"].rank(method="average").sub(1).div(n - 1)
    r2 = valid["speed_3d_mps"].rank(method="average").sub(1).div(n - 1)
    a = valid.index[np.argsort(np.hypot(r1, r2))[:n_per_class]]
    b = valid.index[np.argsort(np.hypot(1-r1, 1-r2))[:n_per_class]]
    labels = pd.Series("unclassified", index=df.index, dtype="object")
    labels.loc[a] = "A"; labels.loc[b.difference(a)] = "B"
    return labels


def cliffs_delta(x: pd.Series, y: pd.Series) -> float:
    x, y = x.dropna().to_numpy(), y.dropna().to_numpy()
    return float((np.greater.outer(x, y).sum() - np.less.outer(x, y).sum()) / (len(x) * len(y)))


def kinematic_statistics(df: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    """Unpaired A/B Mann–Whitney summaries for publication-safe derived metrics."""
    metrics = ["speed_3d_mps", "ramp_up_duration_s", "vertical_speed_mps", "roll_speed_radps",
               "depth_mean_m", "median_click_rate_hz", "pre_buzz_vertical_speed_mps", "post_buzz_pause_s",
               "straightness_before_10m", "straightness_before_20m", "straightness_after_20m",
               "time_to_next_buzz_s", "path_to_next_buzz_m"]
    rows = []
    for metric in metrics:
        a, b = df.loc[labels.eq("A"), metric].dropna(), df.loc[labels.eq("B"), metric].dropna()
        if len(a) and len(b):
            rows.append(dict(metric=metric, n_A=len(a), n_B=len(b), median_A=a.median(), median_B=b.median(),
                             p_value=mannwhitneyu(a, b, alternative="two-sided").pvalue,
                             cliffs_delta=cliffs_delta(a, b)))
    return pd.DataFrame(rows)


def sequence_statistics(df: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    """Empirical Start/A/B/End transition probabilities, pooled across dives."""
    transitions = []
    work = df.assign(buzz_type=labels)
    for _, dive in work.sort_values(["dive_id", "buzz_order_in_dive"]).groupby("dive_id", sort=False):
        states = [x for x in dive.buzz_type if x in {"A", "B"}]
        if states:
            transitions.extend(zip(["Start", *states], [*states, "End"]))
    counts = pd.DataFrame(transitions, columns=["from_state", "to_state"]).value_counts().rename("count").reset_index()
    counts["probability"] = counts["count"] / counts.groupby("from_state")["count"].transform("sum")
    return counts.sort_values(["from_state", "to_state"]).reset_index(drop=True)


def write_validation_figures(df: pd.DataFrame, labels: pd.Series, transitions: pd.DataFrame, output_dir: str | Path) -> None:
    """Write the supported publication-style validation figures.

    These figures intentionally use only the safe per-buzz table: rank-space
    clustering, per-buzz kinematic summaries, and a transition-probability
    heatmap.  They do not recreate raw-sensor trace panels.
    """
    import matplotlib.pyplot as plt
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    valid = df.dropna(subset=["ramp_up_duration_s", "speed_3d_mps"]).copy()
    n = len(valid)
    valid["ramp_rank"] = valid["ramp_up_duration_s"].rank(method="average").sub(1).div(n - 1)
    valid["speed_rank"] = valid["speed_3d_mps"].rank(method="average").sub(1).div(n - 1)
    valid["buzz_type"] = labels.loc[valid.index]
    colors = {"A": "#2A92D5", "B": "#D56D2A", "unclassified": "#BBBBBB"}
    fig, ax = plt.subplots(figsize=(5.3, 5.0))
    for label, group in valid.groupby("buzz_type"):
        ax.scatter(group.ramp_rank, group.speed_rank, s=24, alpha=.8, c=colors[label], label=label)
    ax.set(xlabel="Ramp-up duration (rank)", ylabel="Mean 3-D speed (rank)", xlim=(0, 1), ylim=(0, 1))
    ax.legend(frameon=False); fig.tight_layout()
    for suffix in ("png", "pdf"): fig.savefig(out / f"ceti2024_corner_clustering.{suffix}", dpi=250)
    plt.close(fig)

    metrics = [("vertical_speed_mps", "Mean vertical speed (m/s)"),
               ("roll_speed_radps", "Mean roll speed (rad/s)"),
               ("depth_mean_m", "Mean buzz depth (m)")]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7))
    for ax, (metric, title) in zip(axes, metrics):
        data = [df.loc[labels.eq(k), metric].dropna() for k in ("A", "B")]
        ax.boxplot(data, tick_labels=["A", "B"], patch_artist=True,
                   boxprops={"facecolor": "#DDDDDD"}, medianprops={"color": "#222222"})
        ax.set_ylabel(title)
    fig.tight_layout()
    for suffix in ("png", "pdf"): fig.savefig(out / f"ceti2024_kinematics.{suffix}", dpi=250)
    plt.close(fig)

    states = ["Start", "A", "B"]
    targets = ["A", "B", "End"]
    matrix = transitions.pivot(index="from_state", columns="to_state", values="probability").reindex(index=states, columns=targets).fillna(0)
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    im = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    ax.set(xticks=range(len(targets)), xticklabels=targets, yticks=range(len(states)), yticklabels=states,
           xlabel="Next state", ylabel="Current state")
    for i in range(len(states)):
        for j in range(len(targets)): ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center")
    fig.colorbar(im, ax=ax, label="Transition probability"); fig.tight_layout()
    for suffix in ("png", "pdf"): fig.savefig(out / f"ceti2024_sequence.{suffix}", dpi=250)
    plt.close(fig)


def run_ceti2024_validation(data_csv: str | Path, output_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Run all supported CETI checks and write machine-readable result tables."""
    df = pd.read_csv(data_csv); validate_publication_table(df)
    labels = classify_corner(df)
    labelled = df.assign(buzz_type=labels)
    results = {"labels": labelled, "kinematic_statistics": kinematic_statistics(df, labels),
               "sequence_statistics": sequence_statistics(df, labels)}
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    for name, table in results.items(): table.to_csv(out / f"{name}.csv", index=False)
    write_validation_figures(df, labels, results["sequence_statistics"], out)
    (out / "analysis_manifest.json").write_text(json.dumps({"analysis": "CETI 2024 derived buzz validation", "n_buzzes": len(df), "schema": FEATURE_COLUMNS}, indent=2) + "\n")
    return results
