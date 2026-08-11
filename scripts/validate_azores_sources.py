#!/usr/bin/env python3
"""Validate manually downloaded Azores files against the Dryad manifest."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation.azores import load_azores_sources  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and inspect the four open Azores MATLAB files."
    )
    parser.add_argument(
        "directory",
        help="Directory containing the four files named in data/azores/source_manifest.csv",
    )
    args = parser.parse_args()
    tables = load_azores_sources(args.directory)
    for name, table in tables.items():
        print(f"{name}: {len(table)} rows, {len(table.columns)} fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
