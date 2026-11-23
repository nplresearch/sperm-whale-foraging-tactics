#!/usr/bin/env python3
"""Reviewer-1 (round 1) diagnostics on the released DSWP reconstructions.

No new measurements: recovers how much of each buzz-window speed series was
assumed (0.9 m/s fallback) versus derived from depth rate, then re-runs the
unchanged energy model under alternative mass, smoothing and clip settings.
Writes only to results/review_r1/.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dswp.energetics import EnergyParameters, energy_from_speed_series  # noqa: E402
from dswp.speed_regimes import (  # noqa: E402
    CLIPPED,
    DEPTH,
    FALLBACK,
    classify_steps,
    rebuild_with_clip,
)
from trajectory.analysis import load_trajectory  # noqa: E402

FS = 25.0
PRE_S = 10.0
OUT = ROOT / "results" / "review_r1"
PROD = EnergyParameters()
FEMALE = {  # Dominica social-unit adult, length-scaled skull width
    "female_12t": replace(PROD, body_mass_kg=12_000.0, body_length_m=11.0, skull_width_m=1.375),
    "female_13.5t": replace(PROD, body_mass_kg=13_500.0, body_length_m=11.0, skull_width_m=1.375),
    "female_15t": replace(PROD, body_mass_kg=15_000.0, body_length_m=11.0, skull_width_m=1.375),
}
EFF = PROD.eta_metabolic * PROD.eta_propulsive


def smooth(x, n=int(FS)):
    return np.convolve(x, np.ones(n) / n, mode="same")


def step_speed(xyz):
    return np.linalg.norm(np.diff(xyz, axis=0), axis=1) * FS


def energy(speed, params):
    t = (np.arange(len(speed)) + 0.5) / FS
    return energy_from_speed_series(t, speed, parameters=params)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    index = pd.read_csv(ROOT / "data/dswp/trajectory_index.csv").set_index("trajectory_id")

    rows, energy_rows = [], []
    dataset = {"all": np.zeros(3, int), "foraging": np.zeros(3, int)}
    fallback_violations = ambiguous = 0

    for tid, group in events.groupby("trajectory_id", sort=False):
        if tid not in index.index:
            continue
        meta = index.loc[tid]
        xyz = load_trajectory(ROOT / "data/dswp" / meta["file"])
        regime, est, _ = classify_steps(xyz)
        d = np.diff(xyz, axis=0)
        h_speed = np.hypot(d[:, 0], d[:, 1]) * FS
        fallback_violations += int(np.sum((regime == FALLBACK) & (h_speed > 0.9 + 1e-6)))
        ambiguous += int(np.sum((regime == DEPTH) & (h_speed >= 0.9 * np.cos(0.05) - 1e-9)
                                & (h_speed <= 0.9 + 1e-9)))
        dataset["all"] += np.bincount(regime, minlength=3)
        fs_, fe_ = int(meta["foraging_start_index"]), int(meta["foraging_end_index"])
        dataset["foraging"] += np.bincount(regime[fs_:fe_], minlength=3)

        speeds = {
            "production": step_speed(xyz),
            "clip7": step_speed(rebuild_with_clip(xyz, 7.0)),
            "noclip": step_speed(rebuild_with_clip(xyz, np.inf)),
        }
        speeds["smooth1s"] = smooth(speeds["production"])

        for ev in group.itertuples(index=False):
            if not (np.isfinite(ev.buzz_start_s) and np.isfinite(ev.buzz_end_s)):
                continue
            start = max(0, int(np.floor(ev.buzz_start_s * FS)))
            end = min(len(xyz) - 1, int(np.floor(ev.buzz_end_s * FS)))
            if end - start + 1 < 3:
                continue
            win = slice(start, end)  # steps start..end-1 == diff of xyz[start:end+1]
            pre = slice(max(0, start - int(PRE_S * FS)), start)
            r, rp = regime[win], regime[pre]
            row = {
                "event_id": ev.event_id, "individual_id": ev.individual_id,
                "buzz_type": ev.buzz_type, "n_steps": len(r),
                "buzz_frac_fallback": np.mean(r == FALLBACK),
                "buzz_frac_depth": np.mean(r == DEPTH),
                "buzz_frac_clipped": np.mean(r == CLIPPED),
                "buzz_any_measured": bool(np.any(r != FALLBACK)),
                "buzz_any_clipped": bool(np.any(r == CLIPPED)),
                "pre_frac_fallback": np.mean(rp == FALLBACK) if len(rp) else np.nan,
                "pre_any_measured": bool(np.any(rp != FALLBACK)) if len(rp) else np.nan,
                "buzz_median_estimator_speed": float(np.median(est[win])),
            }
            for name, s in speeds.items():
                row[f"mean_speed_{name}"] = float(s[win].mean())
            rows.append(row)

            variants = {
                "production": (speeds["production"], PROD),
                "smooth1s": (speeds["smooth1s"], PROD),
                "clip7": (speeds["clip7"], PROD),
                "noclip": (speeds["noclip"], PROD),
                **{k: (speeds["production"], p) for k, p in FEMALE.items()},
                "female_13.5t_smooth1s": (speeds["smooth1s"], FEMALE["female_13.5t"]),
            }
            for vname, (s, params) in variants.items():
                e = energy(s[win], params)
                rest_w = e["E_metabolic_rest_J"] / e["capture_duration_s"]
                energy_rows.append({
                    "event_id": ev.event_id, "individual_id": ev.individual_id,
                    "buzz_type": ev.buzz_type, "variant": vname,
                    "E_total_J": e["E_total_J"],
                    "E_drag_only_J": e["drag_work_J"] / EFF + e["E_metabolic_rest_J"],
                    "drag_work_J": e["drag_work_J"],
                    "acc_work_J": e["positive_acceleration_work_J"],
                    "mean_power_W": e["mean_metabolic_power_W"],
                    "power_over_rest": e["mean_metabolic_power_W"] / rest_w,
                })

    ev = pd.DataFrame(rows)
    en = pd.DataFrame(energy_rows)
    ev.to_csv(OUT / "speed_regime_events.csv", index=False)
    en.to_csv(OUT / "energy_variants_events.csv", index=False)

    # Regime summary by buzz type
    by_type = ev.groupby("buzz_type").agg(
        n=("event_id", "size"),
        mean_frac_fallback=("buzz_frac_fallback", "mean"),
        median_frac_fallback=("buzz_frac_fallback", "median"),
        share_no_measured_step=("buzz_any_measured", lambda s: 1 - s.mean()),
        share_any_clipped=("buzz_any_clipped", "mean"),
        pre10s_mean_frac_fallback=("pre_frac_fallback", "mean"),
        pre10s_share_no_measured=("pre_any_measured", lambda s: 1 - s.astype(float).mean()),
        median_mean_speed_production=("mean_speed_production", "median"),
        median_mean_speed_noclip=("mean_speed_noclip", "median"),
    )
    by_type.to_csv(OUT / "speed_regime_by_type.csv")

    # Energy variants: within-whale means, then across whales (manuscript scheme)
    summary = []
    ab = en[en.buzz_type.isin(["A", "B"])]
    for vname, g in ab.groupby("variant", sort=False):
        for col in ("E_total_J", "E_drag_only_J"):
            w = g.pivot_table(index="individual_id", columns="buzz_type", values=col)
            summary.append({
                "variant": vname, "quantity": col,
                "A_MJ": w["A"].mean() / 1e6, "B_MJ": w["B"].mean() / 1e6,
                "B_over_A": w["B"].mean() / w["A"].mean(),
                "whales_B_gt_A": int((w["B"] > w["A"]).sum()), "n_whales": len(w),
                "acc_share_of_mech_work": g.acc_work_J.sum() / (g.acc_work_J + g.drag_work_J).sum(),
                "median_power_A_kW": g.loc[g.buzz_type == "A", "mean_power_W"].median() / 1e3,
                "median_power_B_kW": g.loc[g.buzz_type == "B", "mean_power_W"].median() / 1e3,
                "median_power_over_rest_A": g.loc[g.buzz_type == "A", "power_over_rest"].median(),
                "median_power_over_rest_B": g.loc[g.buzz_type == "B", "power_over_rest"].median(),
            })
    pd.DataFrame(summary).to_csv(OUT / "energy_variants_summary.csv", index=False)

    # Reproduction check against the registered energy table
    reg = pd.read_csv(ROOT / "results/dswp/buzz_energy.csv")[["event_id", "E_total_J"]]
    chk = en[en.variant == "production"].merge(reg, on="event_id", suffixes=("", "_reg"))
    rel = np.abs(chk.E_total_J / chk.E_total_J_reg - 1)

    total = {k: (v / v.sum()).round(4).tolist() for k, v in dataset.items()}
    meta = {
        "regime_order": ["fallback", "depth_derived", "clipped"],
        "step_regime_fractions": total,
        "fallback_steps_with_horizontal_speed_above_0.9": fallback_violations,
        "possibly_level_fallback_steps_classed_depth": ambiguous,
        "production_energy_reproduction": {
            "n_matched": int(len(chk)), "max_rel_diff": float(rel.max()),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
