"""M7: Azores checks need the four Dryad files; skip cleanly when absent."""

import json

import pytest

from common import PKG, RESULTS

DRYAD = PKG.parent / "repo/Clean_notebooks_figures/Azores_code"
A = json.loads((RESULTS / "foraging_models.json").read_text())["azores"]


def test_echo_sample_is_tiny():
    assert A["ts_nearest"]["n_A"] + A["ts_nearest"]["n_B"] <= 30    # one juvenile whale


def test_echo_level_is_a_weak_size_proxy():
    """Fixed target would fall ~40 dB per decade of range; observed is about 24."""
    assert abs(A["echo_level_check"]["median_slope_db_per_decade"]) < 30


def test_no_size_difference_between_tactics():
    assert A["ts_nearest"]["mann_whitney_p"] > 0.05 and A["ts_max"]["mann_whitney_p"] > 0.05


@pytest.mark.skipif(not DRYAD.exists(), reason="Dryad Azores files not in this checkout")
def test_dryad_files_match_pinned_checksums():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(PKG / "scripts/validate_azores_sources.py"), str(DRYAD)],
                       capture_output=True, text=True, cwd=PKG)
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
