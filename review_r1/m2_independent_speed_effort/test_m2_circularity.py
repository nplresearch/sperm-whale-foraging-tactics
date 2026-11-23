"""M2: the matched-speed contrast must be tested against the label it is built from."""

import numpy as np
import pandas as pd
from circularity import adjusted_ratio, binned_contrast

from common import RESULTS, needs_steward


def _synthetic(true_b_speed_gain: float, n=4000, seed=0):
    """Labels built on vertical speed, speed = vertical / sin(pitch) as in production."""
    rng = np.random.default_rng(seed)
    pitch = rng.uniform(30, 80, n)
    vz = rng.lognormal(np.log(1.0), 0.45, n)
    is_b = vz > 1.1                                   # label defined on vertical speed
    speed = vz / np.sin(np.radians(pitch)) * np.where(is_b, true_b_speed_gain, 1.0)
    return pd.DataFrame({
        "buzz_type": np.where(is_b, "B", "A"), "speed": speed, "abs_vz": vz,
        "buzz_abs_pitch_deg": pitch, "individual_id": rng.integers(0, 20, n)})


def test_label_built_on_vertical_speed_gives_spurious_speed_gap():
    r = adjusted_ratio(_synthetic(1.0))
    assert r["pitch_only"]["B_over_A"] > 1.3                      # looks like a finding...
    assert abs(r["pitch_and_vertical_speed"]["B_over_A"] - 1.0) < 0.03   # ...but is not


def test_control_does_not_hide_a_real_speed_difference():
    r = adjusted_ratio(_synthetic(1.5))                           # B truly 50 % faster
    assert abs(r["pitch_and_vertical_speed"]["B_over_A"] - 1.5) < 0.05


def test_binned_contrast_shapes():
    out = binned_contrast(_synthetic(1.0), n_bins=4)
    assert len(out) == 4 and {"median_A", "median_B", "ratio_B_A"} <= set(out.columns)


@needs_steward
def test_released_data_ratio_vanishes_once_vertical_speed_is_matched():
    adj = pd.read_csv(RESULTS / "m2_circularity_adjusted_30.csv").set_index("model")
    assert adj.loc["pitch_only", "B_over_A"] > 1.5
    row = adj.loc["pitch_and_vertical_speed"]
    assert row.ci_low < 1.0 < row.ci_high
