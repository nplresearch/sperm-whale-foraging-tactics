#!/usr/bin/env python3
"""Create the only individual-level trajectory release allowed in this repo.

Input must already be reconstructed positions; this program does *not* ingest
raw recordings, sensor streams, source MAT files, GPS positions, or metadata.
It retains only pseudonymous identifiers, elapsed time, local relative XYZ
coordinates, depth/phase, and a named reconstruction method. It rejects
forbidden columns and values before writing CSV or Parquet.

Example (run outside version control until reviewed):
    python scripts/export_safe_trajectory_data.py reconstructed.csv data/derived/trajectory/trajectories.csv
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from trajectory.schema import FORBIDDEN_TOKENS, OPTIONAL_TRAJECTORY_COLUMNS, TRAJECTORY_COLUMNS, is_safe_release_path, validate_trajectories


def reject_leaks(frame: pd.DataFrame) -> None:
    lower_columns = [c.lower() for c in frame.columns]
    bad_columns = [c for c in lower_columns if any(token in c for token in FORBIDDEN_TOKENS)]
    if bad_columns: raise ValueError(f"forbidden raw/provenance columns: {bad_columns}")
    # Scan object values too, catching accidental paths or source labels.
    for col in frame.select_dtypes(include="object"):
        values = frame[col].dropna().astype(str)
        if values.str.contains(r"(?:^/|[A-Za-z]:\\|~[/\\])", regex=True).any():
            raise ValueError(f"absolute/local path found in {col}")
        if values.str.lower().str.contains("|".join(FORBIDDEN_TOKENS), regex=True).any():
            raise ValueError(f"raw-data token found in {col}")


def sanitize(frame: pd.DataFrame) -> pd.DataFrame:
    reject_leaks(frame)
    permitted = [c for c in (*TRAJECTORY_COLUMNS, *OPTIONAL_TRAJECTORY_COLUMNS) if c in frame.columns]
    out = validate_trajectories(frame.loc[:, permitted])
    # Release coordinates are local, dive-relative reconstructed coordinates only.
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Reviewed reconstructed trajectory CSV/Parquet")
    parser.add_argument("output", type=Path, help="Safe derived CSV/Parquet to write")
    args = parser.parse_args()
    if not is_safe_release_path(args.output): parser.error("output must be a derived CSV/Parquet with a safe name")
    if args.input.suffix.lower() == ".csv": frame = pd.read_csv(args.input)
    elif args.input.suffix.lower() == ".parquet": frame = pd.read_parquet(args.input)
    else: parser.error("input must be CSV or Parquet; raw formats are intentionally unsupported")
    safe = sanitize(frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    (safe.to_csv(args.output, index=False) if args.output.suffix.lower() == ".csv" else safe.to_parquet(args.output, index=False))
    print(f"Wrote {len(safe):,} safe reconstructed samples across {safe.trajectory_id.nunique()} trajectories: {args.output}")

if __name__ == "__main__": main()
