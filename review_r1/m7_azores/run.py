"""Recompute this module's outputs, then re-check its claims.

Backs up results/review_r1 first (the legacy scripts overwrite it in place).
Usage: python review_r1/m7_azores/run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import run_module  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_module(Path(__file__).parent, ["run_review_r1_azores_phase.py"], claims_prefix="M7"))
