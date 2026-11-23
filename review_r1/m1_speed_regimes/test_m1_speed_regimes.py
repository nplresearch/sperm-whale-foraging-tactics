"""M1: how much of the released speed series was measured vs assumed?"""

import numpy as np
import pytest

from common import PKG
from dswp.speed_regimes import FALLBACK, classify_steps

TRAJ = PKG / "data/dswp/trajectories"


def test_pure_fallback_track_is_recognised():
    t = np.arange(200) / 25.0
    xyz = np.column_stack([0.9 * t, np.zeros_like(t), np.full_like(t, 100.0)])
    regime, speed, _ = classify_steps(xyz)
    assert (regime == FALLBACK).all() and np.allclose(speed, 0.9)


def test_fast_steps_with_depth_change_are_not_fallback():
    xyz = np.column_stack([np.arange(50) * 0.1, np.zeros(50), np.arange(50) * 0.1])
    regime, speed, _ = classify_steps(xyz)
    assert (regime != FALLBACK).all() and np.allclose(speed, np.hypot(0.1, 0.1) * 25)  # 0.14 m per 40 ms


@pytest.mark.skipif(not (TRAJ / "T001.npz").exists(), reason="released trajectories absent")
def test_released_track_never_moves_faster_than_fallback_on_fallback_steps():
    xyz = np.load(TRAJ / "T001.npz")["xyz_m"]
    regime, _, _ = classify_steps(xyz)
    h = np.hypot(*np.diff(xyz[:, :2], axis=0).T) * 25.0
    assert h[regime == FALLBACK].max() <= 0.9 + 1e-6
