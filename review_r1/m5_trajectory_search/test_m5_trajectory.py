"""M5: known-answer tests for heading-based steps and discrete step-duration models."""

import numpy as np
from trajectory.heading_steps import (
    block_headings,
    fit_discrete_powerlaw,
    fit_geometric,
    fit_geometric_mixture,
    turn_run_lengths,
)


def test_straight_track_has_no_turns():
    t = np.arange(0, 600, 0.04)
    xyz = np.column_stack([t, 0 * t, 0 * t])
    h, _ = block_headings(xyz, 25.0, 5.0)
    assert turn_run_lengths(h, np.radians(30)).size == 0


def test_depth_wobble_alone_never_creates_heading_turns():
    """The 25-Hz rule's flaw: vertical flips counted as turns. Heading ignores z."""
    t = np.arange(0, 600, 0.04)
    xyz = np.column_stack([t, 0 * t, 0.02 * np.sin(2 * np.pi * t / 5)])
    h, _ = block_headings(xyz, 25.0, 5.0)
    assert turn_run_lengths(h, np.radians(30)).size == 0


def test_known_turn_schedule_is_recovered():
    headings = np.repeat(np.radians([0, 90, 0, 90, 0, 90, 0]), [4, 6, 4, 6, 4, 6, 4])
    assert list(turn_run_lengths(headings, np.radians(30))) == [6, 4, 6, 4, 6]  # first/last runs censored


def test_mixture_beats_power_law_on_two_mode_data_and_vice_versa():
    rng = np.random.default_rng(1)
    two_mode = np.concatenate([rng.geometric(0.6, 700), 20 + rng.geometric(0.05, 300)])
    pl = np.floor((1 - rng.random(1000)) ** (-1 / 1.0)).astype(int)    # discrete Pareto, mu ~ 2
    for data, mixture_should_win in ((two_mode, True),):
        aic_mix = fit_geometric_mixture(data, 1)["aic"]
        aic_pl = fit_discrete_powerlaw(data, 1)["aic"]
        assert (aic_mix < aic_pl) == mixture_should_win
    assert fit_discrete_powerlaw(pl, 1)["aic"] < fit_geometric(pl, 1)["aic"]


def test_powerlaw_mle_recovers_exponent():
    rng = np.random.default_rng(2)
    x = np.floor(rng.pareto(1.0, 20000) + 1).astype(int)       # P(k) ~ k^-2 for large k
    assert abs(fit_discrete_powerlaw(x, 3)["mu"] - 2.0) < 0.15
