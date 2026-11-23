"""Recover the speed-estimator state from released pitch-adaptive trajectories.

The released ``trajectories/T###.npz`` files are the pitch-adaptive hybrid
dead-reckoning reconstruction (provenance: ``compute_3d_trajectory_hybrid`` in
the original repository). At each 25-Hz step that reconstruction

* sets depth directly from the smoothed pressure record, so ``dz`` is observed;
* uses ``v = |dz/dt / sin(pitch)|`` clipped to [0.1, 5] m/s when
  ``|dz| >= 0.05 m`` and ``|pitch| >= 0.05 rad`` (depth-derived regime);
* otherwise uses the constant fallback ``v = 0.9 m/s``;
* moves horizontally by ``v * dt * cos(pitch)`` (an XY rotation preserves this).

Those rules can be inverted exactly from positions alone, except when
``|pitch| < 0.05`` and ``|dz| >= 0.05``. That case is classified as
depth-derived here and is rare. Nothing here adds information beyond the
release; it exposes how much of each speed series was measured versus assumed.
"""

import numpy as np

FALLBACK, DEPTH, CLIPPED = 0, 1, 2
REGIME_NAMES = {FALLBACK: "fallback", DEPTH: "depth_derived", CLIPPED: "clipped"}


def classify_steps(xyz, *, fs_hz=25.0, fallback_m_s=0.9, dz_threshold_m=0.05, clip_max_m_s=5.0):
    """Return per-step ``(regime, estimator_speed, unclipped_speed)``.

    Arrays have ``len(xyz) - 1`` entries; step ``k`` is ``xyz[k] -> xyz[k + 1]``.
    ``estimator_speed`` is the speed the reconstruction used (0.9, the
    depth-derived value, or the clip). ``unclipped_speed`` equals it except on
    clipped steps, where the pre-clip value is recovered from the pitch implied
    by the horizontal step (``h = clip * dt * cos(pitch)``).
    """
    d = np.diff(np.asarray(xyz, float), axis=0)
    dt = 1.0 / fs_hz
    h = np.hypot(d[:, 0], d[:, 1])
    dz = np.abs(d[:, 2])
    implied = np.hypot(h, dz) / dt

    depth = dz >= dz_threshold_m - 1e-9
    clipped = depth & (implied > clip_max_m_s * (1 + 1e-9))
    regime = np.where(clipped, CLIPPED, np.where(depth, DEPTH, FALLBACK))

    estimator = np.where(depth, implied, fallback_m_s)
    estimator[clipped] = clip_max_m_s
    cos_p = np.clip(h[clipped] / (clip_max_m_s * dt), 0.0, 1.0)
    unclipped = estimator.copy()
    unclipped[clipped] = dz[clipped] / dt / np.sqrt(1.0 - cos_p**2)
    return regime, estimator, unclipped


def rebuild_with_clip(xyz, new_clip_m_s, *, fs_hz=25.0, clip_max_m_s=5.0):
    """Re-integrate horizontal position with a different upper speed clip.

    Only clipped steps change: their horizontal displacement is rescaled by
    ``min(unclipped, new_clip) / clip_max``. Depth is kept exactly.
    ``new_clip_m_s=np.inf`` removes the clip.
    """
    xyz = np.asarray(xyz, float)
    regime, _, unclipped = classify_steps(xyz, fs_hz=fs_hz, clip_max_m_s=clip_max_m_s)
    scale = np.ones(len(regime))
    hit = regime == CLIPPED
    scale[hit] = np.minimum(unclipped[hit], new_clip_m_s) / clip_max_m_s
    steps = np.diff(xyz[:, :2], axis=0) * scale[:, None]
    out = xyz.copy()
    out[1:, :2] = xyz[0, :2] + np.cumsum(steps, axis=0)
    return out
