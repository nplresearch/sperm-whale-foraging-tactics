"""M6: the phase check is the guard-rail: transit buzzes must not drive dive-level results."""

import json

import pandas as pd

from common import RESULTS

F = json.loads((RESULTS / "foraging_models.json").read_text())["dswp"]


def test_all_buzz_terminal_effect_disappears_in_the_bottom_phase():
    assert F["D4_terminal_matched"]["is_b"]["odds_ratio"] > 1.8
    bottom = F["P_D4_terminal_bottom_only"]["is_b"]
    assert 0.5 < bottom["odds_ratio"] < 1.5 and bottom["p"] > 0.3


def test_dive_final_type_b_buzzes_are_mostly_on_the_way_up():
    assert F["P_where_last_buzzes_fall"]["B"]["share_in_ascent"] > 0.75


def test_search_coupling_survives_in_bottom_phase_only():
    t = json.loads((RESULTS / "trajectory_tests.json").read_text())
    bottom = t["X_tactic_by_search_phase_bottom_only"]
    assert bottom["odds_ratio_first_vs_within"] < 0.8 and bottom["p"] < 1e-3


def test_transit_buzzes_are_a_small_but_B_rich_minority():
    p = pd.read_csv(RESULTS / "transit_buzz_profile.csv")
    n = p.groupby("phase").n.sum()
    assert 0.10 < (n.ascent + n.descent) / n.sum() < 0.20
    bshare = p[p.buzz_type == "B"].set_index("phase").n / p.groupby("phase").n.sum()
    assert bshare.ascent > bshare.bottom and bshare.descent > bshare.bottom
