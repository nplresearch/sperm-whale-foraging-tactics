"""Validation and loading for publication-safe, derived DSWP buzz tables.

The input is one row per detected buzz. ``deployment_id`` and ``dive_id`` are
opaque, release-specific tokens; do not use names, tag serial numbers, dates,
locations, or raw-sample timestamps.  Kinematic columns are summaries computed
before release from reconstructed trajectories, never sensor streams.
"""
from pathlib import Path
import pandas as pd

ID_COLUMNS = ("deployment_id", "dive_id", "buzz_order_in_dive", "buzz_start_s")
CLASSIFIER_COLUMNS = ("ramp_up_duration_s", "avg_speed_3d_m_s")
OPTIONAL_COLUMNS = (
    "individual_id", "trajectory_id", "event_id", "avg_vertical_speed_m_s",
    "avg_roll_speed_deg_s", "pitch_adaptive_speed_3d_m_s", "avg_depth_m",
    "median_click_rate_hz", "pre_buzz_vertical_velocity_m_s",
    "post_buzz_pause_s", "vertical_direction_before", "vertical_direction_after",
    "deployment_buzz_start_s",
    "straightness_before_20m", "straightness_after_20m", "interbuzz_dt_s",
    "interbuzz_path3d_m", "buzz_end_s", "plateau_start_s", "plateau_end_s",
    "plateau_duration_s", "terminal_duration_s", "buzz_duration_s", "n_clicks",
    "max_click_rate_hz", "buzz_type", "reference_comeback", "comeback_buzz",
    "post_buzz_vertical_velocity_m_s",
)
FORBIDDEN_TOKENS = ("whale", "animal", "name", "latitude", "longitude", "gps", "audio", "wav", "mat", "raw")

def validate_buzz_events(frame: pd.DataFrame, *, require_classifier: bool = True) -> pd.DataFrame:
    """Validate a derived event table and return a copy with stable dtypes.

    The minimal schema needed for sequences is IDs plus ``buzz_start_s``.  The
    classifier additionally needs ramp-up duration and average 3-D speed.
    Values are not imputed: unavailable derived summaries remain missing.
    """
    bad = [c for c in frame.columns if any(x in c.lower() for x in FORBIDDEN_TOKENS)]
    if bad:
        raise ValueError("Input includes prohibited raw/identifying columns: " + ", ".join(bad))
    required = list(ID_COLUMNS) + (list(CLASSIFIER_COLUMNS) if require_classifier else [])
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError("Missing required derived columns: " + ", ".join(missing))
    out = frame.copy()
    for col in ("deployment_id", "dive_id"):
        if out[col].isna().any() or (out[col].astype(str).str.len() == 0).any():
            raise ValueError(f"{col} must be a non-empty opaque release token")
        out[col] = out[col].astype(str)
    for col in set(ID_COLUMNS + CLASSIFIER_COLUMNS + OPTIONAL_COLUMNS).intersection(out.columns):
        if col not in (
            "deployment_id",
            "individual_id",
            "dive_id",
            "trajectory_id",
            "event_id",
            "buzz_type",
            "reference_comeback",
            "comeback_buzz",
        ):
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if (out["buzz_order_in_dive"] < 1).any():
        raise ValueError("buzz_order_in_dive must start at 1")
    return out

def load_buzz_events(path: str | Path, *, require_classifier: bool = True) -> pd.DataFrame:
    """Read a CSV or Parquet derived-event table after safety/schema checks."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    elif path.suffix.lower() in {".parquet", ".pq"}:
        frame = pd.read_parquet(path)
    else:
        raise ValueError("Expected a derived .csv or .parquet table")
    return validate_buzz_events(frame, require_classifier=require_classifier)
