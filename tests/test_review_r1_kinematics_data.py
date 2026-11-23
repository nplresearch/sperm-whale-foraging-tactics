"""Steward-exported kinematic summaries used by the reviewer-1 revision."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trajectory.schema import FORBIDDEN_TOKENS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "dswp"
UNSAFE = re.compile(
    r"(?:^|_)(?:whale_name|animal_name|tag_id|serial_number|latitude|longitude|"
    r"gps|absolute_time|utc|recording_date|source_path|file_path|audio|raw)(?:$|_)",
    re.I,
)


pytestmark = pytest.mark.skipif(
    not (DATA / "buzz_kinematics.csv").exists(),
    reason="steward-review kinematics tables are not committed; request them from the steward",
)


def _safe_columns(frame):
    for column in frame.columns:
        assert not UNSAFE.search(column), column
        assert not any(token in column.lower() for token in FORBIDDEN_TOKENS), column


def test_buzz_kinematics_cover_every_public_buzz_with_sane_values():
    kin = pd.read_csv(DATA / "buzz_kinematics.csv")
    events = pd.read_csv(DATA / "buzz_events.csv")
    _safe_columns(kin)
    assert kin.event_id.is_unique
    assert set(kin.event_id) == set(events.event_id)
    for col in [c for c in kin if c.endswith("_coverage")]:
        assert kin[col].dropna().between(0, 1).all(), col
    for col in [c for c in kin if c.endswith("_speed_m_s")]:
        assert kin[col].dropna().between(0, 10).all(), col
    for col in [c for c in kin if c.endswith("_stroke_rms_deg")]:
        assert (kin[col].dropna() >= 0).all(), col
    assert kin.buzz_abs_pitch_deg.dropna().between(0, 90).all()


def test_dive_and_deployment_kinematics_use_public_identifiers_only():
    dives = pd.read_csv(DATA / "dive_kinematics.csv")
    deployments = pd.read_csv(DATA / "deployment_kinematics.csv")
    events = pd.read_csv(DATA / "buzz_events.csv")
    _safe_columns(dives)
    _safe_columns(deployments)
    assert dives.dive_id.is_unique and set(dives.dive_id) <= set(events.dive_id)
    assert set(deployments.deployment_id) == set(events.deployment_id)
    assert (dives.interdive_interval_s.dropna() > 0).all()
    periods = deployments.descent_stroke_period_s.dropna()
    # Stroke rhythm must fall inside the 0.1-0.4 Hz effort band for most tags.
    assert np.mean((periods >= 2.5) & (periods <= 10)) > 0.9


def test_buzz_profiles_are_binned_summaries_of_public_buzzes():
    prof = pd.read_csv(DATA / "buzz_kinematic_profiles.csv")
    events = pd.read_csv(DATA / "buzz_events.csv")
    _safe_columns(prof)
    assert set(prof.event_id) <= set(events.event_id)
    assert set(prof.bin_start_s) <= set(np.arange(-20.0, 20.0, 2.0))
    assert not prof.duplicated(["event_id", "bin_start_s"]).any()
    for col in ("ocdr45_speed_m_s", "ocdr30_speed_m_s"):
        assert prof[col].dropna().between(0, 10).all(), col
    assert prof.pitch_deg.dropna().between(-90, 90).all()
