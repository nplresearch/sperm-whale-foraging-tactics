"""Shared helpers for the review_r1 modules.

Every module owns (a) a set of *claims* in ``claims.yaml`` (a number quoted in the
response letter, the file and field it comes from, and the tolerance) and (b) an
optional ``run.py`` that recomputes its outputs. ``check_claims`` is the single
mechanism that compares the letter against the result files.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

PKG = Path(__file__).resolve().parents[1]          # CETI_Foraging_Reproducibility/
HERE = Path(__file__).resolve().parent             # review_r1/
RESULTS = PKG / "results" / "review_r1"
STEWARD_FILES = [PKG / "data/dswp" / f for f in (
    "buzz_kinematics.csv", "dive_kinematics.csv", "deployment_kinematics.csv",
    "buzz_kinematic_profiles.csv")]

# Statuses a claim can carry. Only ``verified`` claims may be quoted without a caveat.
STATUSES = {
    "verified": "number reproduces from a result file and is methodologically sound",
    "circular": "number reproduces but is implied by how the A/B labels are built",
    "withdrawn": "number reproduces but the conclusion was withdrawn; do not quote as support",
    "printed_only": "script prints the number but nothing stores it; not machine-checked",
}


def steward_data_present() -> bool:
    return all(p.exists() for p in STEWARD_FILES)


needs_steward = pytest.mark.skipif(
    not steward_data_present(),
    reason="steward-review kinematics tables (data/dswp/*kinematic*.csv) not present in this checkout")


def load_claims(module: str | None = None) -> list[dict]:
    claims = yaml.safe_load((HERE / "claims.yaml").read_text())
    return [c for c in claims if module is None or c["module"] == module]


def _walk(obj, path):
    for key in path:
        obj = obj[key]
    return obj


def observed(claim: dict) -> float:
    """Read the value a claim points at in ``results/review_r1``."""
    f = RESULTS / claim["file"]
    if f.suffix == ".json":
        data = json.loads(f.read_text())
        value = float(_walk(data, claim["path"]))
        if "minus_path" in claim:
            value -= float(_walk(data, claim["minus_path"]))
        return value
    df = pd.read_csv(f)
    for col, val in claim.get("where", {}).items():
        df = df[df[col] == val]
    if len(df) != 1:
        raise LookupError(f"{claim['id']}: selector matched {len(df)} rows in {claim['file']}")
    if "expr" in claim:
        return float(df.eval(claim["expr"]).iloc[0])
    return float(df[claim["col"]].iloc[0])


def matches(claim: dict, value: float) -> bool:
    letter = float(claim["letter"])
    op = claim.get("op", "approx")
    if op == "le":
        return value <= letter
    if op == "ge":
        return value >= letter
    if op == "log10":   # compare orders of magnitude for tiny p-values
        return abs(math.log10(value) - math.log10(letter)) <= float(claim.get("tol", 0.5))
    return abs(value - letter) <= float(claim["tol"])


def run_module(module_dir: Path, scripts: list[str], *, claims_prefix: str, backup: bool = True) -> int:
    """Recompute a module. Backs up results/review_r1 first, then re-checks its claims."""
    if backup and RESULTS.exists():
        dest = RESULTS.parent / f"review_r1_backup_{datetime.now():%Y%m%d_%H%M%S}"
        shutil.copytree(RESULTS, dest)
        print(f"backed up {RESULTS} -> {dest}")
    for s in scripts:
        print(f"== running {s}")
        subprocess.run([sys.executable, str(PKG / "scripts" / s)], check=True, cwd=PKG)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(HERE / "test_claims.py"), "-k", claims_prefix],
        cwd=PKG).returncode
