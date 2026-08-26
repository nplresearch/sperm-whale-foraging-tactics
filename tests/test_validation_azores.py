import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import validation.azores as azores
from validation.azores import (
    AZORES_FILES,
    CITATION,
    DRYAD_DOI,
    LICENSE,
    _transition_counts,
    classify_balanced_assignment,
    classify_nearest_corners,
    find_azores_source_directory,
    source_manifest,
    validate_azores_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def test_azores_provenance_is_pinned_to_authoritative_doi():
    assert DRYAD_DOI in CITATION
    assert "CC0" in LICENSE


def test_azores_manifest_pins_all_required_files():
    manifest = source_manifest()
    assert set(manifest["filename"]) == set(AZORES_FILES)
    assert manifest["sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert manifest["size_bytes"].gt(0).all()


def test_azores_validator_rejects_unreviewed_bytes(tmp_path):
    for filename, metadata in AZORES_FILES.items():
        path = tmp_path / filename
        path.write_bytes(b"not the Dryad file")
        assert hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]
    with pytest.raises(ValueError, match="Dryad source mismatch"):
        validate_azores_sources(tmp_path)


def test_azores_source_finder_uses_and_validates_explicit_directory(tmp_path, monkeypatch):
    source = tmp_path / "open-azores-data"
    source.mkdir()
    for filename in AZORES_FILES:
        (source / filename).touch()
    validated = []
    monkeypatch.setattr(azores, "validate_azores_sources", validated.append)

    found = find_azores_source_directory(tmp_path / "repository", explicit=source)

    assert found == source.resolve()
    assert validated == [source.resolve()]


def test_azores_source_finder_reports_all_default_locations(tmp_path):
    repository = tmp_path / "production"
    repository.mkdir()

    with pytest.raises(FileNotFoundError, match="CETI_AZORES_SOURCE") as error:
        find_azores_source_directory(repository)

    assert str(repository / "local-data" / "azores") in str(error.value)
    assert "Clean_notebooks_figures/Azores_code" in str(error.value)


def test_nearest_corner_boundary_ties_remain_unclassified():
    features = pd.DataFrame(
        {
            "distance_to_a": [0.1, 0.2, 0.8],
            "distance_to_b": [0.9, 0.2, 0.1],
        }
    )
    labels = classify_nearest_corners(features, n_per_corner=2)
    assert labels["operative_type"].tolist() == ["A", "unclassified", "B"]
    assert labels["nearest_corner_tie"].tolist() == [False, True, False]


def test_balanced_assignment_is_disjoint_and_complete():
    features = pd.DataFrame(
        {
            "distance_to_a": [0.1, 0.2, 0.8, 0.9],
            "distance_to_b": [0.9, 0.2, 0.1, 0.8],
        }
    )
    labels = classify_balanced_assignment(features, n_per_type=2)
    assert labels["balanced_type"].value_counts().to_dict() == {"A": 2, "B": 2}


def test_transition_counter_preserves_repeated_bootstrap_draws():
    counts = _transition_counts([["A"], ["A"]])
    assert counts["S"]["A"] == 2
    assert counts["A"]["E"] == 2


def test_derived_azores_regression_targets_are_registered():
    summary = json.loads((ROOT / "results" / "azores" / "azores_summary.json").read_text())
    assert summary["operative_counts"] == {"A": 28, "B": 28, "unclassified": 2}
    assert summary["nearest_corner_ties"] == 2
    assert summary["pre_buzz_vertical_speed"]["p_value"] == pytest.approx(0.0204092687)
    contrasts = pd.read_csv(ROOT / "results" / "azores" / "azores_prey_contrasts.csv")
    operative_depth = contrasts.query(
        "classification == 'operative' and metric == 'mean_prey_depth_m'"
    ).iloc[0]
    assert operative_depth["p_value"] == pytest.approx(0.0040979968)
    assert operative_depth["cohens_d_a_minus_b"] == pytest.approx(1.3426902527)
