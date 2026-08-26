import pandas as pd
import pytest

from validation.ceti2024 import (
    FEATURE_COLUMNS,
    _sequential_tokens,
    classify_corner,
    run_ceti2024_validation,
    validate_publication_table,
)


def safe_table(n=8):
    d = pd.DataFrame(index=range(n), columns=FEATURE_COLUMNS)
    d["unit_id"] = ["unit_a"] * n
    d["dive_id"] = ["dive_a"] * (n // 2) + ["dive_b"] * (n - n // 2)
    d["buzz_order_in_dive"] = [1, 2, 3, 4, 1, 2, 3, 4][:n]
    d["has_kinematics"] = True
    d["n_clicks"] = 40
    for col in FEATURE_COLUMNS[5:]:
        d[col] = 1.0
    d["ramp_up_duration_s"] = list(range(1, n + 1))
    d["speed_3d_mps"] = list(range(1, n + 1))
    return d


def test_schema_rejects_raw_or_identifier_columns():
    d = safe_table()
    d["raw_audio_path"] = "secret.wav"
    with pytest.raises(ValueError, match="Unsafe"):
        validate_publication_table(d)


def test_release_tokens_are_sequential_not_source_hashes():
    source = pd.Series(["source_b", "source_a", "source_b"])
    assert _sequential_tokens(source, "U").tolist() == ["U002", "U001", "U002"]


def test_corner_and_results_are_reproducible(tmp_path):
    d = safe_table()
    validate_publication_table(d)
    labels = classify_corner(d, n_per_class=2)
    assert set(labels) == {"A", "B", "unclassified"}
    source = tmp_path / "buzz_features.csv"
    d.to_csv(source, index=False)
    result = run_ceti2024_validation(source, tmp_path / "results")
    assert {"labels", "kinematic_statistics", "sequence_statistics"} == set(result)
    assert (tmp_path / "results" / "analysis_manifest.json").exists()
    for stem in ("ceti2024_corner_clustering", "ceti2024_kinematics", "ceti2024_sequence"):
        assert (tmp_path / "results" / f"{stem}.png").exists()
