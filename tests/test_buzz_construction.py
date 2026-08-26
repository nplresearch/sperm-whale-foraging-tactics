from pathlib import Path

import numpy as np
import pandas as pd

from dswp.buzz_thresholds import (
    click_rate_series,
    cohort_summary,
    load_clicks,
    null_window_diagnostic,
    segment_clicks,
    threshold_summary,
    threshold_sweep,
)

ROOT = Path(__file__).resolve().parents[1]


def test_segment_is_deterministic_and_ordered():
    result = segment_clicks(np.array([0.0, 0.2, 0.4, 0.6, 2.0, 2.2]), 0.5)
    assert (
        result["start_s"] <= result["plateau_start_s"] <= result["plateau_end_s"] <= result["end_s"]
    )
    rate = click_rate_series(np.array([0.0, 0.2, 0.4, 0.6, 2.0, 2.2]))
    expected = 0.5 * (rate.rate_hz.max() - rate.rate_hz.min())
    assert np.isclose(result["cutoff_hz"], expected)


def test_click_loader_and_sweep(tmp_path):
    p = tmp_path / "clicks.csv"
    pd.DataFrame(
        {
            "event_id": ["B1", "B1"],
            "click_index": [2, 1],
            "click_time_from_buzz_start_s": [0.2, 0.0],
        }
    ).to_csv(p, index=False)
    clicks = load_clicks(p)
    assert clicks.click_index.tolist() == [1, 2]
    assert len(threshold_sweep(clicks, thresholds=(0.5,))) == 1
    assert {round(x, 2) for x in threshold_sweep(clicks).threshold} == {
        round(x, 2) for x in np.arange(0.05, 1, 0.05)
    }


def test_null_window_changes_ici_membership():
    times = [0.0, 0.1, 0.2, 0.3, 1.0, 1.1, 1.2]
    clicks = pd.DataFrame(
        {
            "event_id": ["B1"] * len(times),
            "click_index": range(1, len(times) + 1),
            "click_time_from_buzz_start_s": times,
        }
    )
    sweep = threshold_sweep(clicks, thresholds=(0.5,))
    nulls = null_window_diagnostic(clicks, thresholds=(0.5,), n_windows=5)
    assert "excess_regularity" in nulls
    assert nulls["median_null_ici_cv"].notna().any()
    assert threshold_summary(sweep, nulls).shape == (1, 7)


def test_rate_rejects_single_click():
    try:
        click_rate_series(np.array([0.0]))
    except ValueError:
        pass
    else:
        raise AssertionError("single click should be rejected")


def test_release_cohort_counts_match_manuscript():
    deployments = pd.read_csv(ROOT / "data/dswp/deployment_summary.csv")
    events = pd.read_csv(ROOT / "data/dswp/buzz_events.csv")
    assert cohort_summary(deployments, events) == {
        "deployments": 34,
        "individuals": 20,
        "dives": 245,
        "buzzes": 3686,
    }
