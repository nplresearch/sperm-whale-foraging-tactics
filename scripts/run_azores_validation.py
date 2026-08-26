#!/usr/bin/env python3
"""Run the publication-safe Azores validation from locally retrieved inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation.azores import run_azores_validation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source_directory",
        type=Path,
        help="Directory containing the four validated Dryad MATLAB files.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT / "results" / "azores",
        help="Directory for publication-safe derived outputs.",
    )
    parser.add_argument("--n-boot", type=int, default=2_000)
    args = parser.parse_args()
    result = run_azores_validation(
        args.source_directory,
        args.output_directory,
        n_boot=args.n_boot,
    )
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
