#!/usr/bin/env python3
"""Build the checksum inventory for distributed analytical input files.

Run this script after the data stewards approve a new derived-data bundle.
It inventories actual analytical inputs under ``data/``; documentation and
``manifest.csv`` itself are excluded. The output contains only
repository-relative paths and no private source provenance.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST = DATA / "manifest.csv"

CSV_METADATA = {
    "data/dswp/buzz_events.csv": (
        "dswp",
        "buzz-level analysis input",
        "Pseudonymized derived acoustic and kinematic summaries",
        "dswp-buzz-events-v1",
    ),
    "data/dswp/buzz_clicks.csv": (
        "dswp",
        "sensitivity-analysis input",
        "Derived click times relative to anonymous buzz onset",
        "dswp-buzz-clicks-v1",
    ),
    "data/dswp/roll_speed_bins.csv": (
        "dswp",
        "figure input",
        "Derived two-second buzz-centred roll-rate bins",
        "dswp-roll-bins-v1",
    ),
    "data/dswp/deployment_summary.csv": (
        "dswp",
        "dataset-summary input",
        "Pseudonymized deployment-level recording and event counts",
        "dswp-deployments-v1",
    ),
    "data/dswp/reconstruction_error_summary.csv": (
        "dswp",
        "reconstruction-validation input",
        "Coordinate-free vessel-distance summaries by reconstruction method",
        "dswp-reconstruction-error-v1",
    ),
    "data/dswp/trajectory_index.csv": (
        "dswp",
        "trajectory index",
        "Pseudonymized reconstruction metadata and reviewed analysis bounds",
        "dswp-trajectory-index-v1",
    ),
    "data/dswp/comeback_trajectory_index.csv": (
        "dswp",
        "recurrence trajectory index",
        "Pseudonymized coarse deployment-scale reconstruction metadata",
        "dswp-comeback-trajectory-index-v1",
    ),
    "data/dswp/comeback_manuscript_labels.csv": (
        "dswp",
        "manuscript-result input",
        "Tactic labels used by the manuscript recurrence analysis",
        "dswp-comeback-manuscript-labels-v1",
    ),
    "data/ceti2024/buzz_features.csv": (
        "ceti2024",
        "independent-validation input",
        "Pseudonymized derived buzz and kinematic summaries",
        "ceti2024-buzz-features-v1",
    ),
}


def sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def trajectory_rows() -> list[dict]:
    """Inventory every numeric-only trajectory archive."""
    rows = []
    for path in sorted((DATA / "dswp" / "trajectories").glob("T*.npz")):
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != {"xyz_m"}:
                raise ValueError(f"{path}: expected only xyz_m")
            xyz = archive["xyz_m"]
        if xyz.dtype != np.float64 or xyz.ndim != 2 or xyz.shape[1] != 3:
            raise ValueError(f"{path}: expected an (n, 3) float64 array")
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "dataset": "dswp",
                "role": "reconstructed-trajectory input",
                "description": "Local-coordinate numeric reconstructed dive path",
                "schema_version": "dswp-trajectory-npz-v1",
                "rows": int(xyz.shape[0]),
                "sha256": sha256(path),
                "release_status": "approved_derived_release",
            }
        )
    return rows


def comeback_trajectory_rows() -> list[dict]:
    """Inventory coarse deployment-scale recurrence inputs."""
    rows = []
    paths = DATA / "dswp" / "comeback_trajectories"
    for path in sorted(paths.glob("D*.npz")):
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != {"time_s", "xyz_m"}:
                raise ValueError(f"{path}: expected time_s and xyz_m")
            time_s = archive["time_s"]
            xyz = archive["xyz_m"]
        if (
            time_s.dtype != np.float64
            or xyz.dtype != np.float64
            or time_s.ndim != 1
            or xyz.shape != (len(time_s), 3)
        ):
            raise ValueError(f"{path}: invalid coarse numeric trajectory")
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "dataset": "dswp",
                "role": "recurrence-analysis input",
                "description": "Coarse local-coordinate deployment reconstruction",
                "schema_version": "dswp-comeback-trajectory-npz-v1",
                "rows": int(len(time_s)),
                "sha256": sha256(path),
                "release_status": "approved_derived_release",
            }
        )
    return rows


def main() -> int:
    rows = []
    for relative_path, metadata in CSV_METADATA.items():
        path = ROOT / relative_path
        if not path.exists():
            raise FileNotFoundError(path)
        dataset, role, description, schema = metadata
        rows.append(
            {
                "path": relative_path,
                "dataset": dataset,
                "role": role,
                "description": description,
                "schema_version": schema,
                "rows": int(len(pd.read_csv(path))),
                "sha256": sha256(path),
                "release_status": "approved_derived_release",
            }
        )
    rows.extend(trajectory_rows())
    rows.extend(comeback_trajectory_rows())
    azores_manifest = DATA / "azores" / "source_manifest.csv"
    rows.append(
        {
            "path": azores_manifest.relative_to(ROOT).as_posix(),
            "dataset": "azores",
            "role": "authoritative-source metadata",
            "description": "Dryad version-1 file IDs, sizes, checksums, and MATLAB variables",
            "schema_version": "azores-dryad-source-manifest-v1",
            "rows": int(len(pd.read_csv(azores_manifest))),
            "sha256": sha256(azores_manifest),
            "release_status": "open_source_metadata",
        }
    )
    rows.sort(key=lambda row: row["path"])

    fieldnames = [
        "path",
        "dataset",
        "role",
        "description",
        "schema_version",
        "rows",
        "sha256",
        "release_status",
    ]
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} records to {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
