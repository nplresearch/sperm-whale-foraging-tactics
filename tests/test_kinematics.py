"""Direct kinematic measures from 25-Hz depth, pitch and heading."""

import numpy as np

from dswp.kinematics import ocdr_speed, stroke_oscillation

FS = 25.0


def test_ocdr_recovers_speed_on_steep_segments_and_masks_shallow_ones():
    t = np.arange(0, 120, 1 / FS)
    pitch = np.where(t < 60, -60.0, 20.0)        # steep descent, then shallow climb
    pitch = pitch + 3 * np.sin(2 * np.pi * 0.2 * t)  # stroke-induced wobble
    speed = 1.4
    depth = 500 + np.cumsum(-speed * np.sin(np.radians(pitch))) / FS
    v = ocdr_speed(depth, pitch, FS, min_pitch_deg=45.0, window_s=5.0)
    steep = (t > 5) & (t < 55)
    np.testing.assert_allclose(v[steep], speed, rtol=0.02)
    assert np.isnan(v[(t > 65) & (t < 115)]).all()


def test_ocdr_rejects_sign_inconsistent_samples():
    pitch = np.full(1000, -60.0)          # nose down...
    depth = 500 - np.arange(1000) / FS    # ...but rising
    assert np.isnan(ocdr_speed(depth, pitch, FS)).all()


def test_stroke_oscillation_is_roll_invariant_and_recovers_amplitude():
    t = np.arange(0, 300, 1 / FS)
    wobble = 4.0 * np.sin(2 * np.pi * 0.2 * t)            # deg, 0.2 Hz strokes
    slow_turn = 30 * np.sin(2 * np.pi * 0.01 * t)         # maneuvering, out of band
    upright = stroke_oscillation(-10 + wobble, 50 + slow_turn, FS)   # strokes in pitch
    rolled = stroke_oscillation(np.full_like(t, -10.0), 50 + slow_turn + wobble, FS)
    core = slice(int(20 * FS), int(280 * FS))
    rms_up = np.sqrt(np.mean(upright[core] ** 2))
    rms_rolled = np.sqrt(np.mean(rolled[core] ** 2))
    assert abs(rms_up - 4.0 / np.sqrt(2)) < 0.15
    # heading oscillation maps to a smaller arc at |pitch|>0 (cos 10 deg)
    assert abs(rms_rolled - np.cos(np.radians(10)) * 4.0 / np.sqrt(2)) < 0.15
    gliding = stroke_oscillation(np.full_like(t, -10.0), 50 + slow_turn, FS)
    assert np.sqrt(np.mean(gliding[core] ** 2)) < 0.1


def test_stroke_oscillation_handles_heading_wrap_and_nan_gaps():
    t = np.arange(0, 200, 1 / FS)
    heading = (170 + 20 * np.sin(2 * np.pi * 0.005 * t) + 180) % 360 - 180  # crosses +/-180
    pitch = np.full_like(t, 0.0)
    pitch[1000:1010] = np.nan
    out = stroke_oscillation(pitch, heading, FS)
    assert np.isnan(out[1000:1010]).all()
    core = np.r_[int(20 * FS):1000, 1010:int(180 * FS)]
    assert np.nanmax(np.abs(out[core])) < 0.2
