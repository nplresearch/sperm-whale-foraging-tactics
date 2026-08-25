"""Publication-safe reproduction of the Azores validation analyses.

The four CC0 MATLAB files remain external, checksummed inputs.  This module
loads them locally, reproduces the manuscript-facing derived statistics, and
exports only event-level derived values and aggregate results.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import urllib.request

import numpy as np
import pandas as pd
from scipy.stats import (
    chi2_contingency,
    linregress,
    mannwhitneyu,
    rankdata,
    spearmanr,
)

DRYAD_DOI = "10.5061/dryad.tqjq2bvwg"
DRYAD_LANDING_PAGE = "https://doi.org/10.5061/dryad.tqjq2bvwg"
LICENSE = "CC0 1.0 (Dryad data-publication terms)"
CITATION = ("Tonnesen, P. (2020). The long-range echo scene of the sperm whale biosonar "
            "[Dataset]. Dryad. https://doi.org/10.5061/dryad.tqjq2bvwg")

AZORES_FILES = {
    "sw17_196a_buzz.mat": {
        "dryad_file_id": 353942,
        "size_bytes": 1_067_871,
        "sha256": "d62e28bd05bfb7c9d1ede1f973c5716268e57d3ee0993db7f5824ea7428954a2",
        "matlab_key": "buzz",
    },
    "sw17_196a_data.mat": {
        "dryad_file_id": 353943,
        "size_bytes": 5_417_537,
        "sha256": "8cd541c121e667bb77ff988c332929bd520c47cedf5d3e270acf3921d006e004",
        "matlab_key": "whale",
    },
    "sw17_196a_dive.mat": {
        "dryad_file_id": 353944,
        "size_bytes": 17_962_135,
        "sha256": "64d3215e9371f0be5f4d45cfd1ec08420a4d6ce36d41f40a360b8918383f7ce6",
        "matlab_key": "diving",
    },
    "sw17_196a_echo.mat": {
        "dryad_file_id": 353941,
        "size_bytes": 1_867_939,
        "sha256": "e1791fb944c9d9a43f5f69e8ca1170c90b968d3aaaafaff5a23a40b6cbe2ebcf",
        "matlab_key": "echo",
    },
}

DAYTIME_DIVES = frozenset(range(1, 12))
PREY_WINDOW_S = 10.0
PRE_BUZZ_WINDOW_S = 10.0
POST_BUZZ_WINDOW_S = 10.0
RAMP_WINDOW_S = 0.30
RAMP_STEP_S = 0.05
RAMP_SMOOTH_WINDOWS = 5
RAMP_THRESHOLD = 0.70
PAUSE_BOUNDS_S = (1.3, 3.4, 6.0)
PAUSE_LABELS = ("Short", "Medium", "Long", "Very long")


def source_manifest() -> pd.DataFrame:
    """Return the pinned four-file manifest from Dryad version 1."""
    return pd.DataFrame(
        [
            {"filename": filename, **metadata}
            for filename, metadata in AZORES_FILES.items()
        ]
    )


def fetch_azores_file(url: str, destination: str | Path, sha256: str | None = None) -> Path:
    """Download a named file from the authoritative Dryad record with optional checksum.

    URLs are deliberately supplied by the caller after inspecting Dryad's current
    API/landing-page file list: this avoids silently pinning a brittle CDN URL.
    """
    target = Path(destination); target.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, target)
    if sha256:
        got = hashlib.sha256(target.read_bytes()).hexdigest()
        if got != sha256: target.unlink(missing_ok=True); raise ValueError("Azores checksum mismatch")
    return target


def validate_azores_sources(directory: str | Path) -> pd.DataFrame:
    """Verify the four manually retrieved Dryad files byte-for-byte."""
    directory = Path(directory)
    rows = []
    for filename, expected in AZORES_FILES.items():
        path = directory / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing required Dryad file: {path}")
        size = path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if size != expected["size_bytes"] or digest != expected["sha256"]:
            raise ValueError(
                f"Dryad source mismatch for {filename}: "
                f"size={size}, sha256={digest}"
            )
        rows.append(
            {
                "filename": filename,
                "size_bytes": size,
                "sha256": digest,
                "validated": True,
            }
        )
    return pd.DataFrame(rows)


def find_azores_source_directory(
    repository_root: str | Path,
    *,
    explicit: str | Path | None = None,
) -> Path:
    """Locate a complete, checksummed Azores source directory.

    The public MATLAB inputs remain outside version control. An explicit path
    is authoritative; otherwise, search the documented local-data directory
    and the adjacent analysis checkout used to assemble this release.
    """
    repository_root = Path(repository_root).expanduser().resolve()
    if explicit is not None:
        source = Path(explicit).expanduser().resolve()
        validate_azores_sources(source)
        return source

    candidates = (
        repository_root / "local-data" / "azores",
        repository_root.parent / "repo" / "Clean_notebooks_figures" / "Azores_code",
    )
    searched: list[Path] = []
    for source in candidates:
        source = source.resolve()
        if source in searched:
            continue
        searched.append(source)
        if all((source / filename).is_file() for filename in AZORES_FILES):
            validate_azores_sources(source)
            return source

    locations = "\n".join(f"- {source}" for source in searched)
    raise FileNotFoundError(
        "Could not find a complete Azores source directory. Set "
        "CETI_AZORES_SOURCE or place the four files in local-data/azores. "
        f"Searched:\n{locations}"
    )


def _plain_value(value):
    """Convert MATLAB values without flattening scientific array fields."""
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return value.item()
    return value


def load_mat_struct_table(
    path: str | Path,
    *,
    key: str,
) -> pd.DataFrame:
    """Load one named MATLAB struct array into a DataFrame.

    Array-valued fields remain NumPy arrays in object columns. This reader is
    intentionally narrow: it rejects unexpected top-level objects instead of
    guessing which variable a file contains.
    """
    from scipy.io import loadmat

    contents = loadmat(path, squeeze_me=True, struct_as_record=False)
    if key not in contents:
        public_keys = sorted(name for name in contents if not name.startswith("__"))
        raise KeyError(
            f"Expected MATLAB variable {key!r}; found {public_keys}"
        )
    value = contents[key]
    items = np.atleast_1d(value).ravel()
    rows = []
    for item in items:
        fields = getattr(item, "_fieldnames", None)
        if fields is None:
            raise TypeError(f"{key!r} is not a MATLAB struct array")
        rows.append(
            {field: _plain_value(getattr(item, field)) for field in fields}
        )
    return pd.DataFrame(rows)


def load_azores_sources(directory: str | Path) -> dict[str, pd.DataFrame]:
    """Validate and load the four authoritative Azores source tables."""
    validate_azores_sources(directory)
    directory = Path(directory)
    return {
        metadata["matlab_key"]: load_mat_struct_table(
            directory / filename,
            key=metadata["matlab_key"],
        )
        for filename, metadata in AZORES_FILES.items()
    }


def find_plateau_phase(
    clicks: np.ndarray,
    *,
    window_size: float = RAMP_WINDOW_S,
    window_step: float = RAMP_STEP_S,
    smooth_window: int = RAMP_SMOOTH_WINDOWS,
    threshold: float = RAMP_THRESHOLD,
) -> tuple[float, int]:
    """Return plateau-onset time and the number of above-threshold regions.

    This is the sliding-window implementation used by the supplied Azores
    scripts.  The threshold is a fraction of the smoothed rate range.
    """
    clicks = np.sort(np.asarray(clicks, dtype=float))
    if clicks.size < 2:
        return float(clicks[0]), 0
    start, end = float(clicks[0]), float(clicks[-1])
    starts = np.arange(start, end, window_step)
    if starts.size == 0:
        return start, 1
    rates = np.asarray(
        [np.count_nonzero((clicks >= value) & (clicks < value + window_size)) / window_size
         for value in starts],
        dtype=float,
    )
    if smooth_window > 1 and rates.size >= smooth_window:
        rates = np.convolve(rates, np.ones(smooth_window) / smooth_window, mode="same")
    rate_threshold = float(rates.min() + threshold * (rates.max() - rates.min()))
    above = np.flatnonzero(rates >= rate_threshold)
    if above.size == 0:
        return start, 0
    return float(max(starts[above[0]], start)), int(1 + np.count_nonzero(np.diff(above) > 2))


def mean_absolute_vertical_speed(
    depths: np.ndarray,
    sample_rate_hz: float,
    *,
    smooth_window: int = 3,
) -> float:
    """Return the script's smoothed mean absolute pressure-derived speed."""
    depths = np.asarray(depths, dtype=float)
    if depths.size < 2:
        return float("nan")
    speed = np.abs(np.diff(depths) * sample_rate_hz)
    if smooth_window > 1 and speed.size >= smooth_window:
        speed = np.convolve(speed, np.ones(smooth_window) / smooth_window, mode="same")
    return float(np.nanmean(speed))


def extract_azores_buzz_features(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Derive ramp-up and pressure-speed features for the 11 daytime dives."""
    buzzes = sources["buzz"]
    dives = sources["diving"]
    records: list[dict[str, float | int]] = []
    for dive_index, dive in dives.iterrows():
        dive_no = dive_index + 1
        if dive_no not in DAYTIME_DIVES:
            continue
        dive_start = float(dive["dive_start"])
        depths = np.asarray(dive["depth_data"], dtype=float)
        sample_rate_hz = float(dive["depth_fs"])
        dive_buzzes = buzzes.loc[buzzes["dive_no"] == dive_no].reset_index(drop=True)
        for buzz_index, buzz in dive_buzzes.iterrows():
            clicks = np.asarray(buzz["CLbz"], dtype=float)
            if clicks.size < 2:
                continue
            plateau_start, n_plateau = find_plateau_phase(clicks)
            start, end = float(clicks[0]), float(clicks[-1])
            first_index = int(np.clip((start - dive_start) * sample_rate_hz, 0, len(depths) - 1))
            last_index = int(np.clip((end - dive_start) * sample_rate_hz, 0, len(depths) - 1))
            last_index = min(max(last_index, first_index + 1), len(depths) - 1)
            records.append(
                {
                    "dive_no": dive_no,
                    "buzz_no_in_dive": buzz_index + 1,
                    "ramp_up_duration_s": plateau_start - start,
                    "buzz_duration_s": end - start,
                    "avg_vertical_speed_m_s": mean_absolute_vertical_speed(
                        depths[first_index : last_index + 1], sample_rate_hz
                    ),
                    "n_plateau_regions": n_plateau,
                    # Retained in memory for joining the echo and pause tables;
                    # intentionally omitted from public derived exports.
                    "_buzz_start_s": float(buzz["start"]),
                    "_buzz_end_s": float(buzz["end"]),
                    "_click_first_s": start,
                    "_click_last_s": end,
                }
            )
    features = pd.DataFrame.from_records(records)
    if len(features) != 58:
        raise ValueError(f"Expected 58 daytime buzzes; found {len(features)}")
    features["ramp_rank"] = (rankdata(features["ramp_up_duration_s"]) - 1) / (len(features) - 1)
    features["speed_rank"] = (rankdata(features["avg_vertical_speed_m_s"]) - 1) / (len(features) - 1)
    features["distance_to_a"] = np.hypot(features["ramp_rank"], features["speed_rank"])
    features["distance_to_b"] = np.hypot(1 - features["ramp_rank"], 1 - features["speed_rank"])
    return features


def classify_nearest_corners(features: pd.DataFrame, n_per_corner: int = 29) -> pd.DataFrame:
    """Apply the final Azores extreme-corner rule in two-dimensional rank space.

    Candidate Type A and Type B events are the ``n_per_corner`` observations
    nearest the lower-left and upper-right corners, respectively.  Events
    exactly equidistant from the two corners are boundary ties and remain
    unclassified instead of receiving an arbitrary precedence rule.  For the
    58 daytime buzzes and ``n_per_corner=29``, this yields 28 Type A, 28 Type B,
    and two boundary ties, matching the final manuscript analysis.
    """
    labelled = features.copy()
    tied = np.isclose(labelled["distance_to_a"], labelled["distance_to_b"])
    a_index = labelled.nsmallest(n_per_corner, "distance_to_a").index
    b_index = labelled.nsmallest(n_per_corner, "distance_to_b").index
    tie_index = labelled.index[tied]
    a_index = a_index.difference(tie_index)
    b_index = b_index.difference(tie_index)
    overlap = a_index.intersection(b_index)
    if len(overlap):
        raise ValueError("Nearest-corner selections overlap after boundary ties are removed")
    labelled["operative_type"] = "unclassified"
    labelled.loc[a_index, "operative_type"] = "A"
    labelled.loc[b_index, "operative_type"] = "B"
    labelled["nearest_corner_tie"] = tied
    return labelled


def classify_balanced_assignment(features: pd.DataFrame, n_per_type: int = 29) -> pd.DataFrame:
    """Assign disjoint A/B sets that minimise total nearest-corner distance.

    With all 58 daytime buzzes assigned, the exact balanced solution assigns A
    to the ``n_per_type`` smallest values of ``distance_to_a - distance_to_b``.
    It is a sensitivity analysis, not the manuscript's operative result.
    """
    if len(features) != 2 * n_per_type:
        raise ValueError("Balanced assignment requires exactly twice n_per_type observations")
    labelled = features.copy()
    a_index = (labelled["distance_to_a"] - labelled["distance_to_b"]).nsmallest(n_per_type).index
    labelled["balanced_type"] = "B"
    labelled.loc[a_index, "balanced_type"] = "A"
    return labelled


def _echo_metrics_for_features(
    features: pd.DataFrame,
    echo: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the scripts' echo metrics from the full buzz-plus-margin window."""
    records = []
    for _, row in features.iterrows():
        echo_row = echo.iloc[int(row["dive_no"]) - 1]
        prey_times = np.asarray(echo_row["prey_midtime"], dtype=float)
        prey_distance = np.asarray(echo_row["prey_dist"], dtype=float)
        prey_depth = np.asarray(echo_row["prey_depth"], dtype=float)
        mask = (prey_times >= row["_buzz_start_s"] - PREY_WINDOW_S) & (
            prey_times <= row["_buzz_end_s"] + PREY_WINDOW_S
        )
        count = int(np.count_nonzero(mask))
        records.append(
            {
                "dive_no": int(row["dive_no"]),
                "buzz_no_in_dive": int(row["buzz_no_in_dive"]),
                "prey_echo_count": count,
                "nearest_prey_range_m": float(np.min(prey_distance[mask])) if count else np.nan,
                "mean_prey_depth_m": float(np.mean(prey_depth[mask])) if count else np.nan,
            }
        )
    return pd.DataFrame.from_records(records)


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    pooled_variance = ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1)) / (
        len(a) + len(b) - 2
    )
    return float((np.mean(a) - np.mean(b)) / np.sqrt(pooled_variance))


def _contrast_table(events: pd.DataFrame, label_column: str) -> pd.DataFrame:
    """Calculate manuscript-facing Mann--Whitney and effect-size contrasts."""
    rows = []
    for metric in ("prey_echo_count", "nearest_prey_range_m", "mean_prey_depth_m"):
        a = events.loc[events[label_column] == "A", metric].dropna().to_numpy()
        b = events.loc[events[label_column] == "B", metric].dropna().to_numpy()
        statistic, p_value = mannwhitneyu(a, b, alternative="two-sided")
        rows.append(
            {
                "classification": label_column.removesuffix("_type"),
                "metric": metric,
                "n_a": len(a),
                "n_b": len(b),
                "median_a": float(np.median(a)),
                "median_b": float(np.median(b)),
                "mann_whitney_u": float(statistic),
                "p_value": float(p_value),
                "cohens_d_a_minus_b": _cohens_d(a, b),
            }
        )
    return pd.DataFrame.from_records(rows)


def _robustness_table(features: pd.DataFrame, echo_metrics: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the reported corner-size and threshold-free sensitivities."""
    joined = features.merge(echo_metrics, on=["dive_no", "buzz_no_in_dive"], validate="one_to_one")
    rows = []
    for n_per_corner in (20, 25, 29):
        labels = classify_nearest_corners(features, n_per_corner)
        subset = joined[["dive_no", "buzz_no_in_dive", "prey_echo_count", "mean_prey_depth_m"]].merge(
            labels[["dive_no", "buzz_no_in_dive", "operative_type"]],
            on=["dive_no", "buzz_no_in_dive"],
            validate="one_to_one",
        )
        a_depth = subset.loc[subset["operative_type"] == "A", "mean_prey_depth_m"].dropna()
        b_depth = subset.loc[subset["operative_type"] == "B", "mean_prey_depth_m"].dropna()
        a_count = subset.loc[subset["operative_type"] == "A", "prey_echo_count"]
        b_count = subset.loc[subset["operative_type"] == "B", "prey_echo_count"]
        rows.extend(
            [
                {
                    "analysis": "corner_split",
                    "n_per_corner": n_per_corner,
                    "metric": "mean_prey_depth_m",
                    "estimate": float(mannwhitneyu(a_depth, b_depth, alternative="two-sided").statistic),
                    "p_value": float(mannwhitneyu(a_depth, b_depth, alternative="two-sided").pvalue),
                },
                {
                    "analysis": "corner_split",
                    "n_per_corner": n_per_corner,
                    "metric": "prey_echo_count",
                    "estimate": float(mannwhitneyu(a_count, b_count, alternative="two-sided").statistic),
                    "p_value": float(mannwhitneyu(a_count, b_count, alternative="two-sided").pvalue),
                },
            ]
        )
    for metric in ("prey_echo_count", "mean_prey_depth_m"):
        valid = joined[["ramp_rank", "speed_rank", metric]].dropna()
        result = spearmanr(valid["ramp_rank"] + valid["speed_rank"], valid[metric])
        rows.append(
            {
                "analysis": "continuous_diagonal_rank",
                "n_per_corner": np.nan,
                "metric": metric,
                "estimate": float(result.statistic),
                "p_value": float(result.pvalue),
            }
        )
    return pd.DataFrame.from_records(rows)


def _signed_pre_buzz_speed(features: pd.DataFrame, dives: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, event in features.iterrows():
        dive = dives.iloc[int(event["dive_no"]) - 1]
        depths = np.asarray(dive["depth_data"], dtype=float)
        sample_rate_hz = float(dive["depth_fs"])
        start_index = int(max(0, (event["_buzz_start_s"] - PRE_BUZZ_WINDOW_S - dive["dive_start"]) * sample_rate_hz))
        end_index = int(min(len(depths) - 1, (event["_buzz_start_s"] - dive["dive_start"]) * sample_rate_hz))
        segment = depths[start_index : end_index + 1]
        speed = np.diff(segment) * sample_rate_hz
        if speed.size >= 3:
            speed = np.convolve(speed, np.ones(3) / 3, mode="same")
        rows.append(
            {
                "dive_no": int(event["dive_no"]),
                "buzz_no_in_dive": int(event["buzz_no_in_dive"]),
                "pre_buzz_vertical_speed_m_s": float(np.nanmean(speed)),
            }
        )
    return pd.DataFrame.from_records(rows)


def _pause_categories(features: pd.DataFrame, whale: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, event in features.iterrows():
        regular_clicks = np.asarray(whale.iloc[int(event["dive_no"]) - 1]["CLreg"], dtype=float)
        after = regular_clicks[regular_clicks > event["_buzz_end_s"]]
        pause_s = float(after[0] - event["_buzz_end_s"]) if after.size else np.nan
        if not np.isfinite(pause_s) or pause_s >= 120:
            category = "terminal"
        else:
            category = PAUSE_LABELS[int(np.searchsorted(PAUSE_BOUNDS_S, pause_s, side="left"))]
        rows.append(
            {
                "dive_no": int(event["dive_no"]),
                "buzz_no_in_dive": int(event["buzz_no_in_dive"]),
                "post_buzz_pause_s": pause_s if category != "terminal" else np.nan,
                "pause_category": category,
            }
        )
    return pd.DataFrame.from_records(rows)


def _transition_counts(sequences: list[list[str]]) -> dict[str, dict[str, int]]:
    counts = {"S": {"A": 0, "B": 0}, "A": {"A": 0, "B": 0, "E": 0}, "B": {"A": 0, "B": 0, "E": 0}}
    for sequence in sequences:
        if not sequence:
            continue
        counts["S"][sequence[0]] += 1
        for before, after in zip(sequence, sequence[1:]):
            counts[before][after] += 1
        counts[sequence[-1]]["E"] += 1
    return counts


def _transition_probabilities(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    return {
        start: {end: value / sum(destinations.values()) for end, value in destinations.items()}
        for start, destinations in counts.items()
    }


def _markov_table(features: pd.DataFrame, n_boot: int, random_seed: int = 42) -> pd.DataFrame:
    sequences = [
        group.sort_values("buzz_no_in_dive").loc[
            lambda table: table["operative_type"].isin(["A", "B"]), "operative_type"
        ].tolist()
        for _, group in features.groupby("dive_no", sort=True)
    ]
    sequences = [sequence for sequence in sequences if sequence]
    counts = _transition_counts(sequences)
    point = _transition_probabilities(counts)
    draws: dict[tuple[str, str], list[float]] = {
        (start, end): [] for start, destinations in counts.items() for end in destinations
    }
    rng = np.random.default_rng(random_seed)
    for _ in range(n_boot):
        sampled = [sequences[index] for index in rng.integers(0, len(sequences), len(sequences))]
        probabilities = _transition_probabilities(_transition_counts(sampled))
        for (start, end), values in draws.items():
            values.append(probabilities[start][end])
    return pd.DataFrame(
        [
            {
                "from_state": start,
                "to_state": end,
                "count": counts[start][end],
                "probability": point[start][end],
                "ci_low": float(np.percentile(draws[start, end], 2.5)),
                "ci_high": float(np.percentile(draws[start, end], 97.5)),
            }
            for start, destinations in counts.items()
            for end in destinations
        ]
    )


def _vertical_geometry(features: pd.DataFrame, dives: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, event in features.iterrows():
        dive = dives.iloc[int(event["dive_no"]) - 1]
        depths = np.asarray(dive["depth_data"], dtype=float)
        sample_rate_hz = float(dive["depth_fs"])

        def slope(start_s: float, end_s: float) -> float:
            start = int(np.clip(round((start_s - dive["dive_start"]) * sample_rate_hz), 0, len(depths)))
            end = int(np.clip(round((end_s - dive["dive_start"]) * sample_rate_hz), 0, len(depths)))
            if end - start < 2:
                return float("nan")
            return float(linregress(np.arange(end - start) / sample_rate_hz, depths[start:end]).slope)

        before = slope(event["_click_first_s"] - PRE_BUZZ_WINDOW_S, event["_click_first_s"])
        after = slope(event["_click_last_s"], event["_click_last_s"] + POST_BUZZ_WINDOW_S)
        if not np.isfinite(before) or not np.isfinite(after):
            geometry = "unavailable"
        elif before >= 0 and after >= 0:
            geometry = "DD"
        elif before >= 0 and after < 0:
            geometry = "DU"
        elif before < 0 and after >= 0:
            geometry = "UD"
        else:
            geometry = "UU"
        rows.append(
            {
                "dive_no": int(event["dive_no"]),
                "buzz_no_in_dive": int(event["buzz_no_in_dive"]),
                "vertical_geometry": geometry,
                "geometry_group": (
                    "oscillatory" if geometry in {"DU", "UD"}
                    else "persistent" if geometry in {"DD", "UU"}
                    else "unavailable"
                ),
            }
        )
    return pd.DataFrame.from_records(rows)


def _pause_summary(events: pd.DataFrame) -> dict[str, float | int]:
    classified = events.loc[events["operative_type"].isin(["A", "B"]) & (events["pause_category"] != "terminal")]
    contingency = pd.crosstab(classified["operative_type"], classified["pause_category"]).reindex(
        index=["A", "B"], columns=PAUSE_LABELS, fill_value=0
    )
    statistic, p_value, dof, _ = chi2_contingency(contingency)
    return {
        "chi_square": float(statistic),
        "p_value": float(p_value),
        "dof": int(dof),
        "n_a": int((classified["operative_type"] == "A").sum()),
        "n_b": int((classified["operative_type"] == "B").sum()),
    }


def run_azores_validation(
    directory: str | Path,
    output_directory: str | Path | None = None,
    *,
    n_boot: int = 2_000,
) -> dict[str, object]:
    """Reproduce the main and supplementary Azores numerical analyses.

    ``directory`` must contain validated, locally retrieved MATLAB files.  If
    ``output_directory`` is provided, only publication-safe derived CSV/JSON
    products are written; raw MATLAB arrays and absolute timestamps are never
    exported.
    """
    sources = load_azores_sources(directory)
    features = classify_balanced_assignment(classify_nearest_corners(extract_azores_buzz_features(sources)))
    echo_metrics = _echo_metrics_for_features(features, sources["echo"])
    events = features.merge(echo_metrics, on=["dive_no", "buzz_no_in_dive"], validate="one_to_one")
    events = events.merge(_signed_pre_buzz_speed(events, sources["diving"]), on=["dive_no", "buzz_no_in_dive"], validate="one_to_one")
    events = events.merge(_pause_categories(events, sources["whale"]), on=["dive_no", "buzz_no_in_dive"], validate="one_to_one")
    events = events.merge(_vertical_geometry(events, sources["diving"]), on=["dive_no", "buzz_no_in_dive"], validate="one_to_one")
    operative = _contrast_table(events, "operative_type")
    balanced = _contrast_table(events, "balanced_type")
    robustness = _robustness_table(features, echo_metrics)
    markov = _markov_table(events, n_boot=n_boot)
    pre_a = events.loc[events["operative_type"] == "A", "pre_buzz_vertical_speed_m_s"]
    pre_b = events.loc[events["operative_type"] == "B", "pre_buzz_vertical_speed_m_s"]
    pre_test = mannwhitneyu(pre_a, pre_b, alternative="two-sided")
    geometry = (
        events.loc[events["operative_type"].isin(["A", "B"])]
        .groupby(["operative_type", "geometry_group"], observed=True)
        .size()
        .rename("n")
        .reset_index()
    )
    geometry["proportion"] = geometry["n"] / geometry.groupby("operative_type")["n"].transform("sum")
    summary: dict[str, object] = {
        "n_dives": int(len(sources["diving"])),
        "n_buzzes": int(len(sources["buzz"])),
        "n_daytime_dives": len(DAYTIME_DIVES),
        "n_daytime_buzzes": int(len(events)),
        "operative_counts": events["operative_type"].value_counts().sort_index().to_dict(),
        "nearest_corner_ties": int(events["nearest_corner_tie"].sum()),
        "balanced_counts": events["balanced_type"].value_counts().sort_index().to_dict(),
        "pre_buzz_vertical_speed": {
            "mean_a_m_s": float(pre_a.mean()),
            "mean_b_m_s": float(pre_b.mean()),
            "mann_whitney_u": float(pre_test.statistic),
            "p_value": float(pre_test.pvalue),
        },
        "pause_test": _pause_summary(events),
    }
    if output_directory is not None:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        public_columns = [
            "dive_no", "buzz_no_in_dive", "ramp_up_duration_s", "buzz_duration_s",
            "avg_vertical_speed_m_s", "n_plateau_regions", "ramp_rank", "speed_rank",
            "distance_to_a", "distance_to_b", "operative_type", "nearest_corner_tie",
            "balanced_type", "prey_echo_count", "nearest_prey_range_m", "mean_prey_depth_m",
            "pre_buzz_vertical_speed_m_s", "post_buzz_pause_s", "pause_category",
            "vertical_geometry", "geometry_group",
        ]
        events[public_columns].to_csv(output / "azores_derived_buzz_metrics.csv", index=False)
        pd.concat([operative, balanced], ignore_index=True).to_csv(output / "azores_prey_contrasts.csv", index=False)
        robustness.to_csv(output / "azores_robustness.csv", index=False)
        markov.to_csv(output / "azores_markov_transitions.csv", index=False)
        geometry.to_csv(output / "azores_vertical_geometry.csv", index=False)
        (output / "azores_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return {
        "events": events,
        "operative_contrasts": operative,
        "balanced_contrasts": balanced,
        "robustness": robustness,
        "markov": markov,
        "geometry": geometry,
        "summary": summary,
    }
