import numpy as np
import pandas as pd

from dswp.trajectory_features import buzz_straightness, straightness_index


def test_straight_line_has_unit_straightness():
    xyz = np.c_[np.arange(20), np.zeros(20), np.zeros(20)]
    assert np.isclose(straightness_index(xyz), 1.0)


def test_buzz_windows_use_release_trajectory(tmp_path):
    directory = tmp_path / "trajectories"
    directory.mkdir()
    xyz = np.c_[np.arange(100) * 0.5, np.zeros(100), np.zeros(100)]
    np.savez_compressed(directory / "T001.npz", xyz_m=xyz)
    pd.DataFrame(
        {
            "trajectory_id": ["T001"],
            "file": ["trajectories/T001.npz"],
            "sampling_rate_hz": [2.0],
        }
    ).to_csv(tmp_path / "trajectory_index.csv", index=False)
    events = pd.DataFrame(
        {
            "event_id": ["B001"],
            "trajectory_id": ["T001"],
            "buzz_start_s": [20.0],
            "buzz_end_s": [21.0],
        }
    )
    result = buzz_straightness(events, tmp_path / "trajectory_index.csv", windows_m=(10,))
    assert np.isclose(result.loc[0, "straightness_before_10m"], 1.0)
    assert np.isclose(result.loc[0, "straightness_after_10m"], 1.0)
