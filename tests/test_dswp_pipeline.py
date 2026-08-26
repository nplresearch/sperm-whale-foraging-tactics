import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import pandas as pd
import pytest

from dswp.classification import classify_extreme_corners
from dswp.io import validate_buzz_events
from dswp.statistics import (
    depth_mixed_model,
    markov_leave_subset_out,
    markov_with_ci,
    roll_speed_bin_tests,
)


def events():
    return pd.DataFrame(
        {
            "deployment_id": ["d01"] * 4,
            "dive_id": ["v01"] * 4,
            "buzz_order_in_dive": [1, 2, 3, 4],
            "buzz_start_s": [1.0, 2.0, 3.0, 4.0],
            "ramp_up_duration_s": [0.2, 0.4, 2.0, 3.0],
            "avg_speed_3d_m_s": [0.3, 0.5, 1.8, 2.0],
        }
    )


def test_validator_rejects_raw_or_identifying_columns():
    frame = events().assign(raw_audio_path="secret.wav")
    with pytest.raises(ValueError, match="prohibited"):
        validate_buzz_events(frame)


def test_corner_labels_are_disjoint_and_ordered():
    labels = classify_extreme_corners(events(), n_per_class=1)
    assert labels.iloc[0] == "A" and labels.iloc[-1] == "B"
    assert set(labels).issubset({"A", "B", "?"})


def test_markov_counts_dive_sequence():
    frame = events()
    frame["buzz_type"] = ["A", "B", "B", "A"]
    out = markov_with_ci(frame, n_boot=20, seed=3)
    assert out.loc[(out.from_state == "S") & (out.to_state == "A"), "count"].item() == 1
    assert out.loc[(out.from_state == "A") & (out.to_state == "B"), "count"].item() == 1


def test_paper_markov_preserves_ambiguous_buzz_as_gap():
    frame = events()
    frame["individual_id"] = "w01"
    frame["buzz_type"] = ["A", "?", "B", "B"]
    out = markov_leave_subset_out(frame, n_resamples=5, n_exclude_min=0, seed=3)
    lookup = out.set_index(["from_state", "to_state"])
    assert lookup.loc[("S", "A"), "count"] == 1
    assert lookup.loc[("A", "B"), "count"] == 0
    assert lookup.loc[("B", "B"), "count"] == 1
    assert lookup.loc[("B", "E"), "count"] == 1


def test_registered_markov_matches_published_probabilities():
    root = Path(__file__).parents[1]
    from dswp.classification import attach_labels
    from dswp.io import load_buzz_events

    frame = attach_labels(load_buzz_events(root / "data" / "dswp" / "buzz_events.csv"))
    out = markov_leave_subset_out(frame, n_resamples=20, seed=42)
    lookup = out.set_index(["from_state", "to_state"])
    assert lookup.loc[("S", "A"), "probability"] == pytest.approx(0.4573170732)
    assert lookup.loc[("A", "E"), "probability"] == pytest.approx(0.0618556701)
    assert lookup.loc[("B", "E"), "probability"] == pytest.approx(0.1311475410)


def test_registered_depth_model_matches_manuscript():
    root = Path(__file__).parents[1]
    from dswp.classification import attach_labels
    from dswp.io import load_buzz_events

    frame = attach_labels(load_buzz_events(root / "data" / "dswp" / "buzz_events.csv"))
    result = depth_mixed_model(frame)
    assert result["n"] == 2488
    assert result["n_individuals"] == 20
    assert result["n_deployments"] == 32
    assert result["n_dives"] == 226
    assert result["estimate_A_minus_B_m"] == pytest.approx(10.642, abs=0.01)
    assert result["ci_low_m"] == pytest.approx(4.529, abs=0.02)
    assert result["ci_high_m"] == pytest.approx(16.756, abs=0.02)
    assert result["p_value"] == pytest.approx(6.46e-4, rel=0.03)


def test_roll_speed_bin_tests_bonferroni():
    events_frame = pd.DataFrame(
        {
            "event_id": [f"a{i}" for i in range(6)] + [f"b{i}" for i in range(6)],
            "buzz_type": ["A"] * 6 + ["B"] * 6,
        }
    )
    bins = pd.DataFrame(
        {
            "event_id": events_frame["event_id"],
            "time_bin_s": 0.0,
            "roll_speed_deg_s": [0.8, 0.9, 1.0, 1.0, 1.1, 1.2] + [3.8, 3.9, 4.0, 4.0, 4.1, 4.2],
        }
    )
    out = roll_speed_bin_tests(events_frame, bins)
    assert len(out) == 1
    assert out.loc[0, "mean_A_deg_s"] == pytest.approx(1.0)
    assert out.loc[0, "mean_B_deg_s"] == pytest.approx(4.0)
    assert bool(out.loc[0, "significant_0_05"])
