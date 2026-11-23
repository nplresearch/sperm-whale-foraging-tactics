#!/usr/bin/env python3
"""Reviewer-1 revision: tests of foraging-theory predictions (post hoc).

Optimal diving / patch models (Houston & Carbone 1992; Thompson & Fedak 2001)
treat a dive as an oxygen-limited patch visit. Prey-choice models predict that
costly options are reserved for valuable prey and depend on encounter rate.

DSWP tests (released labels + steward dive timing):
  D1  early encounter rate predicts longer remaining bottom time;
  D2  later first buzz predicts shorter bottom time;
  D3  a larger Type-B share predicts shorter dives and bottom phases;
  D4  Type B is more often the last buzz of a dive, at matched time in dive;
  D5  after a terminal Type B the whale leaves the bottom sooner;
  C1  tactic choice depends on local encounter rate (prey-choice model);
  C2  tactic use changes through the dive (oxygen depletion).
Azores test (optional, needs the four public Dryad files):
  P1  Type B targets give stronger range-corrected echoes (larger prey).

Writes only to results/review_r1/. All tests are reported, whatever the sign.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import mannwhitneyu, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "results" / "review_r1"
SOUND_SPEED_M_S = 1500.0


def mixed(formula, data, term):
    for method in ("lbfgs", "powell", "nm"):
        fit = smf.mixedlm(formula, data, groups=data["individual_id"]).fit(
            reml=True, method=method, maxiter=5000
        )
        if fit.converged:
            break
    lo, hi = fit.conf_int().loc[term]
    return {"formula": formula, "estimator": "mixedlm" if fit.converged else "mixedlm (not converged)",
            "n": int(len(data)), "whales": int(data.individual_id.nunique()),
            "coef": float(fit.params[term]), "ci_low": float(lo), "ci_high": float(hi),
            "p": float(fit.pvalues[term])}


def gee_logit(formula, data, terms):
    fit = smf.gee(formula, groups="individual_id", data=data, family=sm.families.Binomial(),
                  cov_struct=sm.cov_struct.Exchangeable()).fit()
    ci = fit.conf_int()
    return {"formula": formula, "estimator": "GEE logit, exchangeable within whale",
            "n": int(len(data)), "whales": int(data.individual_id.nunique()),
            **{t: {"odds_ratio": float(np.exp(fit.params[t])), "ci_low": float(np.exp(ci.loc[t, 0])),
                   "ci_high": float(np.exp(ci.loc[t, 1])), "p": float(fit.pvalues[t])} for t in terms}}


def dswp_tests():
    ev = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    dives = pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv")
    dives = dives.dropna(subset=["dive_duration_s", "bottom_start_s", "bottom_end_s", "max_depth_m"])
    ev = ev.merge(dives, on=["dive_id", "deployment_id"], how="inner")
    ev = ev.sort_values(["dive_id", "buzz_start_s"]).reset_index(drop=True)
    ev["depth_100m"] = ev.max_depth_m / 100
    ev["rel_time"] = ev.buzz_start_s / ev.dive_duration_s
    whale = ev.groupby("dive_id").individual_id.first()
    out = {}

    # D1, D2: patch quality and bottom time
    d = dives.set_index("dive_id").assign(individual_id=whale).dropna(subset=["individual_id"])
    d["bottom_min"] = (d.bottom_end_s - d.bottom_start_s) / 60
    d["dive_min"] = d.dive_duration_s / 60
    d["depth_100m"] = d.max_depth_m / 100
    first = ev.groupby("dive_id").buzz_start_s.min()
    d["first_buzz_min"] = first / 60
    for w in (180, 300, 480):
        early = ev[(ev.buzz_start_s >= ev.bottom_start_s) & (ev.buzz_start_s < ev.bottom_start_s + w)]
        dd = d.assign(n_early=early.groupby("dive_id").size()).fillna({"n_early": 0})
        dd = dd[(dd.bottom_end_s - dd.bottom_start_s) > w + 60].copy()
        dd["remaining_min"] = (dd.bottom_end_s - dd.bottom_start_s - w) / 60
        out[f"D1_early_rate_{w}s"] = mixed("remaining_min ~ n_early + depth_100m", dd.reset_index(), "n_early")
    out["D2_first_buzz_latency"] = mixed("bottom_min ~ first_buzz_min + depth_100m", d.reset_index(), "first_buzz_min")
    # A long descent delays the first buzz and uses oxygen: control for it, and
    # time the first buzz from the start of the bottom phase instead.
    d["descent_min"] = d.bottom_start_s / 60
    d["first_buzz_from_bottom_min"] = (first - d.bottom_start_s) / 60
    out["D2_latency_with_descent"] = mixed(
        "bottom_min ~ first_buzz_min + descent_min + depth_100m", d.reset_index(), "first_buzz_min")
    out["D2_latency_from_bottom_start"] = mixed(
        "bottom_min ~ first_buzz_from_bottom_min + depth_100m", d.reset_index(), "first_buzz_from_bottom_min")

    # D3: Type-B share and dive / bottom duration
    ab = ev[ev.buzz_type.isin(["A", "B"])]
    share = ab.groupby("dive_id").buzz_type.agg(lambda s: (s == "B").mean())
    n_cls = ab.groupby("dive_id").size()
    dd = d.assign(b_share=share, n_classified=n_cls, n_buzz=ev.groupby("dive_id").size())
    dd = dd[dd.n_classified >= 5].reset_index()
    for y in ("dive_min", "bottom_min"):
        out[f"D3_{y}_vs_b_share"] = mixed(f"{y} ~ b_share + np.log(n_buzz) + depth_100m", dd, "b_share")

    # D4: terminal buzz, matched for time in dive
    ev["is_last"] = (ev.groupby("dive_id").buzz_start_s.transform("max") == ev.buzz_start_s).astype(int)
    abt = ev[ev.buzz_type.isin(["A", "B"])].assign(is_b=lambda x: (x.buzz_type == "B").astype(int))
    out["D4_terminal_raw"] = {t: float(abt.loc[abt.buzz_type == t, "is_last"].mean()) for t in ("A", "B")}
    out["D4_terminal_matched"] = gee_logit("is_last ~ is_b + rel_time + depth_100m", abt, ["is_b"])
    late = abt[abt.rel_time >= abt.rel_time.quantile(2 / 3)]
    out["D4_terminal_last_third"] = gee_logit("is_last ~ is_b + rel_time + depth_100m", late, ["is_b"])

    # D5: giving-up time after the last buzz
    last = ev[ev.is_last == 1].copy()
    last = last[last.buzz_type.isin(["A", "B"])]
    last["giving_up_min"] = np.clip(last.bottom_end_s - last.buzz_end_s, 0, None) / 60
    last["last_is_b"] = (last.buzz_type == "B").astype(int)
    out["D5_giving_up_raw_median_min"] = {t: float(last.loc[last.buzz_type == t, "giving_up_min"].median()) for t in ("A", "B")}
    out["D5_giving_up"] = mixed("giving_up_min ~ last_is_b + depth_100m", last, "last_is_b")

    # C1, C2: tactic choice vs local encounter rate and time in dive
    rows = []
    for _, g in ev.groupby("dive_id"):
        t = g.buzz_start_s.to_numpy()
        types = g.buzz_type.to_numpy()
        for i in range(len(g)):
            rows.append({"local_rate_3min": int(np.sum((t >= t[i] - 180) & (t < t[i]))),
                         "prev_type": types[i - 1] if i else "none",
                         "gap_min": (t[i] - g.buzz_end_s.to_numpy()[i - 1]) / 60 if i else np.nan})
    ev = pd.concat([ev, pd.DataFrame(rows, index=ev.index)], axis=1)
    ch = ev[ev.buzz_type.isin(["A", "B"])].assign(is_b=lambda x: (x.buzz_type == "B").astype(int))
    out["C1_local_rate"] = gee_logit(
        "is_b ~ local_rate_3min + C(prev_type) + rel_time + I(rel_time**2) + depth_100m",
        ch, ["local_rate_3min", "rel_time"])
    cg = ch.dropna(subset=["gap_min"]).query("gap_min > 0")
    out["C1_gap_since_previous"] = gee_logit(
        "is_b ~ np.log(gap_min) + C(prev_type) + rel_time + depth_100m", cg, ["np.log(gap_min)"])
    phase = pd.cut(ch.rel_time, [0, 1 / 3, 2 / 3, 1.0], labels=["first third", "middle third", "last third"])
    out["C2_b_share_by_dive_third"] = ch.groupby(phase, observed=True).is_b.mean().round(3).to_dict()
    out["C2_b_share_by_local_rate"] = ch.groupby(ch.local_rate_3min.clip(upper=4)).is_b.agg(["mean", "size"]).round(3).to_dict()

    # P: is "Type B ends dives" built into the labels by descent/ascent movement?
    kin = pd.read_csv(ROOT / "data/dswp/buzz_kinematics.csv")[["event_id", "buzz_pitch_deg", "buzz_vertical_speed_m_s"]]
    ab2 = abt.merge(kin, on="event_id", how="left")
    ab2["in_bottom"] = (ab2.buzz_start_s >= ab2.bottom_start_s) & (ab2.buzz_start_s < ab2.bottom_end_s)
    ab2["in_ascent"] = ab2.buzz_start_s >= ab2.bottom_end_s
    ab2["rel_bottom"] = (ab2.buzz_start_s - ab2.bottom_start_s) / (ab2.bottom_end_s - ab2.bottom_start_s)
    last_rows = ab2[ab2.is_last == 1]
    out["P_where_last_buzzes_fall"] = {
        t: {"n": int((last_rows.buzz_type == t).sum()),
            "share_in_ascent": float(last_rows.loc[last_rows.buzz_type == t, "in_ascent"].mean()),
            "share_in_bottom": float(last_rows.loc[last_rows.buzz_type == t, "in_bottom"].mean())}
        for t in ("A", "B")}
    out["P_phase_of_buzzes_by_type"] = ab2.assign(
        phase=np.select([ab2.buzz_start_s < ab2.bottom_start_s, ab2.in_bottom], ["descent", "bottom"], "ascent")
    ).groupby(["phase", "buzz_type"]).size().unstack().to_dict()
    bot = ab2[ab2.in_bottom].copy()
    out["P_D4_terminal_bottom_only"] = gee_logit("is_last ~ is_b + rel_time + depth_100m", bot, ["is_b"])
    out["P_D4_terminal_bottom_only"]["raw"] = {t: float(bot.loc[bot.buzz_type == t, "is_last"].mean()) for t in ("A", "B")}
    bot["is_last_bottom"] = (bot.groupby("dive_id").buzz_start_s.transform("max") == bot.buzz_start_s).astype(int)
    out["P_D4_last_bottom_buzz"] = gee_logit("is_last_bottom ~ is_b + rel_bottom + depth_100m", bot, ["is_b"])
    out["P_D4_last_bottom_buzz"]["raw"] = {t: float(bot.loc[bot.buzz_type == t, "is_last_bottom"].mean()) for t in ("A", "B")}
    vc = ab2.dropna(subset=["buzz_pitch_deg", "buzz_vertical_speed_m_s"]).assign(
        climbing=lambda x: (x.buzz_pitch_deg > 0).astype(int))
    out["P_D4_terminal_vertical_controlled"] = gee_logit(
        "is_last ~ is_b + rel_time + depth_100m + climbing + buzz_vertical_speed_m_s", vc, ["is_b", "climbing"])
    out["P_D4_terminal_vertical_controlled"]["note"] = "over-controls: Type B is largely defined by vertical speed"
    phase3 = pd.cut(bot.rel_bottom, [0, 1 / 3, 2 / 3, 1.0], labels=["first third", "middle third", "last third"])
    out["P_C2_b_share_by_bottom_third"] = bot.groupby(phase3, observed=True).is_b.mean().round(3).to_dict()
    out["P_C2_bottom_only"] = gee_logit("is_b ~ rel_bottom + I(rel_bottom**2) + depth_100m", bot,
                                        ["rel_bottom", "I(rel_bottom ** 2)"])
    cb = bot.merge(ch[["event_id", "gap_min", "prev_type"]], on="event_id", how="left").dropna(subset=["gap_min"])
    cb = cb[cb.gap_min > 0]
    out["P_C1_gap_bottom_only"] = gee_logit("is_b ~ np.log(gap_min) + C(prev_type) + rel_bottom + depth_100m",
                                            cb, ["np.log(gap_min)"])
    bshare = bot.groupby("dive_id").is_b.mean()
    nb = bot.groupby("dive_id").size()
    dd2 = d.assign(b_share_bottom=bshare, n_bottom=nb, n_buzz=ev.groupby("dive_id").size())
    dd2 = dd2[dd2.n_bottom >= 5].reset_index()
    for y in ("dive_min", "bottom_min"):
        out[f"P_D3_{y}_vs_bottom_b_share"] = mixed(f"{y} ~ b_share_bottom + np.log(n_buzz) + depth_100m",
                                                   dd2, "b_share_bottom")
    return out


def azores_tests(directory: Path):
    from validation.azores import (classify_nearest_corners, extract_azores_buzz_features,
                                   load_azores_sources)
    sources = load_azores_sources(directory)
    feats = classify_nearest_corners(extract_azores_buzz_features(sources))
    echo = sources["echo"]

    # Is column 3 an echo level? Between a stream's endpoint echoes, a fixed target's received
    # level should rise about 40 dB per tenfold drop in range.
    slopes = []
    for _, row in echo.iterrows():
        for stream in np.atleast_1d(row["prey"]):
            s = np.atleast_2d(np.asarray(stream, float))
            if s.shape[0] < 2 or s.shape[1] < 3:  # streams store 2-3 endpoint echoes
                continue
            r = s[:, 1] * SOUND_SPEED_M_S / 2
            if np.nanmax(r) / np.nanmin(r) < 1.5:
                continue
            slopes.append(np.polyfit(np.log10(r), s[:, 2], 1)[0])

    rows = []
    for _, b in feats.iterrows():
        e = echo.iloc[int(b.dive_no) - 1]
        mid = np.asarray(e["prey_midtime"], float)
        dist = np.asarray(e["prey_dist"], float)
        sel = np.where((mid >= b._buzz_start_s - 10) & (mid <= b._buzz_end_s + 10))[0]
        ts, near = [], (np.nan, np.inf)
        for k in sel:
            s = np.atleast_2d(np.asarray(np.atleast_1d(e["prey"])[k], float))
            pre = s[s[:, 0] < b._click_first_s]          # regular clicks only
            if len(pre) == 0:
                continue
            value = float(np.median(pre[:, 2] + 40 * np.log10(pre[:, 1] * SOUND_SPEED_M_S / 2)))
            ts.append(value)
            if dist[k] < near[1]:
                near = (value, dist[k])
        rows.append({"type": b.operative_type, "b_minus_a": float(b.distance_to_a - b.distance_to_b),
                     "ts_max": max(ts) if ts else np.nan, "ts_median": float(np.median(ts)) if ts else np.nan,
                     "ts_nearest": near[0]})
    t = pd.DataFrame(rows)
    res = {"echo_level_check": {"streams": len(slopes), "median_slope_db_per_decade": float(np.median(slopes)),
                                "iqr": [float(np.percentile(slopes, 25)), float(np.percentile(slopes, 75))],
                                "expected_if_echo_level": -40.0}}
    for col in ("ts_nearest", "ts_max", "ts_median"):
        a = t.loc[t.type == "A", col].dropna()
        bb = t.loc[t.type == "B", col].dropna()
        rho = spearmanr(t.b_minus_a, t[col], nan_policy="omit")
        res[col] = {"n_A": len(a), "n_B": len(bb), "median_A_db": float(a.median()), "median_B_db": float(bb.median()),
                    "mann_whitney_p": float(mannwhitneyu(bb, a).pvalue) if min(len(a), len(bb)) >= 3 else np.nan,
                    "spearman_rho_vs_B_likeness": float(rho.statistic), "spearman_p": float(rho.pvalue)}
    return res


def transit_tests():
    """Q: are descent/ascent 'Type B' buzzes acoustically Type B, and is there a
    per-buzz oxygen cost of Type B at dive scale?"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    ev = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    dives = pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv")
    kin = pd.read_csv(ROOT / "data/dswp/buzz_kinematics.csv")
    e = (ev.merge(dives, on=["dive_id", "deployment_id"], how="inner")
           .merge(kin[["event_id", "buzz_stroke_rms_deg", "buzz_vertical_speed_m_s"]], on="event_id", how="left")
           .dropna(subset=["bottom_start_s", "bottom_end_s"]))
    e["phase"] = np.select([e.buzz_start_s < e.bottom_start_s, e.buzz_start_s < e.bottom_end_s],
                           ["descent", "bottom"], "ascent")
    out = {}
    for c in ("ramp_up_duration_s", "buzz_duration_s"):
        e[f"log_{c}"] = np.log(e[c].clip(lower=0.05))
    feature_sets = {
        "acoustic_all": ["log_ramp_up_duration_s", "log_buzz_duration_s", "median_click_rate_hz", "max_click_rate_hz"],
        "acoustic_without_ramp_up": ["log_buzz_duration_s", "median_click_rate_hz", "max_click_rate_hz"],
    }
    lab = e[e.buzz_type.isin(["A", "B"])].dropna(subset=feature_sets["acoustic_all"]).copy()
    lab["is_b"] = (lab.buzz_type == "B").astype(int)
    bottom = lab[lab.phase == "bottom"]
    for name, feats in feature_sets.items():
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
        cv = cross_val_predict(model, bottom[feats], bottom.is_b, groups=bottom.individual_id,
                               cv=GroupKFold(n_splits=5), method="predict_proba")[:, 1]
        model.fit(bottom[feats], bottom.is_b)
        res = {"bottom_cv_auc": float(roc_auc_score(bottom.is_b, cv)),
               "bottom_cv_accuracy": float(((cv > 0.5) == bottom.is_b).mean())}
        for ph in ("descent", "bottom", "ascent"):
            sub = lab[lab.phase == ph]
            pb = cv if ph == "bottom" else model.predict_proba(sub[feats])[:, 1]
            pred_b = pb > 0.5
            res[ph] = {"n": int(len(sub)), "labelled_B": int(sub.is_b.sum()),
                       "acoustically_B_among_labelled_B": float(pred_b[sub.is_b.to_numpy() == 1].mean()),
                       "acoustically_B_among_labelled_A": float(pred_b[sub.is_b.to_numpy() == 0].mean()),
                       "agreement": float((pred_b == sub.is_b.to_numpy()).mean())}
        out[f"Q1_{name}"] = res

    prof = lab.groupby(["phase", "buzz_type"]).agg(
        n=("event_id", "size"), ramp_up_s=("ramp_up_duration_s", "median"), buzz_s=("buzz_duration_s", "median"),
        median_click_hz=("median_click_rate_hz", "median"), stroke_deg=("buzz_stroke_rms_deg", "median"),
        roll_deg_s=("avg_roll_speed_deg_s", "median"), vertical_m_s=("buzz_vertical_speed_m_s", "median"))
    prof.round(3).to_csv(OUT / "transit_buzz_profile.csv")
    out["Q2_profile"] = {f"{a}_{b}": v for (a, b), v in prof.round(3).to_dict(orient="index").items()}
    # effort: ascent/descent Type B vs bottom Type B, whale-level
    bb = lab[lab.buzz_type == "B"].pivot_table(index="individual_id", columns="phase",
                                               values="buzz_stroke_rms_deg", aggfunc="median")
    for ph in ("ascent", "descent"):
        both = bb[["bottom", ph]].dropna()
        from scipy.stats import wilcoxon
        out[f"Q2_stroke_B_{ph}_vs_bottom"] = {"whales": int(len(both)), "median_bottom": float(both.bottom.median()),
                                             f"median_{ph}": float(both[ph].median()),
                                             "wilcoxon_p": float(wilcoxon(both[ph], both.bottom).pvalue) if len(both) >= 5 else np.nan}

    # Q3: per-buzz oxygen cost at dive scale: does each B cost more dive time / recovery than each A?
    counts = e.pivot_table(index="dive_id", columns=["phase", "buzz_type"], values="event_id",
                           aggfunc="count", fill_value=0)
    d = dives.set_index("dive_id").copy()
    d["individual_id"] = e.groupby("dive_id").individual_id.first()
    d = d.dropna(subset=["individual_id", "dive_duration_s", "bottom_start_s", "bottom_end_s", "max_depth_m"])
    for scope, phases in {"bottom": ["bottom"], "all": ["descent", "bottom", "ascent"]}.items():
        dd = d.copy()
        for t, col in (("A", "n_a"), ("B", "n_b"), ("?", "n_u")):
            dd[col] = sum(counts[(ph, t)] if (ph, t) in counts.columns else 0 for ph in phases)
        dd = dd.assign(dive_min=dd.dive_duration_s / 60, bottom_min=(dd.bottom_end_s - dd.bottom_start_s) / 60,
                       depth_100m=dd.max_depth_m / 100, log_interval=np.log(dd.interdive_interval_s)).reset_index()
        for y in ("dive_min", "bottom_min", "log_interval"):
            data = dd.dropna(subset=[y])
            fit = None
            for method in ("lbfgs", "powell", "nm"):
                fit = smf.mixedlm(f"{y} ~ n_b + n_a + n_u + depth_100m", data, groups=data["individual_id"]).fit(
                    reml=True, method=method, maxiter=5000)
                if fit.converged:
                    break
            diff = fit.params["n_b"] - fit.params["n_a"]
            cov = fit.cov_params()
            se = float(np.sqrt(cov.loc["n_b", "n_b"] + cov.loc["n_a", "n_a"] - 2 * cov.loc["n_b", "n_a"]))
            from scipy.stats import norm
            out[f"Q3_{scope}_{y}"] = {"n_dives": int(len(data)), "per_B": float(fit.params["n_b"]),
                                      "per_A": float(fit.params["n_a"]), "B_minus_A": float(diff),
                                      "ci_low": float(diff - 1.96 * se), "ci_high": float(diff + 1.96 * se),
                                      "p": float(2 * norm.sf(abs(diff / se)))}
    return out


def energy_tests():
    """E: genuine bottom-phase Type B and dive length; dive-level stroke effort as
    an energy proxy linked to dive length and recovery time."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    ev = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    dives = pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv")
    kin = pd.read_csv(ROOT / "data/dswp/buzz_kinematics.csv")
    e = (ev.merge(dives, on=["dive_id", "deployment_id"], how="inner")
           .merge(kin[["event_id", "buzz_stroke_rms_deg"]], on="event_id", how="left")
           .dropna(subset=["bottom_start_s", "bottom_end_s", "dive_duration_s"]))
    bot = e[(e.buzz_start_s >= e.bottom_start_s) & (e.buzz_start_s < e.bottom_end_s)].copy()
    for c in ("ramp_up_duration_s", "buzz_duration_s"):
        bot[f"log_{c}"] = np.log(bot[c].clip(lower=0.05))
    feats = ["log_ramp_up_duration_s", "log_buzz_duration_s", "median_click_rate_hz", "max_click_rate_hz"]
    lab = bot[bot.buzz_type.isin(["A", "B"])].dropna(subset=feats).copy()
    lab["is_b"] = (lab.buzz_type == "B").astype(int)
    lab["p_acoustic_b"] = cross_val_predict(
        make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)), lab[feats], lab.is_b,
        groups=lab.individual_id, cv=GroupKFold(n_splits=5), method="predict_proba")[:, 1]
    b = lab[lab.is_b == 1]
    med = b.groupby("individual_id").buzz_stroke_rms_deg.median()
    lab["b_confirmed"] = (lab.is_b == 1) & (lab.p_acoustic_b > 0.5)
    lab["b_costly"] = (lab.is_b == 1) & (lab.buzz_stroke_rms_deg >= lab.individual_id.map(med))
    lab["effort"] = lab.buzz_stroke_rms_deg * lab.buzz_duration_s

    per = lab.groupby("dive_id").agg(
        n_a=("is_b", lambda x: int((x == 0).sum())), n_b=("is_b", "sum"),
        n_b_conf=("b_confirmed", "sum"), n_b_costly=("b_costly", "sum"),
        b_effort=("effort", lambda x: float(x[lab.loc[x.index, "is_b"] == 1].sum())),
        a_effort=("effort", lambda x: float(x[lab.loc[x.index, "is_b"] == 0].sum())))
    per["n_u"] = bot[bot.buzz_type == "?"].groupby("dive_id").size().reindex(per.index).fillna(0)
    d = (dives.set_index("dive_id").join(per, how="inner")
         .assign(individual_id=e.groupby("dive_id").individual_id.first())
         .dropna(subset=["individual_id", "bottom_stroke_rms_deg", "max_depth_m"]))
    d = d.assign(dive_min=d.dive_duration_s / 60, bottom_min=(d.bottom_end_s - d.bottom_start_s) / 60,
                 depth_100m=d.max_depth_m / 100, log_interval=np.log(d.interdive_interval_s),
                 n_cls=d.n_a + d.n_b)
    d = d[d.n_cls >= 5].reset_index()
    d["share_b"] = d.n_b / d.n_cls
    d["share_b_conf"] = d.n_b_conf / d.n_cls
    d["share_b_costly"] = d.n_b_costly / d.n_cls
    d["n_b_other_conf"] = d.n_b - d.n_b_conf
    d["n_b_other_costly"] = d.n_b - d.n_b_costly
    out = {"dives": int(len(d)), "whales": int(d.individual_id.nunique()),
           "share_of_bottom_B_confirmed": float(lab.loc[lab.is_b == 1, "b_confirmed"].mean())}

    def fit(formula, data):
        for method in ("lbfgs", "powell", "nm"):
            r = smf.mixedlm(formula, data, groups=data["individual_id"]).fit(reml=True, method=method, maxiter=5000)
            if r.converged:
                return r
        return r

    def coef(r, term):
        lo, hi = r.conf_int().loc[term]
        return {"coef": float(r.params[term]), "ci_low": float(lo), "ci_high": float(hi), "p": float(r.pvalues[term])}

    def contrast(r, t1, t2):
        from scipy.stats import norm
        cv = r.cov_params()
        dlt = r.params[t1] - r.params[t2]
        se = float(np.sqrt(cv.loc[t1, t1] + cv.loc[t2, t2] - 2 * cv.loc[t1, t2]))
        return {"diff": float(dlt), "ci_low": float(dlt - 1.96 * se), "ci_high": float(dlt + 1.96 * se),
                "p": float(2 * norm.sf(abs(dlt / se)))}

    for y in ("dive_min", "bottom_min"):
        for name, share in (("labelled", "share_b"), ("confirmed", "share_b_conf"), ("costly", "share_b_costly")):
            out[f"E1_{y}_share_{name}"] = coef(fit(f"{y} ~ {share} + np.log(n_cls) + depth_100m", d), share)
        r = fit(f"{y} ~ n_b_conf + n_b_other_conf + n_a + n_u + depth_100m", d)
        out[f"E1_{y}_count_confirmedB_minus_A"] = contrast(r, "n_b_conf", "n_a")
        r = fit(f"{y} ~ n_b_costly + n_b_other_costly + n_a + n_u + depth_100m", d)
        out[f"E1_{y}_count_costlyB_minus_A"] = contrast(r, "n_b_costly", "n_a")

    # E2: dive-level stroke effort as an energy proxy
    d["stroke_z"] = (d.bottom_stroke_rms_deg - d.bottom_stroke_rms_deg.mean()) / d.bottom_stroke_rms_deg.std()
    out["E2_dive_min_vs_bottom_stroke"] = coef(fit("dive_min ~ stroke_z + depth_100m", d), "stroke_z")
    out["E2_bottom_min_vs_bottom_stroke"] = coef(fit("bottom_min ~ stroke_z + depth_100m", d), "stroke_z")
    di = d.dropna(subset=["log_interval"])
    out["E2_log_interval_vs_bottom_stroke"] = coef(fit("log_interval ~ stroke_z + dive_min + depth_100m", di), "stroke_z")
    # E3: does Type B raise dive-level effort, and does effort carry the B effect?
    out["E3_bottom_stroke_vs_share_b_conf"] = coef(fit("bottom_stroke_rms_deg ~ share_b_conf + depth_100m", d), "share_b_conf")
    r = fit("dive_min ~ share_b_conf + stroke_z + np.log(n_cls) + depth_100m", d)
    out["E3_dive_min_share_b_conf_with_stroke"] = {"share_b_conf": coef(r, "share_b_conf"), "stroke_z": coef(r, "stroke_z")}
    out["note"] = ("bottom-phase buzzes only; dives with >= 5 classified bottom buzzes; mixed models by whale. "
                   "stroke_z = dive-mean stroke RMS over the bottom phase, standardised; coefficients in minutes per SD")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--azores-dir", type=Path, help="folder with the four public Dryad .mat files")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"dswp": dswp_tests(), "transit": transit_tests(), "energy": energy_tests()}
    if args.azores_dir:
        out["azores"] = azores_tests(args.azores_dir)
    (OUT / "foraging_models.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
