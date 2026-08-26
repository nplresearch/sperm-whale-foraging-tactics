#!/usr/bin/env python3
"""Create reviewed comeback-analysis inputs in a restricted environment.

This is a data-steward export, not part of the public analysis run. It accepts
the internal derived buzz/dive objects, manuscript clustering table, and
deployment-scale *reconstructed* positions. It writes only:

* relative deployment time for each already-pseudonymized public buzz;
* A/B labels needed to reproduce the manuscript forest plot; and
* 20-s, local-coordinate numeric reconstructed paths.

No source identifiers, crosswalk, raw sensor channels, locations, or private
paths are written.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

FS_HZ = 25.0
SUBSAMPLE_S = 20.0
SPECIAL_PUBLIC_OFFSETS_S = {"D012": 7200.0, "D029": 7200.0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_buzz_pickle", type=Path)
    parser.add_argument("source_dive_pickle", type=Path)
    parser.add_argument("source_manuscript_labels_csv", type=Path)
    parser.add_argument("source_reconstruction_dir", type=Path)
    parser.add_argument("public_buzz_events_csv", type=Path)
    parser.add_argument("output_data_dir", type=Path)
    args = parser.parse_args()

    source_buzzes = pd.read_pickle(args.source_buzz_pickle).reset_index(drop=True)
    source_dives = pd.read_pickle(args.source_dive_pickle)
    public_buzzes = pd.read_csv(args.public_buzz_events_csv).reset_index(drop=True)
    manuscript_labels = pd.read_csv(args.source_manuscript_labels_csv).reset_index(drop=True)
    if not (
        len(source_buzzes) == len(public_buzzes) == len(manuscript_labels)
        and np.allclose(
            source_buzzes["duration_start"],
            public_buzzes["ramp_up_duration_s"],
            equal_nan=True,
        )
        and np.allclose(
            source_buzzes["avg_speed_3d_during_buzz"],
            public_buzzes["avg_speed_3d_m_s"],
            equal_nan=True,
        )
    ):
        raise ValueError("source and public buzz rows do not align exactly")

    source_buzzes = source_buzzes.merge(
        source_dives[["tag_id", "dive_number", "dive_start"]],
        on=["tag_id", "dive_number"],
        validate="many_to_one",
    )
    public_buzzes["deployment_buzz_start_s"] = [
        float(dive_start) + float(clicks[0])
        for dive_start, clicks in zip(source_buzzes["dive_start"], source_buzzes["buzzes_times"])
    ]
    public_buzzes.to_csv(args.public_buzz_events_csv, index=False)

    pd.DataFrame(
        {
            "event_id": public_buzzes["event_id"],
            "manuscript_buzz_type": manuscript_labels["clustering_AB"],
        }
    ).to_csv(args.output_data_dir / "comeback_manuscript_labels.csv", index=False)

    source_tokens = sorted(source_buzzes["tag_id"].astype(str).unique())
    token_map = {
        source_token: f"D{number:03d}" for number, source_token in enumerate(source_tokens, 1)
    }
    output_paths = args.output_data_dir / "comeback_trajectories"
    output_paths.mkdir(parents=True, exist_ok=True)
    rows = []
    step = int(FS_HZ * SUBSAMPLE_S)
    for source_path in sorted(args.source_reconstruction_dir.glob("*.pkl")):
        deployment_id = token_map[source_path.stem]
        xyz = np.load(source_path, allow_pickle=True)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
            raise ValueError(f"{source_path}: invalid reconstructed positions")
        time_offset = SPECIAL_PUBLIC_OFFSETS_S.get(deployment_id, 10.0 / FS_HZ)
        time_s = time_offset + np.arange(len(xyz), dtype=float) / FS_HZ
        sampled_xyz = xyz[::step].astype(np.float64)
        sampled_xyz[:, :2] -= sampled_xyz[0, :2]
        sampled_time = time_s[::step].astype(np.float64)
        relative_path = Path("comeback_trajectories") / f"{deployment_id}.npz"
        np.savez_compressed(
            args.output_data_dir / relative_path,
            time_s=sampled_time,
            xyz_m=sampled_xyz,
        )
        rows.append(
            {
                "deployment_id": deployment_id,
                "file": relative_path.as_posix(),
                "n_samples": len(sampled_xyz),
                "subsample_interval_s": SUBSAMPLE_S,
                "reconstruction_method": "constant_speed_1.2",
                "coordinate_frame": "deployment_local",
            }
        )
    pd.DataFrame(rows).to_csv(args.output_data_dir / "comeback_trajectory_index.csv", index=False)
    print(
        f"Updated {len(public_buzzes)} buzzes and exported {len(rows)} coarse reconstructed paths"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
