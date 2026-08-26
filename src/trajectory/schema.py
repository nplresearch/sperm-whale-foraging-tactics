"""Validation for publication-safe reconstructed trajectory tables.

This package intentionally has no reader for tag sensor, audio, GPS, or MAT
files.  Its only individual-level input is a derived trajectory table with
reconstructed positions and an optional *derived* buzz-event table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

TRAJECTORY_COLUMNS = ("trajectory_id", "individual_id", "dive_id", "time_s", "x_m", "y_m", "z_m")
OPTIONAL_TRAJECTORY_COLUMNS = ("depth_m", "phase", "reconstruction_method", "sample_interval_s")
BUZZ_COLUMNS = ("trajectory_id", "buzz_time_s", "buzz_type")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# A publication release must not accidentally include operational provenance or
# raw acquisition channels.  These substrings are checked in column names and
# object/string values by the sanitizer.
FORBIDDEN_TOKENS = (
    "audio",
    "hydrophone",
    "wav",
    "flac",
    "mat",
    "imu",
    "acceler",
    "magnet",
    "gyro",
    "pressure_raw",
    "gps",
    "latitude",
    "longitude",
    "filepath",
    "file_path",
    "absolute_path",
    "source_path",
    "serial_number",
)


def assert_safe_identifiers(
    frame: pd.DataFrame, fields=("trajectory_id", "individual_id", "dive_id")
) -> None:
    for field in fields:
        if field in frame:
            bad = ~frame[field].astype(str).str.fullmatch(IDENTIFIER)
            if bad.any():
                raise ValueError(f"{field} contains an unsafe identifier")


def validate_trajectories(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted, validated trajectory table without modifying values."""
    missing = set(TRAJECTORY_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"trajectory table is missing required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("trajectory table is empty")
    assert_safe_identifiers(frame)
    out = frame.copy()
    for col in ("time_s", "x_m", "y_m", "z_m"):
        out[col] = pd.to_numeric(out[col], errors="raise")
    if not out[["time_s", "x_m", "y_m", "z_m"]].apply(lambda x: x.notna().all()).all():
        raise ValueError("trajectory coordinates and times must be finite")
    out = out.sort_values(["trajectory_id", "time_s"], kind="stable").reset_index(drop=True)
    if (out.groupby("trajectory_id")["time_s"].diff().dropna() <= 0).any():
        raise ValueError("time_s must strictly increase within each trajectory")
    return out


def validate_buzzes(frame: pd.DataFrame, trajectories: pd.DataFrame | None = None) -> pd.DataFrame:
    missing = set(BUZZ_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"buzz table is missing required columns: {sorted(missing)}")
    out = frame.copy()
    assert_safe_identifiers(out, ("trajectory_id",))
    out["buzz_time_s"] = pd.to_numeric(out["buzz_time_s"], errors="raise")
    if out["buzz_time_s"].isna().any() or out["buzz_type"].isna().any():
        raise ValueError("buzz rows require a time and classification")
    if trajectories is not None and not set(out.trajectory_id).issubset(
        set(trajectories.trajectory_id)
    ):
        raise ValueError("buzz table refers to unknown trajectory_id values")
    return out.sort_values(["trajectory_id", "buzz_time_s"], kind="stable").reset_index(drop=True)


def is_safe_release_path(path: str | Path) -> bool:
    """True for derived CSV/Parquet data; false for raw-like formats/names."""
    p = Path(path)
    return p.suffix.lower() in {".csv", ".parquet"} and not any(
        t in p.name.lower() for t in FORBIDDEN_TOKENS
    )
