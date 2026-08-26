import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import numpy as np
import pandas as pd

from dswp.comebacks import (
    attach_comeback_context,
    find_matched_comeback_points,
    group_comeback_events,
    stratified_comeback_association,
)


def test_return_detector_uses_recent_qualifying_reference():
    xyz = np.array(
        [
            [0.0, 0.0, 300.0],
            [200.0, 0.0, 300.0],
            [1.0, 0.0, 300.0],
            [220.0, 0.0, 300.0],
            [2.0, 0.0, 300.0],
        ]
    )
    returns, references = find_matched_comeback_points(xyz, close_m=10, far_m=100)
    assert list(returns) == [2, 4]
    assert list(references) == [0, 2]


def test_event_grouping_context_and_cmh():
    time = np.array([0.0, 20.0, 40.0, 200.0])
    xyz = np.c_[np.zeros(4), np.zeros(4), [300, 310, 320, 100]]
    events = group_comeback_events("D001", time, xyz, np.array([0, 1, 2]))
    buzzes = pd.DataFrame(
        {
            "event_id": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"],
            "deployment_id": ["D001"] * 4 + ["D002"] * 4,
            "deployment_buzz_start_s": [10, 500, 20, 600] * 2,
            "buzz_type": ["A", "A", "B", "B", "A", "A", "B", "B"],
        }
    )
    recurrence = pd.concat(
        [events, events.assign(deployment_id="D002")],
        ignore_index=True,
    )
    labelled = attach_comeback_context(buzzes, recurrence, buffer_s=0)
    assert labelled["deep_comeback_context"].tolist() == [
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    ]
    association_rows = []
    for deployment_id, table in (
        ("D001", [[3, 2], [2, 3]]),
        ("D002", [[4, 2], [3, 5]]),
    ):
        for context, counts in zip([True, False], table):
            for buzz_type, count in zip(["A", "B"], counts):
                association_rows.extend(
                    [
                        {
                            "deployment_id": deployment_id,
                            "buzz_type": buzz_type,
                            "deep_comeback_context": context,
                        }
                    ]
                    * count
                )
    strata, summary = stratified_comeback_association(pd.DataFrame(association_rows))
    assert len(strata) == 2
    assert summary["n_buzzes"] == 24
    assert summary["pooled_odds_ratio"] > 1
