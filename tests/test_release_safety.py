from pathlib import Path

from scripts.check_release_safety import audit


def test_release_tree_passes_public_data_boundary():
    root = Path(__file__).resolve().parents[1]
    assert audit(root) == []


def test_release_guard_detects_raw_file_and_private_path(tmp_path):
    (tmp_path / "recording.wav").write_bytes(b"not real audio")
    (tmp_path / "loader.py").write_text(
        'SOURCE = "/' + 'Users/example/private/data"\n', encoding="utf-8"
    )
    errors = audit(tmp_path)
    assert any("forbidden raw/opaque" in error for error in errors)
    assert any("personal macOS path" in error for error in errors)
