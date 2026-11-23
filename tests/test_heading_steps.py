"""Heading-based steps and discrete step-duration fits."""

import numpy as np

from trajectory.heading_steps import (
    block_headings,
    choose_kmin,
    fit_discrete_powerlaw,
    fit_geometric,
    fit_geometric_mixture,
    turn_run_lengths,
)

FS = 25.0


def _path(headings_deg, seconds_each, speed=0.9, depth_wobble_m=0.02):
    """25-Hz path: constant heading segments, horizontal speed, vertical wobble."""
    xyz, pos = [], np.zeros(3)
    rng = np.random.default_rng(0)
    for h, s in zip(headings_deg, seconds_each):
        for _ in range(int(s * FS)):
            step = speed / FS * np.array([np.sin(np.radians(h)), np.cos(np.radians(h)), 0.0])
            pos = pos + step
            xyz.append(pos + [0, 0, rng.normal(0, depth_wobble_m)])
    return np.array(xyz)


def test_heading_turns_ignore_vertical_wobble_and_recover_segment_durations():
    xyz = _path([0, 90, 30, 200], [40, 25, 60, 30])
    heads, _ = block_headings(xyz, FS, block_s=5.0)
    runs = turn_run_lengths(heads, np.radians(30))
    # Interior segments are 25 s and 60 s: 5 and 12 blocks of 5 s.
    np.testing.assert_array_equal(runs, [5, 12])


def test_discrete_powerlaw_recovers_exponent_and_beats_geometric():
    from scipy.stats import zipf

    k = zipf.rvs(2.2, size=4000, random_state=1)          # exact discrete power law, kmin = 1
    pl = fit_discrete_powerlaw(k, 1)
    assert abs(pl["mu"] - 2.2) < 0.08
    assert pl["aic"] < fit_geometric(k, 1)["aic"]


def test_geometric_mixture_beats_powerlaw_on_two_mode_data():
    rng = np.random.default_rng(2)
    k = np.concatenate([rng.geometric(0.6, 3000), rng.geometric(0.05, 1000)])
    mix = fit_geometric_mixture(k, 1)
    assert mix["aic"] < fit_discrete_powerlaw(k, 1)["aic"]
    assert mix["aic"] < fit_geometric(k, 1)["aic"]
    assert 1 <= choose_kmin(k) <= np.percentile(k, 80)
