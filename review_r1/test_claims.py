"""One parametrised test: every number in the letter must match its result file.

Run one module:  pytest review_r1/test_claims.py -k M3
A failure means the letter, the result file, or the code has drifted: decide which
is right, never just widen the tolerance.
"""

import pytest
from common import STATUSES, load_claims, matches, observed

CLAIMS = load_claims()
CHECKABLE = [c for c in CLAIMS if c["status"] != "printed_only"]


def test_registry_is_well_formed():
    ids = [c["id"] for c in CLAIMS]
    assert len(ids) == len(set(ids)), "duplicate claim ids"
    for c in CLAIMS:
        assert c["status"] in STATUSES, c["id"]
        assert c["id"].split("-")[0] == c["module"], c["id"]
        assert c["status"] == "printed_only" or c.get("file"), c["id"]


@pytest.mark.parametrize("claim", CHECKABLE, ids=[c["id"] for c in CHECKABLE])
def test_claim_matches_result_file(claim):
    value = observed(claim)
    assert matches(claim, value), (
        f"{claim['id']}: letter says {claim['letter']} but {claim['file']} gives {value!r}\n"
        f"  claim: {claim['text']}")
