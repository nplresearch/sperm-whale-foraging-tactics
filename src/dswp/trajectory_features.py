"""Buzz-centred features computed from released reconstructed trajectories."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from trajectory.analysis import load_trajectory


def resample_path_spatial(xyz: np.ndarray, step_m: float = 1.0) -> np.ndarray:
    """Linearly resample a 3-D path at approximately constant arc length."""
    xyz = np.asarray(xyz, dtype=float)
    if len(xyz) < 2:
        return xyz
    segment = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    cumulative = np.r_[0.0, np.cumsum(segment)]
    if cumulative[-1] < step_m:
        return np.array([xyz[0], xyz[-1]])
    # Remove repeated arc-length values caused by stationary samples before
    # interpolation; this does not alter the path geometry.
    keep = np.r_[True, np.diff(cumulative) > 0]
    cumulative = cumulative[keep]
    xyz = xyz[keep]
    target = np.linspace(
        0.0, cumulative[-1], int(cumulative[-1] / step_m) + 1
    )
    return np.column_stack(
        [np.interp(target, cumulative, xyz[:, axis]) for axis in range(3)]
    )


def straightness_index(xyz: np.ndarray, step_m: float = 1.0) -> float:
    """Displacement divided by path length after spatial resampling."""
    resampled = resample_path_spatial(xyz, step_m)
    if len(resampled) < 2:
        return np.nan
    path_length = np.linalg.norm(np.diff(resampled, axis=0), axis=1).sum()
    if path_length <= 0:
        return np.nan
    return float(np.linalg.norm(resampled[-1] - resampled[0]) / path_length)


def buzz_straightness(
    events: pd.DataFrame,
    trajectory_index_csv: str | Path,
    *,
    windows_m: tuple[int, ...] = (20, 30, 40),
    resample_step_m: float = 1.0,
) -> pd.DataFrame:
    """Calculate before/after distance-window straightness for each buzz.

    Before windows end at the first click; after windows begin at the last
    click. Acoustic times are relative to the released reconstructed dive.
    """
    required = {
        "event_id",
        "trajectory_id",
        "buzz_start_s",
        "buzz_end_s",
    }
    missing = required - set(events)
    if missing:
        raise ValueError(f"events are missing {sorted(missing)}")
    index_path = Path(trajectory_index_csv)
    metadata = pd.read_csv(index_path).set_index("trajectory_id")
    rows = []
    for trajectory_id, group in events.groupby("trajectory_id", sort=False):
        if trajectory_id not in metadata.index:
            continue
        meta = metadata.loc[trajectory_id]
        fs_hz = float(meta["sampling_rate_hz"])
        xyz = load_trajectory(index_path.parent / meta["file"])
        cumulative = np.r_[
            0.0, np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))
        ]
        for event in group.itertuples(index=False):
            start = max(0, int(float(event.buzz_start_s) * fs_hz))
            end = min(len(xyz) - 1, int(float(event.buzz_end_s) * fs_hz))
            if start >= end:
                continue
            row = {"event_id": event.event_id}
            for window in windows_m:
                before_distance = cumulative[start] - window
                before = (
                    0
                    if before_distance < 0
                    else int(np.searchsorted(cumulative, before_distance))
                )
                after_distance = cumulative[end] + window
                after = (
                    len(xyz) - 1
                    if after_distance > cumulative[-1]
                    else int(np.searchsorted(cumulative, after_distance))
                )
                row[f"straightness_before_{window}m"] = straightness_index(
                    xyz[before : start + 1], resample_step_m
                )
                row[f"straightness_after_{window}m"] = straightness_index(
                    xyz[end : after + 1], resample_step_m
                )
            rows.append(row)
    return pd.DataFrame(rows)
