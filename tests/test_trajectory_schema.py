import pandas as pd
import pytest

from scripts.export_safe_trajectory_data import sanitize
from trajectory.schema import validate_trajectories


def valid_table():
    return pd.DataFrame(
        {
            "trajectory_id": ["D01"] * 3,
            "individual_id": ["W01"] * 3,
            "dive_id": ["D01"] * 3,
            "time_s": [0.0, 1.0, 2.0],
            "x_m": [0.0, 1.0, 2.0],
            "y_m": [0.0, 0.0, 0.0],
            "z_m": [0.0, 0.0, 0.0],
        }
    )


def test_schema_sorts_and_rejects_nonmonotonic_time():
    assert list(validate_trajectories(valid_table().iloc[::-1]).time_s) == [0.0, 1.0, 2.0]
    bad = valid_table()
    bad.loc[2, "time_s"] = 1
    with pytest.raises(ValueError):
        validate_trajectories(bad)


def test_sanitizer_rejects_raw_columns_and_paths():
    bad = valid_table()
    bad["audio_file"] = "recording.wav"
    with pytest.raises(ValueError):
        sanitize(bad)
    bad = valid_table()
    bad["note"] = "/private/source/file"
    with pytest.raises(ValueError):
        sanitize(bad)
