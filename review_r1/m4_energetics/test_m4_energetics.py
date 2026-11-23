"""M4: known-answer physics checks on the per-buzz energy model, and its failure mode."""

import numpy as np
import pandas as pd
from dswp.energetics import EnergyParameters, energy_from_speed_series

from common import RESULTS

T = np.arange(0, 6, 1 / 25)


def test_constant_speed_has_no_acceleration_work():
    r = energy_from_speed_series(T, np.full(len(T), 1.0))
    assert r["positive_acceleration_work_J"] < 1e-6


def test_drag_work_scales_with_speed_cubed():
    lo = energy_from_speed_series(T, np.full(len(T), 1.0))["drag_work_J"]
    hi = energy_from_speed_series(T, np.full(len(T), 2.0))["drag_work_J"]
    assert 6.5 < hi / lo < 7.5     # v^2.8: v^3 drag times Cd ~ Re^-0.2 (2^2.8 = 6.96)


def test_zero_mean_speed_noise_is_rectified_into_positive_work():
    """Failure mode behind '99 % of work is acceleration': jitter has zero net
    acceleration but max(0, m a v) keeps only the positive half."""
    rng = np.random.default_rng(0)
    steady = np.full(len(T), 0.9)
    noisy = steady + rng.normal(0, 0.15, len(T))
    r0, r1 = energy_from_speed_series(T, steady), energy_from_speed_series(T, noisy)
    assert r1["positive_acceleration_work_J"] > 20 * r1["drag_work_J"]
    assert r1["E_total_J"] > 5 * r0["E_total_J"]


def test_smoothing_removes_the_rectified_noise_work():
    rng = np.random.default_rng(0)
    noisy = 0.9 + rng.normal(0, 0.15, len(T))
    smooth = np.convolve(noisy, np.ones(25) / 25, mode="same")
    a = energy_from_speed_series(T[25:-25], noisy[25:-25])["positive_acceleration_work_J"]
    b = energy_from_speed_series(T[25:-25], smooth[25:-25])["positive_acceleration_work_J"]
    assert b < 0.1 * a


def test_body_mass_rescales_absolute_energy_but_not_the_ratio():
    s = pd.read_csv(RESULTS / "energy_variants_summary.csv")
    s = s[s.quantity == "E_total_J"].set_index("variant")
    assert s.loc["production", "B_MJ"] / s.loc["female_13.5t", "B_MJ"] > 2.5
    assert abs(s.loc["production", "B_over_A"] - s.loc["female_13.5t", "B_over_A"]) < 0.2


def test_default_parameters_are_the_40t_adult_male():
    assert EnergyParameters().body_mass_kg > 30_000     # not a Dominica social-unit whale
