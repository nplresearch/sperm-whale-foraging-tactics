"""Speed-regime recovery from released pitch-adaptive reconstructions."""

import numpy as np

from dswp.speed_regimes import CLIPPED, DEPTH, FALLBACK, classify_steps, rebuild_with_clip


def _production_hybrid(depth, pitch, yaw, *, fs=25.0, v0=0.9, dz_thr=0.05, clip=5.0):
    """Copy of repo/Clean_notebooks_figures/utils/trajectories.py
    ``compute_3d_trajectory_hybrid`` (smoothing disabled), the provenance code
    that produced ``data/dswp/trajectories``."""
    n, dt = len(depth), 1.0 / fs
    speed = np.full(n, v0)
    for i in range(1, n):
        dz, p = depth[i] - depth[i - 1], pitch[i - 1]
        if abs(dz) >= dz_thr and abs(p) >= 0.05:
            speed[i] = np.clip(abs(dz / dt / np.sin(p)), 0.1, clip)
    speed[0] = speed[1]
    xyz = np.zeros((n, 3))
    xyz[0, 2] = depth[0]  # released tracks start at the observed depth, not z=0
    for i in range(1, n):
        horiz = speed[i] * dt * np.cos(pitch[i - 1])
        xyz[i, 0] = xyz[i - 1, 0] + horiz * np.sin(yaw[i - 1])
        xyz[i, 1] = xyz[i - 1, 1] + horiz * np.cos(yaw[i - 1])
        xyz[i, 2] = depth[i]
    return xyz, speed


def _synthetic():
    rng = np.random.default_rng(0)
    n = 2000
    pitch = np.concatenate([
        np.full(500, 0.02),            # level: fallback
        np.full(500, -0.9),            # steep descent: depth-derived
        np.full(500, 0.15),            # shallow pitch, fast climb: clipped
        rng.uniform(-1.2, 1.2, 500),   # mixed
    ])
    vz = np.concatenate([
        rng.uniform(0.0, 1.0, 500),
        np.full(500, 1.6),
        np.full(500, -1.4),
        rng.uniform(-2.0, 2.0, 500),
    ])
    yaw = rng.uniform(-np.pi, np.pi, n)
    depth = 500 + np.cumsum(vz) / 25.0
    return depth, pitch, yaw


def test_regimes_and_speeds_recovered_exactly():
    depth, pitch, yaw = _synthetic()
    xyz, speed = _production_hybrid(depth, pitch, yaw)
    regime, est, unclipped = classify_steps(xyz)

    dz = np.abs(np.diff(depth))
    used_depth = (dz >= 0.05) & (np.abs(pitch[:-1]) >= 0.05)
    raw = np.abs(np.diff(depth) * 25.0 / np.sin(pitch[:-1]))
    want = np.where(used_depth, np.where(raw > 5.0, CLIPPED, DEPTH), FALLBACK)

    # The only unidentifiable case: |pitch| < 0.05 with |dz| >= 0.05.
    identifiable = ~((dz >= 0.05) & (np.abs(pitch[:-1]) < 0.05))
    np.testing.assert_array_equal(regime[identifiable], want[identifiable])
    np.testing.assert_allclose(est[identifiable], speed[1:][identifiable], rtol=1e-9)
    clipped = want == CLIPPED
    assert clipped.sum() > 100
    np.testing.assert_allclose(unclipped[clipped], raw[clipped], rtol=1e-6)


def test_rebuild_with_original_clip_is_identity_and_higher_clip_matches_production():
    depth, pitch, yaw = _synthetic()
    xyz5, _ = _production_hybrid(depth, pitch, yaw, clip=5.0)
    xyz9, _ = _production_hybrid(depth, pitch, yaw, clip=9.0)
    np.testing.assert_allclose(rebuild_with_clip(xyz5, 5.0), xyz5, atol=1e-9)
    np.testing.assert_allclose(rebuild_with_clip(xyz5, 9.0), xyz9, atol=1e-6)
