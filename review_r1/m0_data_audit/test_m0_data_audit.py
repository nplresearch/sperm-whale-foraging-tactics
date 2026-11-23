"""M0: are the inputs every other module depends on what we think they are?"""

import sys

import pandas as pd
import pytest

from common import PKG, needs_steward

sys.path.insert(0, str(PKG / "scripts"))


def test_release_safety_gate_passes():
    from check_release_safety import audit
    assert audit() == []


@needs_steward
def test_kinematics_rows_match_public_events_one_to_one():
    ev = pd.read_csv(PKG / "data/dswp/buzz_events.csv")
    kin = pd.read_csv(PKG / "data/dswp/buzz_kinematics.csv")
    assert len(ev) == len(kin) == 3686
    assert kin.event_id.is_unique and set(kin.event_id) == set(ev.event_id)


@needs_steward
def test_pitch_is_physically_possible():
    """The 180-degree pitch error in 17 internal buzzes must not leak into the export."""
    kin = pd.read_csv(PKG / "data/dswp/buzz_kinematics.csv")
    assert kin.buzz_pitch_deg.dropna().abs().max() <= 90.0


@needs_steward
def test_buzzes_without_orientation_are_few_and_flagged_nan():
    kin = pd.read_csv(PKG / "data/dswp/buzz_kinematics.csv")
    missing = kin.buzz_pitch_deg.isna().sum()
    assert 0 < missing <= 0.02 * len(kin)   # 66 buzzes (1.8 %) in two deployments


@needs_steward
def test_new_tables_are_marked_pending_in_manifest():
    m = pd.read_csv(PKG / "data/manifest.csv").set_index("path")
    if "data/dswp/buzz_kinematics.csv" not in m.index:
        pytest.skip("manifest rows for the new tables are not committed on this branch")
    for name in ("buzz_kinematics", "dive_kinematics", "deployment_kinematics",
                 "buzz_kinematic_profiles"):
        assert m.loc[f"data/dswp/{name}.csv", "release_status"] == "pending_steward_review"


@pytest.mark.skip(reason="needs the raw tag files in repo/Data; owner of M0 runs this by hand")
def test_17_buzzes_with_flipped_pitch_heading_are_documented():
    """See README: check whether the constant-speed reconstruction used the bad pitch."""
