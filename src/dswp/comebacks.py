"""Spatial-recurrence analysis from coarse reconstructed trajectories.

The manuscript's current comeback result was produced from 20-s subsamples of
the constant-speed deployment reconstruction. This module preserves that
result-producing calculation so it can be audited independently of raw tag
data. See ``docs/known_issues.md`` before interpreting the output: the current
SI describes different distance thresholds and the archived forest plot used
an earlier version of the A/B labels.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from statsmodels.stats.contingency_tables import StratifiedTable, Table2x2


DEFAULT_CLOSE_M = 50.0
DEFAULT_FAR_M = 150.0
DEFAULT_EVENT_GAP_S = 120.0
DEFAULT_DEEP_M = 200.0
DEFAULT_CONTEXT_BUFFER_S = 120.0


def load_coarse_reconstruction(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load one numeric-only, deployment-scale reconstruction archive."""
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != {"time_s", "xyz_m"}:
            raise ValueError(f"{path}: expected numeric members time_s and xyz_m")
        time_s = archive["time_s"].astype(float, copy=False)
        xyz_m = archive["xyz_m"].astype(float, copy=False)
    if (
        time_s.ndim != 1
        or xyz_m.ndim != 2
        or xyz_m.shape != (len(time_s), 3)
        or len(time_s) < 2
        or not np.isfinite(time_s).all()
        or not np.isfinite(xyz_m).all()
        or np.any(np.diff(time_s) <= 0)
    ):
        raise ValueError(f"{path}: invalid coarse reconstructed trajectory")
    return time_s, xyz_m


def find_matched_comeback_points(
    xyz_m: np.ndarray,
    *,
    close_m: float = DEFAULT_CLOSE_M,
    far_m: float = DEFAULT_FAR_M,
    dimensions: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Pair each return with its most recent qualifying reference point.

    A sample is a return when it lies within ``close_m`` of an earlier sample
    and the intervening path moved more than ``far_m`` away from the return
    location. The most recent qualifying earlier sample is used. Endpoints and
    unmatched samples are not altered.
    """
    xyz = np.asarray(xyz_m, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or dimensions not in (2, 3):
        raise ValueError("xyz_m must have shape (n, 3); dimensions must be 2 or 3")
    if close_m <= 0 or far_m <= close_m:
        raise ValueError("require 0 < close_m < far_m")
    values = xyz[:, :dimensions]
    returns: list[int] = []
    references: list[int] = []
    for current_index in range(1, len(values)):
        current = values[current_index][None, :]
        distances = cdist(current, values[:current_index]).ravel()
        candidates = np.where(distances <= close_m)[0]
        for reference_index in candidates[::-1]:
            intermediate = values[reference_index + 1 : current_index]
            if len(intermediate) and np.max(cdist(current, intermediate)) > far_m:
                returns.append(current_index)
                references.append(int(reference_index))
                break
    return np.asarray(returns, dtype=int), np.asarray(references, dtype=int)


def group_comeback_events(
    deployment_id: str,
    time_s: np.ndarray,
    xyz_m: np.ndarray,
    comeback_indices: np.ndarray,
    *,
    event_gap_s: float = DEFAULT_EVENT_GAP_S,
) -> pd.DataFrame:
    """Group nearby return samples into recurrence events."""
    indices = np.asarray(comeback_indices, dtype=int)
    if not len(indices):
        return pd.DataFrame(
            columns=[
                "deployment_id",
                "event_order",
                "event_start_s",
                "event_end_s",
                "event_center_s",
                "event_depth_median_m",
            ]
        )
    groups = np.split(
        indices,
        np.where(np.diff(time_s[indices]) > event_gap_s)[0] + 1,
    )
    rows = []
    for event_order, group in enumerate(groups, 1):
        rows.append(
            {
                "deployment_id": deployment_id,
                "event_order": event_order,
                "event_start_s": float(time_s[group[0]]),
                "event_end_s": float(time_s[group[-1]]),
                "event_center_s": float(np.median(time_s[group])),
                "event_depth_median_m": float(np.median(xyz_m[group, 2])),
            }
        )
    return pd.DataFrame(rows)


def detect_comeback_events(index_csv: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detect recurrence events in every released coarse deployment path.

    Returns an event table and one deployment-level summary row per available
    reconstruction. The defaults exactly encode the result-producing notebook:
    a 3-D 50/150-m return criterion and 120-s event grouping.
    """
    index_path = Path(index_csv)
    index = pd.read_csv(index_path)
    required = {"deployment_id", "file", "subsample_interval_s"}
    if missing := required - set(index):
        raise ValueError("comeback index is missing: " + ", ".join(sorted(missing)))
    event_tables = []
    summaries = []
    for row in index.sort_values("deployment_id").itertuples(index=False):
        time_s, xyz_m = load_coarse_reconstruction(index_path.parent / row.file)
        returns, references = find_matched_comeback_points(xyz_m)
        events = group_comeback_events(row.deployment_id, time_s, xyz_m, returns)
        event_tables.append(events)
        summaries.append(
            {
                "deployment_id": row.deployment_id,
                "n_samples": int(len(xyz_m)),
                "n_comeback_samples": int(len(returns)),
                "n_reference_samples": int(len(references)),
                "comeback_ratio": float(len(returns) / len(xyz_m)),
                "n_events": int(len(events)),
            }
        )
    nonempty_events = [table for table in event_tables if not table.empty]
    event_table = (
        pd.concat(nonempty_events, ignore_index=True)
        if nonempty_events
        else pd.DataFrame()
    )
    if not event_table.empty:
        event_table.insert(
            0,
            "comeback_event_id",
            [f"C{number:04d}" for number in range(1, len(event_table) + 1)],
        )
    return event_table, pd.DataFrame(summaries)


def attach_comeback_context(
    buzzes: pd.DataFrame,
    comeback_events: pd.DataFrame,
    *,
    deep_m: float = DEFAULT_DEEP_M,
    buffer_s: float = DEFAULT_CONTEXT_BUFFER_S,
) -> pd.DataFrame:
    """Flag buzz starts falling within buffered deep-recurrence intervals."""
    required_buzz = {"event_id", "deployment_id", "deployment_buzz_start_s"}
    required_event = {
        "deployment_id",
        "event_start_s",
        "event_end_s",
        "event_depth_median_m",
    }
    if missing := required_buzz - set(buzzes):
        raise ValueError("buzzes are missing: " + ", ".join(sorted(missing)))
    if missing := required_event - set(comeback_events):
        raise ValueError("comeback events are missing: " + ", ".join(sorted(missing)))
    intervals = {
        deployment_id: group[["event_start_s", "event_end_s"]].to_numpy(float)
        for deployment_id, group in comeback_events[
            comeback_events["event_depth_median_m"] > deep_m
        ].groupby("deployment_id")
    }
    context = []
    for row in buzzes.itertuples(index=False):
        windows = intervals.get(row.deployment_id, np.empty((0, 2)))
        time = float(row.deployment_buzz_start_s)
        context.append(
            bool(
                len(windows)
                and np.any(
                    (time >= windows[:, 0] - buffer_s)
                    & (time <= windows[:, 1] + buffer_s)
                )
            )
        )
    return buzzes.assign(deep_comeback_context=context)


def stratified_comeback_association(
    events: pd.DataFrame,
    *,
    label_col: str = "buzz_type",
    context_col: str = "deep_comeback_context",
) -> tuple[pd.DataFrame, dict]:
    """Cochran--Mantel--Haenszel association stratified by deployment."""
    required = {"deployment_id", label_col, context_col}
    if missing := required - set(events):
        raise ValueError("events are missing: " + ", ".join(sorted(missing)))
    rows = []
    tables = []
    for deployment_id, group in events[
        events[label_col].isin(["A", "B"])
    ].groupby("deployment_id", sort=True):
        table = (
            pd.crosstab(group[context_col].astype(bool), group[label_col])
            .reindex(index=[True, False], columns=["A", "B"], fill_value=0)
        )
        if table.iloc[0].sum() == 0 or table.iloc[1].sum() == 0:
            continue
        values = table.to_numpy(dtype=float)
        tables.append(values)
        adjusted = Table2x2(values + 0.5)
        ci_low, ci_high = adjusted.oddsratio_confint()
        rows.append(
            {
                "deployment_id": deployment_id,
                "near_A": int(values[0, 0]),
                "near_B": int(values[0, 1]),
                "away_A": int(values[1, 0]),
                "away_B": int(values[1, 1]),
                "n": int(values.sum()),
                "odds_ratio_corrected": float(adjusted.oddsratio),
                "ci_low_corrected": float(ci_low),
                "ci_high_corrected": float(ci_high),
            }
        )
    if not tables:
        raise ValueError("no deployment contains classified buzzes both near and away")
    model = StratifiedTable(np.stack(tables, axis=2))
    ci_low, ci_high = model.oddsratio_pooled_confint()
    summary = {
        "n_deployments": int(len(tables)),
        "n_buzzes": int(sum(row["n"] for row in rows)),
        "pooled_odds_ratio": float(model.oddsratio_pooled),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "p_value": float(model.test_null_odds().pvalue),
        "homogeneity_p_value": float(model.test_equal_odds().pvalue),
    }
    return pd.DataFrame(rows), summary
