#!/usr/bin/env python3
"""Reviewer-1 re-analysis on directly measured kinematics (public step).

Inputs are the released labels plus the steward-exported summaries
``data/dswp/{buzz,dive}_kinematics.csv``. Writes only to results/review_r1/.

A. Type contrasts on measured kinematics (vertical speed, pitch, valid OCDR
   speed, stroke effort), at buzz and whale level.
B. Classifier re-test with measured kinematics in place of reconstructed speed.
C. Energetics without assumed speed: drag at valid OCDR speed (13.5 t, no
   acceleration term) and a stroke-effort index.
D. Dive budgets and inter-dive interval / dive duration versus Type-B share.
E. Discreteness: posterior distribution and parametric-bootstrap LRT (k=1 vs 2).
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dswp.classification import FEATURES, classify_gmm  # noqa: E402
from dswp.energetics import EnergyParameters, energy_from_speed_series  # noqa: E402

OUT = ROOT / "results" / "review_r1"
FEMALE = replace(EnergyParameters(), body_mass_kg=13_500.0, body_length_m=11.0, skull_width_m=1.375)
EFF = FEMALE.eta_metabolic * FEMALE.eta_propulsive
RNG_SEED = 20261122


def whale_contrast(ev, col):
    ab = ev[ev.buzz_type.isin(["A", "B"])].dropna(subset=[col])
    per = ab.pivot_table(index="individual_id", columns="buzz_type", values=col, aggfunc="median")
    both = per.dropna()
    p = wilcoxon(both.B, both.A).pvalue if len(both) >= 5 else np.nan
    return {
        "metric": col,
        "n_A": int((ab.buzz_type == "A").sum()), "n_B": int((ab.buzz_type == "B").sum()),
        "n_unassigned": int(ev.loc[ev.buzz_type == "?", col].notna().sum()),
        "median_A": ab.loc[ab.buzz_type == "A", col].median(),
        "median_B": ab.loc[ab.buzz_type == "B", col].median(),
        "median_unassigned": ev.loc[ev.buzz_type == "?", col].median(),
        "whales_with_both": len(both), "whales_B_gt_A": int((both.B > both.A).sum()),
        "wilcoxon_p": p,
    }


def quantile_normal(x):
    from sklearn.preprocessing import QuantileTransformer

    return QuantileTransformer(
        n_quantiles=len(x), output_distribution="normal", random_state=0
    ).fit_transform(x)


def gmm(x, k, n_init=10, seed=1234, tol=1e-3):
    from sklearn.mixture import GaussianMixture

    return GaussianMixture(
        k, covariance_type="full", n_init=n_init, init_params="kmeans", random_state=seed,
        tol=tol, max_iter=2000,
    ).fit(x)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    labels = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    kin = pd.read_csv(ROOT / "data/dswp/buzz_kinematics.csv")
    dives = pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv")
    ev = labels.merge(kin, on="event_id", validate="one_to_one")
    ev["stroke_effort_deg_s"] = ev.buzz_stroke_rms_deg * ev.buzz_duration_s
    summary = {}

    # A. contrasts --------------------------------------------------------
    metrics = [
        "buzz_vertical_speed_m_s", "buzz_abs_pitch_deg", "buzz_ocdr45_coverage",
        "buzz_ocdr45_speed_m_s", "buzz_ocdr30_speed_m_s", "buzz_stroke_rms_deg",
        "stroke_effort_deg_s", "pre_vertical_speed_m_s", "pre_ocdr45_speed_m_s",
        "pre_stroke_rms_deg", "avg_roll_speed_deg_s",
    ]
    contrasts = pd.DataFrame([whale_contrast(ev, m) for m in metrics])
    contrasts.to_csv(OUT / "kinematics_type_contrasts.csv", index=False)
    cover = ev.groupby("buzz_type").agg(
        share_ocdr45_any=("buzz_ocdr45_coverage", lambda s: (s > 0).mean()),
        share_ocdr45_half=("buzz_ocdr45_coverage", lambda s: (s >= 0.5).mean()),
        share_ocdr30_half=("buzz_ocdr30_coverage", lambda s: (s >= 0.5).mean()),
    )
    cover.to_csv(OUT / "ocdr_coverage_by_type.csv")
    ok = ev.dropna(subset=["buzz_stroke_rms_deg", "buzz_ocdr45_speed_m_s"])
    rho = spearmanr(ok.buzz_stroke_rms_deg, ok.buzz_ocdr45_speed_m_s)
    summary["stroke_vs_ocdr45_speed_spearman"] = {
        "rho": rho.statistic, "p": rho.pvalue, "n": len(ok)
    }
    # stroke effort within body-angle bands (separates effort from posture)
    from scipy.stats import mannwhitneyu

    ab = ev[ev.buzz_type.isin(["A", "B"])].dropna(subset=["buzz_stroke_rms_deg", "buzz_abs_pitch_deg"])
    posture_rows = []
    for band, g in ab.groupby(pd.cut(ab.buzz_abs_pitch_deg, [0, 15, 30, 45, 90]), observed=True):
        a = g.loc[g.buzz_type == "A", "buzz_stroke_rms_deg"]
        b = g.loc[g.buzz_type == "B", "buzz_stroke_rms_deg"]
        posture_rows.append({
            "abs_pitch_deg": str(band), "n_A": len(a), "n_B": len(b),
            "median_A": a.median(), "median_B": b.median(), "ratio_B_A": b.median() / a.median(),
            "mann_whitney_p": mannwhitneyu(b, a).pvalue if min(len(a), len(b)) > 10 else np.nan,
        })
    pd.DataFrame(posture_rows).to_csv(OUT / "stroke_by_posture.csv", index=False)
    # stroke effort relative to each dive's bottom-phase baseline
    ev = ev.merge(dives[["dive_id", "bottom_stroke_rms_deg"]], on="dive_id", how="left")
    ev["stroke_rel_bottom"] = ev.buzz_stroke_rms_deg / ev.bottom_stroke_rms_deg
    ev["pre_stroke_rel_bottom"] = ev.pre_stroke_rms_deg / ev.bottom_stroke_rms_deg
    rel = pd.DataFrame([whale_contrast(ev, m) for m in ("stroke_rel_bottom", "pre_stroke_rel_bottom")])
    rel.to_csv(OUT / "stroke_relative_to_bottom.csv", index=False)

    # B. classifier re-test -----------------------------------------------
    registered = classify_gmm(ev, features=FEATURES)
    summary["registered_labels_reproduced"] = bool((registered == ev.buzz_type).all())
    rows = []
    variants = {
        "registered_constant_speed_3d": FEATURES,
        "measured_vertical_speed": ("ramp_up_duration_s", "buzz_vertical_speed_m_s"),
        "stroke_effort": ("ramp_up_duration_s", "buzz_stroke_rms_deg"),
        "vertical_speed_plus_stroke": (
            "ramp_up_duration_s", "buzz_vertical_speed_m_s", "buzz_stroke_rms_deg"
        ),
    }
    from sklearn.metrics import cohen_kappa_score

    for name, feats in variants.items():
        lab = classify_gmm(ev, features=feats)
        both = lab.isin(["A", "B"]) & ev.buzz_type.isin(["A", "B"])
        x = quantile_normal(ev.dropna(subset=list(feats))[list(feats)].to_numpy())
        bic = [gmm(x, k, tol=1e-7).bic(x) for k in (1, 2, 3, 4)]  # converged EM
        rows.append({
            "variant": name, "features": "+".join(feats),
            "n_A": int((lab == "A").sum()), "n_B": int((lab == "B").sum()),
            "n_unassigned": int((lab == "?").sum()),
            "both_confident": int(both.sum()),
            "agreement_with_registered": float((lab[both] == ev.buzz_type[both]).mean()),
            "kappa_with_registered": float(cohen_kappa_score(lab[both], ev.buzz_type[both])),
            **{f"bic_k{k}": b for k, b in zip((1, 2, 3, 4), bic)},
            "best_k": int(np.argmin(bic)) + 1,
        })
    pd.DataFrame(rows).to_csv(OUT / "classifier_kinematic_retest.csv", index=False)
    r = spearmanr(ev.avg_speed_3d_m_s, ev.buzz_vertical_speed_m_s, nan_policy="omit")
    summary["registered_speed_vs_measured_vertical_speed_spearman"] = r.statistic

    # C. energetics without assumed speed ---------------------------------
    energy_rows = []
    for thr in (45, 30):
        sub = ev[(ev[f"buzz_ocdr{thr}_coverage"] >= 0.5) & ev.buzz_type.isin(["A", "B"])]
        for e in sub.itertuples():
            n = max(3, int(round(e.buzz_duration_s * 25)))
            t = np.arange(n) / 25.0
            v = np.full(n, getattr(e, f"buzz_ocdr{thr}_speed_m_s"))
            out = energy_from_speed_series(t, v, parameters=FEMALE)
            energy_rows.append({
                "event_id": e.event_id, "individual_id": e.individual_id,
                "buzz_type": e.buzz_type, "threshold_deg": thr,
                "speed_m_s": v[0], "duration_s": out["capture_duration_s"],
                "E_drag_rest_J": out["drag_work_J"] / EFF + out["E_metabolic_rest_J"],
                "power_W": (out["drag_work_J"] / EFF + out["E_metabolic_rest_J"])
                / out["capture_duration_s"],
                "rest_W": out["E_metabolic_rest_J"] / out["capture_duration_s"],
            })
    en = pd.DataFrame(energy_rows)
    en.to_csv(OUT / "energy_ocdr_events.csv", index=False)
    esum = []
    for thr, g in en.groupby("threshold_deg"):
        w = g.pivot_table(index="individual_id", columns="buzz_type", values="E_drag_rest_J").dropna()
        esum.append({
            "basis": f"drag at OCDR speed, |pitch|>={thr}, coverage>=0.5, 13.5 t",
            "n_A": int((g.buzz_type == "A").sum()), "n_B": int((g.buzz_type == "B").sum()),
            "whales_with_both": len(w),
            "A_kJ": w.A.mean() / 1e3 if len(w) else np.nan,
            "B_kJ": w.B.mean() / 1e3 if len(w) else np.nan,
            "B_over_A": w.B.mean() / w.A.mean() if len(w) else np.nan,
            "whales_B_gt_A": int((w.B > w.A).sum()),
            "median_power_over_rest": float((g.power_W / g.rest_W).median()),
        })
    for col in ("buzz_stroke_rms_deg", "stroke_effort_deg_s"):
        w = ev[ev.buzz_type.isin(["A", "B"])].pivot_table(
            index="individual_id", columns="buzz_type", values=col, aggfunc="mean"
        ).dropna()
        esum.append({
            "basis": f"stroke index: {col}", "n_A": int((ev.buzz_type == "A").sum()),
            "n_B": int((ev.buzz_type == "B").sum()), "whales_with_both": len(w),
            "A_kJ": np.nan, "B_kJ": np.nan, "B_over_A": w.B.mean() / w.A.mean(),
            "whales_B_gt_A": int((w.B > w.A).sum()), "median_power_over_rest": np.nan,
        })
    pd.DataFrame(esum).to_csv(OUT / "energy_rebuilt_summary.csv", index=False)

    # D. dive budgets -----------------------------------------------------
    counts = ev.pivot_table(index="dive_id", columns="buzz_type", values="event_id",
                            aggfunc="count", fill_value=0)
    effort = ev.pivot_table(index="dive_id", columns="buzz_type", values="stroke_effort_deg_s",
                            aggfunc="sum", fill_value=0.0)
    budget = pd.DataFrame({
        "n_A": counts.get("A", 0), "n_B": counts.get("B", 0), "n_unassigned": counts.get("?", 0),
        "effort_A": effort.get("A", 0.0), "effort_B": effort.get("B", 0.0),
        "effort_unassigned": effort.get("?", 0.0),
    }).reset_index()
    budget["b_fraction"] = budget.n_B / (budget.n_A + budget.n_B)
    budget["b_effort_share"] = budget.effort_B / budget[["effort_A", "effort_B", "effort_unassigned"]].sum(axis=1)
    budget = budget.merge(dives, on="dive_id", how="left").merge(
        ev[["dive_id", "individual_id"]].drop_duplicates(), on="dive_id", how="left"
    )
    budget.to_csv(OUT / "dive_budget.csv", index=False)
    summary["dive_budget"] = {
        "dives": len(budget),
        "median_b_fraction": budget.b_fraction.median(),
        "median_b_effort_share": budget.b_effort_share.median(),
        "median_b_count_share_all_buzzes": float(
            (budget.n_B / budget[["n_A", "n_B", "n_unassigned"]].sum(axis=1)).median()
        ),
    }

    import statsmodels.formula.api as smf

    models = {}
    base = budget[(budget.n_A + budget.n_B) >= 5].dropna(
        subset=["b_fraction", "dive_duration_s", "max_depth_m"]
    ).assign(dive_min=lambda d: d.dive_duration_s / 60, depth_100m=lambda d: d.max_depth_m / 100)
    specs = {
        "log_interdive_all": ("np.log(interdive_interval_s) ~ b_fraction + dive_min + depth_100m",
                              base.dropna(subset=["interdive_interval_s"])),
        "log_interdive_le_30min": ("np.log(interdive_interval_s) ~ b_fraction + dive_min + depth_100m",
                                   base[base.interdive_interval_s <= 1800]),
        "dive_duration_min": ("dive_min ~ b_fraction + depth_100m", base),
    }
    for name, (formula, data) in specs.items():
        fit = None
        for method in ("lbfgs", "powell", "nm"):
            candidate = smf.mixedlm(formula, data, groups=data["individual_id"]).fit(
                reml=True, method=method, maxiter=5000
            )
            if candidate.converged:
                fit = candidate
                break
        if fit is None:  # fall back to OLS with whale-clustered standard errors
            fit = smf.ols(formula, data).fit(
                cov_type="cluster", cov_kwds={"groups": pd.factorize(data["individual_id"])[0]}
            )
        ci = fit.conf_int().loc["b_fraction"]
        models[name] = {
            "formula": formula, "n_dives": int(len(data)),
            "n_whales": int(data.individual_id.nunique()),
            "b_fraction_coef": float(fit.params["b_fraction"]),
            "ci_low": float(ci[0]), "ci_high": float(ci[1]),
            "p": float(fit.pvalues["b_fraction"]),
            "estimator": "mixedlm" if hasattr(fit, "cov_re") else "ols_cluster_whale",
        }
    summary["dive_models"] = models

    # E. discreteness -----------------------------------------------------
    x = quantile_normal(ev.dropna(subset=list(FEATURES))[list(FEATURES)].to_numpy())
    m2 = gmm(x, 2)
    post = m2.predict_proba(x).max(axis=1)
    bins = [0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 0.95, 1.0001]
    hist = np.histogram(post, bins=bins)[0]
    rng = np.random.default_rng(RNG_SEED)

    def lr(data):
        # Tight tolerance: the default EM stopping rule leaves LR errors of several units.
        two = gmm(data, 2, n_init=5, tol=1e-7).score(data)
        return 2 * len(data) * (two - gmm(data, 1, n_init=1, tol=1e-7).score(data))

    lrt = {}
    for name in ("registered_constant_speed_3d", "measured_vertical_speed", "stroke_effort"):
        feats = list(variants[name])
        xv = quantile_normal(ev.dropna(subset=feats)[feats].to_numpy())
        null_model = gmm(xv, 1, n_init=1)
        observed = lr(xv)
        null = np.array([
            lr(quantile_normal(rng.multivariate_normal(
                null_model.means_[0], null_model.covariances_[0], size=len(xv))))
            for _ in range(200)
        ])
        lrt[name] = {
            "n": len(xv), "lr_observed": float(observed),
            "null_95th": float(np.percentile(null, 95)), "null_max": float(null.max()),
            "bootstrap_p": float((1 + (null >= observed).sum()) / (1 + len(null))),
        }
    summary["discreteness"] = {
        "posterior_max_histogram_registered": dict(
            zip([f"[{a},{b})" for a, b in zip(bins[:-1], bins[1:])], hist.tolist())
        ),
        "share_posterior_below_0.75": float((post < 0.75).mean()),
        "lrt_k2_vs_k1_parametric_bootstrap_200": lrt,
    }

    (OUT / "kinematics_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    print(contrasts.round(3).to_string(index=False))
    print(cover.round(3).to_string())
    print(rel.round(3).to_string(index=False))
    print(pd.read_csv(OUT / "classifier_kinematic_retest.csv").round(3).to_string(index=False))
    print(pd.DataFrame(esum).round(3).to_string(index=False))
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
