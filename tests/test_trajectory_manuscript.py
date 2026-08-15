import numpy as np
import pandas as pd
from pathlib import Path

from trajectory.manuscript import (
    buzz_centred_msd_by_type,
    buzz_centred_results,
    phase_summary,
    plot_buzz_centred_displacement,
    representative_path,
)


ROOT = Path(__file__).resolve().parents[1]

def test_phase_summary_and_representative(tmp_path):
    t = tmp_path / "T.npz"; np.savez(t, xyz_m=np.c_[np.arange(100.), np.zeros(100), np.arange(100.)])
    index = tmp_path / "index.csv"
    pd.DataFrame([{"trajectory_id":"T1","individual_id":"W1","dive_id":"D1","file":"T.npz","n_samples":100,"sampling_rate_hz":25,"foraging_start_index":10,"foraging_end_index":80,"max_depth_m":700}]).to_csv(index,index=False)
    assert phase_summary(index).iloc[0].foraging_samples == 70
    _, xyz = representative_path(index); assert xyz.shape == (100,3)

def test_buzz_type_boundary():
    result = buzz_centred_msd_by_type(pd.DataFrame({"event_id":["B1"]}))
    assert result["supported"] is False


def test_buzz_centred_results_use_onset_reference_and_paired_individuals(tmp_path):
    fs = 2.0
    n = 60
    index_rows = []
    event_rows = []
    for individual in range(5):
        trajectory_id = f"T{individual}"
        xyz = np.c_[np.arange(n), np.zeros(n), np.zeros(n)]
        np.savez(tmp_path / f"{trajectory_id}.npz", xyz_m=xyz)
        index_rows.append({
            "trajectory_id": trajectory_id,
            "individual_id": f"W{individual}",
            "file": f"{trajectory_id}.npz",
            "sampling_rate_hz": fs,
        })
        for order, ramp in enumerate((0.1, 0.2), 1):
            event_rows.append({
                "event_id": f"B{individual}{order}",
                "trajectory_id": trajectory_id,
                "individual_id": f"W{individual}",
                "buzz_start_s": 15.0,
                "ramp_up_duration_s": ramp,
                "avg_speed_3d_m_s": 1.0 if order == 1 else 3.0,
            })
    pd.DataFrame(index_rows).to_csv(tmp_path / "index.csv", index=False)
    result = buzz_centred_results(
        pd.DataFrame(event_rows), tmp_path / "index.csv", window_s=2, minimum_per_type=1
    )
    assert result["n_individuals"] == 5
    assert not result["paired_tests"].empty
    assert set(result["curves"].buzz_type) == {"A", "B"}
    assert "wilcoxon_p_bonferroni" in result["paired_tests"]


def test_release_reproduces_legacy_buzz_msd_and_exposes_corrected_result():
    events = pd.read_csv(ROOT / "data/dswp/buzz_events.csv")
    labels = pd.read_csv(ROOT / "data/dswp/comeback_legacy_labels.csv")
    index = ROOT / "data/dswp/trajectory_index.csv"
    manuscript = buzz_centred_results(
        events,
        index,
        labels=labels,
        label_column="legacy_buzz_type",
        time_origin="legacy_subtract_dive_start",
    )
    corrected_time_legacy_labels = buzz_centred_results(
        events,
        index,
        labels=labels,
        label_column="legacy_buzz_type",
        time_origin="dive_local",
    )
    corrected = buzz_centred_results(events, index)
    assert manuscript["n_individuals"] == 8
    assert np.allclose(
        manuscript["paired_tests"]["wilcoxon_p"],
        [0.84375, 0.4609375, 0.3125, 0.25, 0.1484375, 0.1484375, 0.3828125, 0.9453125],
    )
    assert corrected_time_legacy_labels["n_individuals"] == 19
    assert corrected_time_legacy_labels["paired_tests"]["wilcoxon_p"].max() < 0.001
    assert corrected["n_individuals"] == 20
    assert corrected["retained_buzz_counts"] == {"A": 1346, "B": 1141}
    assert corrected["paired_tests"]["wilcoxon_p_bonferroni"].max() < 0.001
    assert corrected["paired_tests"]["n_B_gt_A"].min() == 19
    assert corrected["paired_tests"].loc[
        corrected["paired_tests"]["lag_s"] >= 1, "n_B_gt_A"
    ].eq(20).all()
    axes = plot_buzz_centred_displacement(corrected)
    assert len(axes) == 2
    axes[0].figure.clf()
