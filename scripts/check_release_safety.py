#!/usr/bin/env python3
"""Fail if the repository contains material outside the public data boundary.

This is a release guard, not a claim that automated scanning can replace review.
It checks the most common failure modes in this project:

* raw/opaque scientific file types;
* original DSWP/CETI identifiers in code or distributed data;
* private download links and personal filesystem paths;
* notebook outputs or execution counts;
* unsafe CSV columns;
* object arrays hidden in NPZ archives; and
* files too large for an ordinary GitHub repository.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 95 * 1024 * 1024

IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "__pycache__",
    "notebooks_executed",
}

FORBIDDEN_SUFFIXES = {
    ".aif",
    ".aiff",
    ".flac",
    ".mat",
    ".mp3",
    ".pickle",
    ".pkl",
    ".tdms",
    ".wav",
}

PRIVATE_TEXT_PATTERNS = {
    "personal macOS path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    "personal Linux path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
    "personal Windows path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\\]+\\\\"),
    "private Dropbox URL": re.compile(
        r"https?://(?:www\.)?(?:dropbox\.com|dropboxusercontent\.com)/", re.I
    ),
    "legacy private data path": re.compile(r"(?:\.\./)+Data/(?:big|Name_data)/"),
}

# Source tag formats are allowed only in the documentation/notebook that points
# to the already-public Azores archive. They must not occur in distributed
# DSWP/CETI data or executable examples.
SOURCE_ID = re.compile(r"\bsw\d{2}[_-]\d{3}[a-z]?\b", re.I)
SOURCE_ID_ALLOWLIST = {
    Path("docs/validation_pipeline.md"),
    Path("notebooks/validation/01_azores_open_data.ipynb"),
    Path("notebooks/validation/03_azores_derivation.ipynb"),
}

UNSAFE_COLUMN = re.compile(
    r"(?:^|_)(?:whale_name|animal_name|tag_id|serial_number|latitude|longitude|"
    r"gps|absolute_time|utc|recording_date|source_path|file_path|audio|raw)(?:$|_)",
    re.I,
)


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        yield path


def is_text(path: Path) -> bool:
    return path.suffix.lower() in {
        "",
        ".bib",
        ".cff",
        ".cfg",
        ".csv",
        ".ini",
        ".ipynb",
        ".json",
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }


def check_text(path: Path, relative: Path, errors: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{relative}: expected text but could not decode as UTF-8")
        return
    for label, pattern in PRIVATE_TEXT_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"{relative}: contains {label}")
    if relative not in SOURCE_ID_ALLOWLIST and SOURCE_ID.search(text):
        errors.append(f"{relative}: contains an original source-style deployment identifier")


def check_notebook(path: Path, relative: Path, errors: list[str]) -> None:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{relative}: invalid notebook JSON ({exc})")
        return
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None:
            errors.append(f"{relative}: code cell {index} has an execution count")
        if cell.get("outputs"):
            errors.append(f"{relative}: code cell {index} contains embedded output")


def check_csv(path: Path, relative: Path, errors: list[str]) -> None:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle), [])
    except (UnicodeDecodeError, OSError, csv.Error) as exc:
        errors.append(f"{relative}: could not inspect CSV header ({exc})")
        return
    bad = [column for column in header if UNSAFE_COLUMN.search(column)]
    if bad:
        errors.append(f"{relative}: unsafe CSV columns: {', '.join(bad)}")


def check_npz(path: Path, relative: Path, errors: list[str]) -> None:
    """Inspect NPY headers without inflating every released trajectory."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.endswith(".npy")]
            if not members:
                errors.append(f"{relative}: empty NPZ archive")
            for member in members:
                name = Path(member).stem
                if UNSAFE_COLUMN.search(name):
                    errors.append(f"{relative}: unsafe NPZ member name: {name}")
                with archive.open(member) as handle:
                    version = np.lib.format.read_magic(handle)
                    if version == (1, 0):
                        _, _, dtype = np.lib.format.read_array_header_1_0(handle)
                    else:
                        _, _, dtype = np.lib.format.read_array_header_2_0(handle)
                if dtype.kind in {"O", "S", "U", "V"}:
                    errors.append(
                        f"{relative}: non-numeric NPZ member {name!r} ({dtype})"
                    )
    except Exception as exc:  # noqa: BLE001 - report every unreadable release archive
        errors.append(f"{relative}: unsafe or unreadable NPZ archive ({exc})")


def audit(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in iter_files(root):
        relative = path.relative_to(root)
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"{relative}: forbidden raw/opaque file type {suffix}")
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(
                f"{relative}: {path.stat().st_size / 1024**2:.1f} MiB exceeds "
                f"the {MAX_FILE_BYTES / 1024**2:.0f} MiB release limit"
            )
        if is_text(path):
            check_text(path, relative, errors)
        if suffix == ".ipynb":
            check_notebook(path, relative, errors)
        elif suffix == ".csv" and relative.parts[:1] == ("data",):
            check_csv(path, relative, errors)
        elif suffix == ".npz" and relative.parts[:1] == ("data",):
            check_npz(path, relative, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = audit(args.root.resolve())
    if errors:
        print("PUBLIC-RELEASE SAFETY CHECK FAILED", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"Public-release safety check passed: {args.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
