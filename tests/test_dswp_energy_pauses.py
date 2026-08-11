import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import numpy as np
import pandas as pd
from dswp.aoki import aoki_energy_from_speed_series
from dswp.energetics import (
    energy_from_speed_series,
    event_energy_from_speed_table,
    event_energy_from_trajectories,
)
from dswp.pauses import categorize_pauses, pause_category_table, pause_association

def test_energy_is_finite_for_safe_speed_summary():
    result = energy_from_speed_series([0., .1, .2, .3], [.6, .8, 1.1, 1.2])
    assert result["E_total_J"] > 0 and np.isfinite(result["drag_work_J"])


def test_aoki_cost_is_cubic_in_constant_speed():
    slow = aoki_energy_from_speed_series([0., 1.], [1., 1.])
    fast = aoki_energy_from_speed_series([0., 1.], [2., 2.])
    assert np.isclose(
        fast["aoki_drag_locomotor_energy_J"]
        / slow["aoki_drag_locomotor_energy_J"],
        8.0,
    )

def test_event_energy_groups_opaque_event_keys():
    samples = pd.DataFrame({"deployment_id":["d1"]*3, "dive_id":["v1"]*3,
        "buzz_order_in_dive":[1]*3, "capture_time_s":[0., .1, .2], "speed_3d_m_s":[.5,.8,1.]})
    out = event_energy_from_speed_table(samples)
    assert len(out) == 1 and out.loc[0, "E_total_J"] > 0


def test_event_energy_can_be_rebuilt_from_release_trajectory(tmp_path):
    trajectories = tmp_path / "trajectories"
    trajectories.mkdir()
    xyz = np.c_[np.arange(20) * 0.04, np.zeros(20), np.zeros(20)]
    np.savez_compressed(trajectories / "T001.npz", xyz_m=xyz)
    pd.DataFrame(
        {
            "trajectory_id": ["T001"],
            "file": ["trajectories/T001.npz"],
            "sampling_rate_hz": [25.0],
        }
    ).to_csv(tmp_path / "trajectory_index.csv", index=False)
    events = pd.DataFrame(
        {
            "event_id": ["B001"],
            "trajectory_id": ["T001"],
            "buzz_start_s": [0.08],
            "buzz_end_s": [0.40],
            "buzz_type": ["A"],
        }
    )
    out = event_energy_from_trajectories(
        events, tmp_path / "trajectory_index.csv"
    )
    assert out.loc[0, "event_id"] == "B001"
    assert out.loc[0, "E_total_J"] > 0

def test_pause_edges_and_association():
    assert list(categorize_pauses([1.29, 1.3, 3.4, 6.0, 6.1])) == ["short", "medium", "long", "long", "very_long"]
    events = pd.DataFrame({"buzz_type":["A"]*4+["B"]*4, "post_buzz_pause_s":[4,5,7,8,.2,.3,.5,1.]})
    table = pause_category_table(events)
    assert table["count"].sum() == 8
    assert 0 <= pause_association(events, n_permutations=30, seed=1)["permutation_p"] <= 1
