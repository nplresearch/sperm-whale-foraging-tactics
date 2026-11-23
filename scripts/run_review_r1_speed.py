#!/usr/bin/env python3
"""Is Type B faster than Type A where swim speed can actually be measured?

Uses observed climb/descent-rate (OCDR) speed only where it is valid: body
pitch beyond a threshold (45 deg, or 30 deg) with vertical motion matching body
orientation, averaged over a stroke cycle. Writes to results/review_r1/.

1. Buzz-level mixed models: log speed ~ type + |pitch| + direction + depth,
   random intercept per whale; B/A speed ratio at matched posture.
2. Posture x direction strata with whale-level paired counts.
3. AUC of measured speed for separating B from A.
4. Agreement of the original speed variables with OCDR speed.
5. Buzz-centred OCDR-speed and stroke profiles (2-s bins).
6. Drag-based cost at measured speed (13.5 t, no acceleration term), matched.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import mannwhitneyu, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dswp.energetics import EnergyParameters, energy_from_speed_series  # noqa: E402

OUT = ROOT / "results" / "review_r1"
FEMALE = replace(EnergyParameters(), body_mass_kg=13_500.0, body_length_m=11.0, skull_width_m=1.375)
EFF = FEMALE.eta_metabolic * FEMALE.eta_propulsive


def mixed(formula, data):
    for method in ("lbfgs", "powell", "nm"):
        fit = smf.mixedlm(formula, data, groups=data["individual_id"]).fit(
            reml=True, method=method, maxiter=5000
        )
        if fit.converged:
            return fit, "mixedlm"
    fit = smf.ols(formula, data).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(data["individual_id"])[0]}
    )
    return fit, "ols_cluster_whale"


def ratio_row(name, fit, estimator, data, term="C(buzz_type)[T.B]"):
    lo, hi = fit.conf_int().loc[term]
    return {
        "model": name, "estimator": estimator, "n_A": int((data.buzz_type == "A").sum()),
        "n_B": int((data.buzz_type == "B").sum()), "n_whales": int(data.individual_id.nunique()),
        "B_over_A": float(np.exp(fit.params[term])), "ci_low": float(np.exp(lo)),
        "ci_high": float(np.exp(hi)), "p": float(fit.pvalues[term]),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    labels = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    kin = pd.read_csv(ROOT / "data/dswp/buzz_kinematics.csv")
    prof = pd.read_csv(ROOT / "data/dswp/buzz_kinematic_profiles.csv")
    ev = labels.merge(kin, on="event_id", validate="one_to_one")
    ev["direction"] = np.where(ev.buzz_pitch_deg < 0, "descending", "ascending")
    ev["depth_100m"] = ev.avg_depth_m / 100
    ab = ev[ev.buzz_type.isin(["A", "B"])].copy()
    summary, models, strata = {}, [], []

    for thr in (45, 30):
        sub = ab[(ab[f"buzz_ocdr{thr}_coverage"] >= 0.5)].dropna(
            subset=[f"buzz_ocdr{thr}_speed_m_s", "buzz_abs_pitch_deg"]
        ).assign(speed=lambda d: d[f"buzz_ocdr{thr}_speed_m_s"])
        for name, formula in {
            "unadjusted": "np.log(speed) ~ C(buzz_type)",
            "matched_posture_direction_depth":
                "np.log(speed) ~ C(buzz_type) + buzz_abs_pitch_deg + C(direction) + depth_100m",
        }.items():
            fit, est = mixed(formula, sub)
            models.append({"threshold_deg": thr, **ratio_row(name, fit, est, sub)})

        # strata
        bands = pd.cut(sub.buzz_abs_pitch_deg, [thr, 45, 60, 90] if thr < 45 else [45, 60, 90])
        for (band, direction), g in sub.groupby([bands, "direction"], observed=True):
            a, b = g[g.buzz_type == "A"].speed, g[g.buzz_type == "B"].speed
            w = g.pivot_table(index="individual_id", columns="buzz_type", values="speed",
                              aggfunc="median").dropna()
            strata.append({
                "threshold_deg": thr, "abs_pitch_deg": str(band), "direction": direction,
                "n_A": len(a), "n_B": len(b), "median_A": a.median(), "median_B": b.median(),
                "whales_with_both": len(w), "whales_B_gt_A": int((w.B > w.A).sum()) if len(w) else 0,
                "mann_whitney_p": mannwhitneyu(b, a).pvalue if min(len(a), len(b)) >= 5 else np.nan,
            })
        u = mannwhitneyu(sub[sub.buzz_type == "B"].speed, sub[sub.buzz_type == "A"].speed)
        summary[f"auc_B_vs_A_ocdr{thr}"] = float(
            u.statistic / ((sub.buzz_type == "B").sum() * (sub.buzz_type == "A").sum())
        )

        # original speed variables vs measured speed
        for col in ("avg_speed_3d_m_s", "pitch_adaptive_speed_3d_m_s"):
            ok = sub.dropna(subset=[col])
            per_whale = [
                spearmanr(g[col], g.speed).statistic
                for _, g in ok.groupby("individual_id") if len(g) >= 10
            ]
            summary[f"{col}_vs_ocdr{thr}"] = {
                "spearman_pooled": float(spearmanr(ok[col], ok.speed).statistic),
                "spearman_within_whale_median": float(np.nanmedian(per_whale)),
                "whales": len(per_whale), "n": len(ok),
                "median_difference_m_s": float((ok[col] - ok.speed).median()),
            }

        # drag-based cost at measured speed
        rows = []
        for e in sub.itertuples():
            n = max(3, int(round(e.buzz_duration_s * 25)))
            out = energy_from_speed_series(np.arange(n) / 25.0, np.full(n, e.speed), parameters=FEMALE)
            energy = out["drag_work_J"] / EFF + out["E_metabolic_rest_J"]
            rows.append({"event_id": e.event_id, "energy_J": energy,
                         "power_W": energy / out["capture_duration_s"]})
        sub = sub.merge(pd.DataFrame(rows), on="event_id")
        for name, formula in {
            "energy_per_buzz_matched": "np.log(energy_J) ~ C(buzz_type) + buzz_abs_pitch_deg + C(direction) + depth_100m",
            "power_matched": "np.log(power_W) ~ C(buzz_type) + buzz_abs_pitch_deg + C(direction) + depth_100m",
        }.items():
            fit, est = mixed(formula, sub)
            models.append({"threshold_deg": thr, **ratio_row(name, fit, est, sub)})

    pd.DataFrame(models).to_csv(OUT / "speed_matched_models.csv", index=False)
    pd.DataFrame(strata).to_csv(OUT / "speed_strata.csv", index=False)

    # buzz-centred profiles: whale-level means per bin and type
    p = prof.merge(labels[["event_id", "individual_id", "buzz_type"]], on="event_id")
    p = p[p.buzz_type.isin(["A", "B"])]
    p["direction"] = np.where(p.pitch_deg < 0, "descending", "ascending")
    prof_rows = []
    for col in ("ocdr45_speed_m_s", "ocdr30_speed_m_s", "stroke_rms_deg"):
        w = p.dropna(subset=[col]).groupby(["bin_start_s", "buzz_type", "individual_id"])[col].mean()
        for (b, t), g in w.groupby(level=[0, 1]):
            prof_rows.append({
                "variable": col, "bin_start_s": b, "buzz_type": t, "whales": len(g),
                "mean": g.mean(), "sem": g.std(ddof=1) / np.sqrt(len(g)) if len(g) > 1 else np.nan,
                "n_buzz_bins": int(p.loc[(p.bin_start_s == b) & (p.buzz_type == t), col].notna().sum()),
            })
    pd.DataFrame(prof_rows).to_csv(OUT / "speed_profiles.csv", index=False)

    (OUT / "speed_summary.json").write_text(json.dumps(summary, indent=2))
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    print(pd.DataFrame(models).round(3).to_string(index=False))
    print(pd.DataFrame(strata).round(3).to_string(index=False))
    print(json.dumps(summary, indent=2))
    pr = pd.DataFrame(prof_rows)
    print(pr[pr.variable == "ocdr30_speed_m_s"].pivot(index="bin_start_s", columns="buzz_type",
                                                       values=["mean", "whales"]).round(2).to_string())


if __name__ == "__main__":
    main()
