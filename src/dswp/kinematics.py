"""Kinematic measures computed directly from 25-Hz depth, pitch and heading.

These replace reconstruction-derived swim speed in the reviewer-1 revision:

* ``ocdr_speed``: observed climb/descent-rate speed, ``-d(depth)/dt / sin(pitch)``,
  averaged over one stroke cycle and reported only where the body is steep
  (default |pitch| >= 45 deg) and the vertical motion agrees with body
  orientation. Elsewhere it is NaN; no constant speed is substituted.
* ``stroke_oscillation``: band-passed (0.1-0.4 Hz) angular oscillation of the
  body-axis direction built from pitch and heading. Dorso-ventral fluke strokes
  rotate the body axis whatever the roll angle, so the measure works at any
  posture, including near-horizontal swimming. It is a relative effort index
  in degrees, not a speed.

Conventions: depth positive downward (m), pitch positive nose-up (deg),
heading in degrees.
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt

STROKE_BAND_HZ = (0.1, 0.4)


def centered_mean(x, n):
    """Centred moving mean over ``n`` samples; NaN unless the window is full."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    kernel = np.ones(int(n))
    total = np.convolve(np.where(ok, x, 0.0), kernel, mode="same")
    count = np.convolve(ok.astype(float), kernel, mode="same")
    out = np.full(len(x), np.nan)
    full = count >= n
    out[full] = total[full] / count[full]
    return out


def ocdr_speed(depth_m, pitch_deg, fs_hz, *, min_pitch_deg=45.0, window_s=5.0):
    """Stroke-cycle-averaged OCDR speed (m/s), NaN where it is not valid."""
    depth = np.asarray(depth_m, float)
    pitch = np.asarray(pitch_deg, float)
    n = max(1, int(round(window_s * fs_hz)))
    rate = centered_mean(np.gradient(depth) * fs_hz, n)
    body = centered_mean(pitch, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        speed = -rate / np.sin(np.radians(body))
        valid = np.isfinite(speed) & (np.abs(body) >= min_pitch_deg) & (speed > 0)
    return np.where(valid, speed, np.nan)


def stroke_oscillation(pitch_deg, heading_deg, fs_hz, *, band_hz=STROKE_BAND_HZ, order=2):
    """Magnitude (deg) of the stroke-band oscillation of the body-axis direction."""
    p = np.radians(np.asarray(pitch_deg, float))
    h = np.radians(np.asarray(heading_deg, float))
    axis = np.column_stack([np.cos(p) * np.sin(h), np.cos(p) * np.cos(h), np.sin(p)])
    bad = ~np.isfinite(axis).all(axis=1)
    if bad.all():
        return np.full(len(p), np.nan)
    if bad.any():
        idx = np.arange(len(p))
        for j in range(3):
            axis[bad, j] = np.interp(idx[bad], idx[~bad], axis[~bad, j])
    sos = butter(order, band_hz, btype="bandpass", fs=fs_hz, output="sos")
    filtered = sosfiltfilt(sos, axis, axis=0)
    out = np.degrees(np.linalg.norm(filtered, axis=1))
    out[bad] = np.nan
    return out
