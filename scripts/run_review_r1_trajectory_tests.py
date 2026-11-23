#!/usr/bin/env python3
"""Reviewer-1 revision: trajectory-scale search tests on heading-based steps.

Steps are times between heading turns (src/trajectory/heading_steps.py), so
neither the depth wobble that drives the production 25-Hz "turns" nor the
assumed horizontal speed enters. Post hoc; every result is reported.

S   sensitivity of step statistics to block length and turn threshold, and
    per-dive AIC comparison: power law vs geometric vs two-geometric mixture;
M   mode switching: are steps longer far from buzzes?
L   Lévy foraging hypothesis: exponent (and MSD slope) vs buzz rate;
A   area-restricted search: heading turn rate before vs after buzzes, and
    its decay with time since the last buzz;
V   marginal value theorem: buzz bouts as patches, residence vs travel time.
Writes results/review_r1/trajectory_tests.json and per-dive CSV.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trajectory.analysis import load_trajectory, loglog_slope, msd_curve  # noqa: E402
from trajectory.heading_steps import (  # noqa: E402
    block_headings, choose_kmin, fit_discrete_powerlaw, fit_geometric,
    fit_geometric_mixture, turn_runs,
)

FS = 25.0
OUT = ROOT / "results" / "review_r1"
PRIMARY = (5.0, 30.0)
GRID = [(b, t) for b in (2.0, 5.0, 10.0) for t in (20.0, 30.0, 45.0)]
POST_BINS = [0, 30, 60, 120, 240, np.inf]


def mixed(formula, data, term):
    for method in ("lbfgs", "powell", "nm"):
        fit = smf.mixedlm(formula, data, groups=data["individual_id"]).fit(
            reml=True, method=method, maxiter=5000)
        if fit.converged:
            break
    lo, hi = fit.conf_int().loc[term]
    return {"formula": formula, "n": int(len(data)), "whales": int(data.individual_id.nunique()),
            "coef": float(fit.params[term]), "ci_low": float(lo), "ci_high": float(hi),
            "p": float(fit.pvalues[term]), "converged": bool(fit.converged)}


def gee_logit_turn(blocks):
    # Independence working correlation; robust standard errors clustered by whale.
    fit = smf.gee("turn ~ np.log(to_buzz_s + 1)", groups="individual_id", data=blocks,
                  family=sm.families.Binomial(), cov_struct=sm.cov_struct.Independence()).fit()
    t = "np.log(to_buzz_s + 1)"
    lo, hi = np.exp(fit.conf_int().loc[t])
    return {"odds_ratio_per_log_s": float(np.exp(fit.params[t])), "ci_low": float(lo),
            "ci_high": float(hi), "p": float(fit.pvalues[t])}


def whale_wilcoxon(values: pd.Series):
    v = values.dropna()
    return {"whales": int(len(v)), "median": float(v.median()), "n_negative": int((v < 0).sum()),
            "wilcoxon_p": float(wilcoxon(v).pvalue) if len(v) >= 5 else np.nan}


def fits(durations):
    if len(durations) < 40:
        return None
    kmin = choose_kmin(durations)
    pl, ge, mx = (fit_discrete_powerlaw(durations, kmin), fit_geometric(durations, kmin),
                  fit_geometric_mixture(durations, kmin))
    aics = {"power_law": pl["aic"], "geometric": ge["aic"], "two_geometric": mx["aic"]}
    best = min(aics, key=aics.get)
    return {"kmin": kmin, "mu": pl["mu"], "n_tail": pl["n"], **{f"aic_{k}": v for k, v in aics.items()},
            "best": best, "best_by_2": best if sorted(aics.values())[1] - aics[best] > 2 else "tie"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    per = pd.read_csv(ROOT / "results/trajectory/per_dive_levy_msd.csv")
    index = pd.read_csv(ROOT / "data/dswp/trajectory_index.csv").set_index("trajectory_id")
    ev = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
    dives = pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv").set_index("dive_id")

    rows, grid_rows, step_rows, sec_rows, ars_rows = [], [], [], [], []
    block_rows, null_inputs, persist_rows, net_rows = [], [], [], []
    for _, d in per.iterrows():
        tid = d.trajectory_id
        m = index.loc[tid]
        a, b = int(m.foraging_start_index), int(m.foraging_end_index)
        xyz = load_trajectory(ROOT / "data/dswp" / m["file"])[a:b]
        t0 = a / FS                                        # segment start, s since dive start
        bz = ev[ev.trajectory_id == tid].sort_values("buzz_start_s")
        starts, ends = bz.buzz_start_s.to_numpy(), bz.buzz_end_s.to_numpy()
        in_seg = (starts >= t0) & (starts < b / FS)
        seg_min = (b - a) / FS / 60
        base = {"trajectory_id": tid, "individual_id": d.individual_id,
                "buzz_rate_per_min": in_seg.sum() / seg_min, "alpha_msd": d.alpha_msd,
                "mu_production": d.mu,
                "depth_100m": dives.max_depth_m.get(tid, np.nan) / 100}

        # Speed-independent search measures for the Lévy foraging test
        h5, _ = block_headings(xyz, FS, PRIMARY[0])
        dth = np.abs(np.angle(np.exp(1j * np.diff(h5))))
        base["turns_per_min"] = float(np.sum(dth[np.isfinite(dth)] > np.radians(PRIMARY[1])) / seg_min)
        h1, _ = block_headings(xyz, FS, 1.0)
        u = np.exp(1j * h1[: len(h1) // 60 * 60]).reshape(-1, 60)
        base["persistence_60s"] = float(np.nanmean(np.abs(np.nanmean(u, axis=1))))
        flat = xyz.copy()
        flat[:, 2] = 0.0
        base["alpha_horizontal"] = loglog_slope(msd_curve(flat))["alpha_msd"]

        # S: grid of block lengths and thresholds
        for block_s, thr in GRID:
            heads, _ = block_headings(xyz, FS, block_s)
            runs = turn_runs(heads, np.radians(thr))
            f = fits(runs[:, 1]) if len(runs) else None
            grid_rows.append({"trajectory_id": tid, "block_s": block_s, "threshold_deg": thr,
                              "n_steps": len(runs), "median_step_s": float(np.median(runs[:, 1]) * block_s) if len(runs) else np.nan,
                              **(f or {})})
            if (block_s, thr) == PRIMARY:
                rows.append({**base, "n_steps": len(runs), **(f or {})})
                # per-block turn indicator vs time to nearest buzz (no step-length bias)
                dth_b = np.abs(np.angle(np.exp(1j * np.diff(heads))))
                bt = t0 + (np.arange(1, len(heads)) + 0.5) * block_s
                inside_b = np.zeros(len(bt), bool)
                for s_, e_ in zip(starts, ends):
                    inside_b |= (bt >= s_ - block_s / 2) & (bt <= e_ + block_s / 2)
                if len(starts):
                    dist = np.minimum(np.abs(bt[:, None] - starts[None, :]), np.abs(bt[:, None] - ends[None, :]))
                    near = dist.min(axis=1)
                    nearest_id = bz.event_id.to_numpy()[dist.argmin(axis=1)]
                    okb = np.isfinite(dth_b) & ~inside_b
                    block_rows.append(pd.DataFrame({"individual_id": d.individual_id, "to_buzz_s": near[okb],
                                                    "nearest_event": nearest_id[okb],
                                                    "turn": (dth_b[okb] > np.radians(thr)).astype(int)}))
                    # R2: does a turn persist? heading 10 s before vs 10 s after the turn
                    for i in np.where(np.isfinite(dth_b) & (dth_b > np.radians(thr)) & ~inside_b)[0]:
                        if i - 2 >= 0 and i + 3 < len(heads):
                            net = abs(np.angle(np.exp(1j * (heads[i + 3] - heads[i - 2]))))
                            persist_rows.append({"individual_id": d.individual_id, "to_buzz_s": near[i],
                                                 "turn_deg": np.degrees(dth_b[i]), "net_deg": np.degrees(net)})
                null_inputs.append((runs, t0, block_s, starts, ends, b / FS))
                # M: step duration vs time to the nearest buzz (outside buzzes)
                for start, length in runs:
                    mid = t0 + (start + length / 2) * block_s
                    gaps = np.concatenate([np.abs(starts - mid), np.abs(mid - ends)]) if len(starts) else np.array([np.inf])
                    step_rows.append({"trajectory_id": tid, "individual_id": d.individual_id,
                                      "step_s": length * block_s, "to_buzz_s": float(gaps.min())})

        # A: 1-s heading turn rate
        heads1, _ = block_headings(xyz, FS, 1.0)
        rate = np.degrees(np.abs(np.angle(np.exp(1j * np.diff(heads1)))))   # deg/s, at second i+1
        sec_t = t0 + np.arange(1, len(heads1)) + 0.5
        inside = np.zeros(len(sec_t), bool)
        for s_, e_ in zip(starts, ends):
            inside |= (sec_t >= s_) & (sec_t <= e_)
        last_end = np.full(len(sec_t), np.nan)
        last_type = np.full(len(sec_t), "", dtype=object)
        for s_, e_, ty in zip(starts, ends, bz.buzz_type):
            after = sec_t > e_
            last_end[after] = e_
            last_type[after] = ty
        since = sec_t - last_end
        ok = ~inside & np.isfinite(rate) & np.isfinite(since)
        sec_rows.append(pd.DataFrame({"individual_id": d.individual_id, "since_s": since[ok],
                                      "rate": rate[ok], "last_type": last_type[ok]}))
        def circ_mean(sel):
            v = np.exp(1j * heads1[1:][sel])
            v = v[np.isfinite(v)]
            return np.angle(v.mean()) if len(v) >= 10 else np.nan

        seg_end = b / FS
        for s_, e_ in zip(starts, ends):
            if s_ - 30 >= t0 and e_ + 30 <= seg_end:
                hb = circ_mean((sec_t >= s_ - 30) & (sec_t < s_ - 10))
                ha = circ_mean((sec_t > e_ + 10) & (sec_t <= e_ + 30))
                net_rows.append({"individual_id": d.individual_id, "kind": "buzz",
                                 "net_deg": np.degrees(abs(np.angle(np.exp(1j * (ha - hb)))))})
        for tc in np.arange(t0 + 40, seg_end - 50, 10.0):
            if len(starts) and np.any((ends >= tc - 40) & (starts <= tc + 50)):
                continue
            hb = circ_mean((sec_t >= tc - 30) & (sec_t < tc - 10))
            ha = circ_mean((sec_t > tc + 15) & (sec_t <= tc + 35))
            net_rows.append({"individual_id": d.individual_id, "kind": "control",
                             "net_deg": np.degrees(abs(np.angle(np.exp(1j * (ha - hb)))))})
        for s_, e_, ty in zip(starts, ends, bz.buzz_type):
            pre = (sec_t >= s_ - 40) & (sec_t < s_ - 10) & ~inside
            post = (sec_t > e_ + 10) & (sec_t <= e_ + 40) & ~inside
            if pre.sum() >= 15 and post.sum() >= 15:
                ars_rows.append({"individual_id": d.individual_id, "type": ty,
                                 "pre": float(np.nanmean(rate[pre])), "post": float(np.nanmean(rate[post]))})

    dive_tab = pd.DataFrame(rows)
    grid = pd.DataFrame(grid_rows)
    dive_tab.to_csv(OUT / "trajectory_tests_per_dive.csv", index=False)
    out = {"primary_setting": {"block_s": PRIMARY[0], "threshold_deg": PRIMARY[1]}}

    # S
    g = grid.groupby(["block_s", "threshold_deg"])
    sens = g.agg(dives=("trajectory_id", "size"), median_steps=("n_steps", "median"),
                 median_step_s=("median_step_s", "median"), median_mu=("mu", "median"))
    for model in ("power_law", "geometric", "two_geometric"):
        sens[f"share_best_{model}"] = g.best.apply(lambda s, m=model: (s == m).sum() / s.notna().sum())
    sens.reset_index().to_csv(OUT / "trajectory_step_sensitivity.csv", index=False)
    out["S_sensitivity"] = sens.round(3).reset_index().to_dict(orient="records")
    prim = dive_tab.dropna(subset=["best"])
    out["S_primary_model_choice"] = {"dives_fitted": int(len(prim)),
                                     "best": prim.best.value_counts().to_dict(),
                                     "best_by_2_aic": prim.best_by_2.value_counts().to_dict(),
                                     "median_mu": float(prim.mu.median())}
    steps = pd.DataFrame(step_rows)
    steps.to_csv(OUT / "trajectory_steps_primary.csv", index=False)
    pooled = fits(np.round(steps.step_s / PRIMARY[0]).astype(int).to_numpy())
    out["S_pooled_fit"] = pooled
    whale_of = dive_tab.set_index("trajectory_id").individual_id
    wrows = []
    for block_s, thr in GRID:
        for whale, tids in whale_of.groupby(whale_of):
            ks = []
            for tid in tids.index:
                m = index.loc[tid]
                xyz = load_trajectory(ROOT / "data/dswp" / m["file"])[int(m.foraging_start_index):int(m.foraging_end_index)]
                ks.extend(turn_runs(block_headings(xyz, FS, block_s)[0], np.radians(thr))[:, 1])
            f = fits(np.array(ks))
            if f:
                wrows.append({"block_s": block_s, "threshold_deg": thr, "individual_id": whale, **f})
    wfit = pd.DataFrame(wrows)
    wfit.to_csv(OUT / "trajectory_step_fits_per_whale.csv", index=False)
    out["S_per_whale_model_choice"] = {
        f"{b:g}s_{t:g}deg": {"whales_fitted": int(len(g)), **g.best.value_counts().to_dict(),
                             "median_mu": round(float(g.mu.median()), 3)}
        for (b, t), g in wfit.groupby(["block_s", "threshold_deg"])}

    # M: mode switching
    rho = steps.groupby("trajectory_id").apply(
        lambda s: spearmanr(s.step_s, s.to_buzz_s).statistic if len(s) >= 20 else np.nan)
    whale_rho = rho.groupby(dive_tab.set_index("trajectory_id").individual_id).median()
    out["M_step_vs_distance_to_buzz"] = {"median_dive_rho": float(rho.median()),
                                         **whale_wilcoxon(-whale_rho)}   # negative = longer far from buzzes
    out["M_step_vs_distance_to_buzz"]["note"] = "n_negative counts whales with positive rho (steps longer far from buzzes)"
    out["M_all_steps_mixed"] = mixed("np.log(step_s) ~ np.log(to_buzz_s + 1)", steps, "np.log(to_buzz_s + 1)")
    out["M_all_steps_mixed"]["caveat"] = "biased: a step without a buzz inside sits >= half its length from the nearest buzz"

    # M2: per-block turn probability vs time to nearest buzz (free of that bias)
    blocks = pd.concat(block_rows)
    edges = [0, 10, 30, 60, 120, 240, np.inf]
    (blocks.assign(bin=pd.cut(blocks.to_buzz_s, edges, right=False).astype(str))
     .groupby(["individual_id", "bin"]).turn.agg(["mean", "size"]).reset_index()
     .to_csv(OUT / "trajectory_turn_probability_by_whale.csv", index=False))
    out["M2_block_turn_probability"] = {
        "blocks": int(len(blocks)),
        **{k: v for k, v in gee_logit_turn(blocks).items()},
        "by_bin": blocks.groupby(pd.cut(blocks.to_buzz_s, [0, 10, 30, 60, 120, 240, np.inf], right=False),
                                 observed=True).turn.mean().round(4).rename(str).to_dict()}

    # M3: permutation null for the step-level correlation (circular shift of buzz times)
    def pooled_rho(shift_fn):
        xs, ys = [], []
        for runs, t0_, bs_, st, en, t_end in null_inputs:
            if len(st) == 0:
                continue
            st2, en2 = shift_fn(st, en, t0_, t_end)
            for start, length in runs:
                mid = t0_ + (start + length / 2) * bs_
                xs.append(length * bs_)
                ys.append(min(np.min(np.abs(st2 - mid)), np.min(np.abs(mid - en2))))
        return spearmanr(xs, ys).statistic

    rng = np.random.default_rng(7)

    def shift(st, en, t0_, t_end):
        span = t_end - t0_
        k = rng.uniform(0, span)
        return t0_ + (st - t0_ + k) % span, t0_ + (en - t0_ + k) % span

    observed = pooled_rho(lambda st, en, a_, b_: (st, en))
    null = np.array([pooled_rho(shift) for _ in range(200)])
    out["M3_step_rho_permutation"] = {"observed_rho": float(observed), "null_median": float(np.median(null)),
                                      "null_95th": float(np.percentile(null, 95)),
                                      "p": float((1 + (null >= observed).sum()) / 201)}

    # L: Lévy foraging hypothesis
    lt = prim.dropna(subset=["mu", "buzz_rate_per_min", "depth_100m"])
    out["L_mu_vs_buzz_rate"] = mixed("mu ~ buzz_rate_per_min + depth_100m", lt, "buzz_rate_per_min")
    full = dive_tab.dropna(subset=["depth_100m"])
    for y in ("alpha_msd", "alpha_horizontal", "turns_per_min", "persistence_60s"):
        out[f"L_{y}_vs_buzz_rate"] = mixed(f"{y} ~ buzz_rate_per_min + depth_100m",
                                           full.dropna(subset=[y]), "buzz_rate_per_min")

    # A: area-restricted search
    ars = pd.DataFrame(ars_rows)
    ars["diff"] = ars.post - ars.pre
    w = ars.groupby("individual_id")["diff"].median()
    out["A_post_minus_pre_turn_rate"] = {"buzzes": int(len(ars)), "median_pre_deg_s": float(ars.pre.median()),
                                         "median_post_deg_s": float(ars.post.median()),
                                         **whale_wilcoxon(-w)}
    out["A_post_minus_pre_turn_rate"]["note"] = "n_negative counts whales turning more after than before"
    by = ars[ars.type.isin(["A", "B"])].pivot_table(index="individual_id", columns="type", values="diff", aggfunc="median").dropna()
    out["A_type_contrast"] = {"median_diff_A": float(by.A.median()), "median_diff_B": float(by.B.median()),
                              **whale_wilcoxon(by.B - by.A)}
    sec = pd.concat(sec_rows)
    sec["bin"] = pd.cut(sec.since_s, POST_BINS, right=False, labels=False)
    curve = sec.groupby(["individual_id", "bin"]).rate.mean().unstack()
    slopes = curve.apply(lambda r: spearmanr(np.arange(len(r))[r.notna()], r.dropna()).statistic, axis=1)
    out["A_decay_with_time_since_buzz"] = {"bins_s": [str(x) for x in POST_BINS],
                                           "population_curve_deg_s": curve.median().round(3).tolist(),
                                           **whale_wilcoxon(slopes)}
    out["A_decay_with_time_since_buzz"]["note"] = "n_negative counts whales whose turning declines with time since the last buzz"

    # V: marginal value theorem with buzz bouts
    ibi = []
    for _, g2 in ev.sort_values(["trajectory_id", "buzz_start_s"]).groupby("trajectory_id"):
        gaps = g2.buzz_start_s.to_numpy()[1:] - g2.buzz_end_s.to_numpy()[:-1]
        ibi.extend(gaps[gaps > 0])
    from sklearn.mixture import GaussianMixture
    logi = np.log10(np.array(ibi)).reshape(-1, 1)
    gm = GaussianMixture(2, random_state=0, n_init=5).fit(logi)
    grid_x = np.linspace(logi.min(), logi.max(), 4000).reshape(-1, 1)
    post = gm.predict_proba(grid_x)[:, np.argmin(gm.means_.ravel())]
    threshold_s = float(10 ** grid_x[np.argmin(np.abs(post - 0.5)), 0])
    bouts = []
    for tid, g2 in ev.sort_values(["trajectory_id", "buzz_start_s"]).groupby("trajectory_id"):
        s_, e_ = g2.buzz_start_s.to_numpy(), g2.buzz_end_s.to_numpy()
        split = np.where(s_[1:] - e_[:-1] > threshold_s)[0] + 1
        groups = np.split(np.arange(len(s_)), split)
        dur = dives.dive_duration_s.get(tid, np.nan)
        for j, grp in enumerate(groups):
            bouts.append({"trajectory_id": tid, "individual_id": g2.individual_id.iloc[0],
                          "n_buzz": len(grp), "residence_s": e_[grp[-1]] - s_[grp[0]],
                          "travel_s": s_[grp[0]] - e_[groups[j - 1][-1]] if j else np.nan,
                          "first": j == 0, "last": j == len(groups) - 1,
                          "rel_time": s_[grp[0]] / dur if np.isfinite(dur) else np.nan})
    bouts = pd.DataFrame(bouts)
    core = bouts[(~bouts["first"]) & (~bouts["last"]) & (bouts.n_buzz >= 2)].dropna(subset=["rel_time"])
    out["V_bouts"] = {"bout_threshold_s": threshold_s, "bouts": int(len(bouts)),
                      "interior_multi_buzz_bouts": int(len(core)),
                      "median_buzzes_per_bout": float(bouts.n_buzz.median())}
    out["V_residence_vs_travel"] = mixed("np.log(residence_s) ~ np.log(travel_s) + rel_time", core, "np.log(travel_s)")
    gee = smf.gee("n_buzz ~ np.log(travel_s) + rel_time", groups="individual_id", data=core,
                  family=sm.families.Poisson(), cov_struct=sm.cov_struct.Exchangeable()).fit()
    ci = gee.conf_int().loc["np.log(travel_s)"]
    out["V_buzzes_vs_travel"] = {"rate_ratio_per_log_s": float(np.exp(gee.params["np.log(travel_s)"])),
                                 "ci_low": float(np.exp(ci[0])), "ci_high": float(np.exp(ci[1])),
                                 "p": float(gee.pvalues["np.log(travel_s)"]), "n": int(len(core))}
    withlast = bouts[(~bouts["first"]) & (bouts.n_buzz >= 2)].dropna(subset=["rel_time"])
    out["V_residence_vs_travel_incl_last_bout"] = mixed(
        "np.log(residence_s) ~ np.log(travel_s) + rel_time", withlast, "np.log(travel_s)")

    # R: are turns near buzzes roll / compass artefacts?
    net = pd.DataFrame(net_rows).dropna()
    wn = net.pivot_table(index="individual_id", columns="kind", values="net_deg", aggfunc="median").dropna()
    share = net.assign(big=net.net_deg > 30).pivot_table(index="individual_id", columns="kind", values="big", aggfunc="mean").dropna()
    out["R1_net_heading_change_across_buzz"] = {
        "windows": net.kind.value_counts().to_dict(),
        "median_net_deg_buzz": float(wn.buzz.median()), "median_net_deg_control": float(wn.control.median()),
        "share_over_30deg_buzz": float(share.buzz.median()), "share_over_30deg_control": float(share.control.median()),
        **whale_wilcoxon(wn.control - wn.buzz)}
    out["R1_net_heading_change_across_buzz"]["note"] = "heading 10-30 s before vs 10-30 s after; n_negative = whales with larger net change across buzzes"
    per = pd.DataFrame(persist_rows)
    per["zone"] = np.where(per.to_buzz_s <= 10, "near", np.where(per.to_buzz_s >= 60, "far", "mid"))
    per["persists"] = (per.net_deg > 30).astype(int)
    pz = per[per.zone != "mid"].pivot_table(index="individual_id", columns="zone", values="persists", aggfunc="mean").dropna()
    out["R2_turn_persistence"] = {
        "turns": per.zone.value_counts().to_dict(),
        "share_persisting_near": float(per.loc[per.zone == "near", "persists"].mean()),
        "share_persisting_far": float(per.loc[per.zone == "far", "persists"].mean()),
        "median_net_deg_near": float(per.loc[per.zone == "near", "net_deg"].median()),
        "median_net_deg_far": float(per.loc[per.zone == "far", "net_deg"].median()),
        **whale_wilcoxon(pz.near - pz.far)}
    out["R2_turn_persistence"]["note"] = "persists = heading 10 s after differs by >30 deg from 10 s before; n_negative = whales whose near-buzz turns persist less"
    roll = pd.read_csv(ROOT / "data/dswp/roll_speed_bins.csv").groupby("event_id").roll_speed_deg_s.mean()
    bl = blocks.assign(roll=blocks.nearest_event.map(roll), whale=blocks.individual_id)
    med = bl.drop_duplicates("nearest_event").groupby("whale").roll.median()
    q25 = bl.drop_duplicates("nearest_event").groupby("whale").roll.quantile(0.25)
    bl["roll_class"] = np.where(bl.roll <= bl.whale.map(q25), "lowest_quarter",
                                np.where(bl.roll <= bl.whale.map(med), "low", "high"))
    bl["zone"] = np.where(bl.to_buzz_s <= 10, "near", np.where((bl.to_buzz_s >= 60) & (bl.to_buzz_s < 240), "far", "mid"))
    rr = {"far_baseline": float(bl.loc[bl.zone == "far", "turn"].mean())}
    for cls in ("lowest_quarter", "low", "high"):
        rr[f"near_{cls}_roll"] = float(bl.loc[(bl.zone == "near") & (bl.roll_class == cls), "turn"].mean())
    sub = bl[bl.zone.isin(["near", "far"])].dropna(subset=["roll"]).copy()
    sub["near_low"] = ((sub.zone == "near") & (sub.roll_class != "high")).astype(int)
    sub["near_high"] = ((sub.zone == "near") & (sub.roll_class == "high")).astype(int)
    fit = smf.gee("turn ~ near_low + near_high", groups="individual_id", data=sub,
                  family=sm.families.Binomial(), cov_struct=sm.cov_struct.Independence()).fit()
    ci = np.exp(fit.conf_int())
    rr.update({f"OR_{t}_vs_far": {"or": float(np.exp(fit.params[t])), "ci_low": float(ci.loc[t, 0]),
                                  "ci_high": float(ci.loc[t, 1]), "p": float(fit.pvalues[t])}
               for t in ("near_low", "near_high")})
    wl = bl[bl.zone.isin(["near", "far"])].assign(k=lambda x: np.where(x.zone == "far", "far", np.where(x.roll_class == "high", "near_high", "near_low")))
    wtab = wl.pivot_table(index="individual_id", columns="k", values="turn", aggfunc="mean").dropna()
    rr["whale_level_near_low_minus_far"] = whale_wilcoxon(wtab.far - wtab.near_low)
    rr["note"] = "roll = mean |roll rate| from 10 s before to 10 s after onset; low = at or below each whale's median"
    out["R3_turning_near_low_roll_buzzes"] = rr

    # X: which search phase does each tactic occur in?
    tagged = []
    for tid, g2 in ev.sort_values(["trajectory_id", "buzz_start_s"]).groupby("trajectory_id"):
        s_, e_ = g2.buzz_start_s.to_numpy(), g2.buzz_end_s.to_numpy()
        gap_before = np.r_[np.inf, s_[1:] - e_[:-1]]
        dur = dives.dive_duration_s.get(tid, np.nan)
        tagged.append(g2.assign(first_in_bout=(gap_before > threshold_s).astype(int),
                                rel_time=s_ / dur if np.isfinite(dur) else np.nan,
                                depth_100m=dives.max_depth_m.get(tid, np.nan) / 100))
    tagged = pd.concat(tagged)
    tx = tagged[tagged.buzz_type.isin(["A", "B"])].dropna(subset=["rel_time", "depth_100m"])
    tx = tx.assign(is_b=(tx.buzz_type == "B").astype(int))
    fit = smf.gee("is_b ~ first_in_bout + rel_time + I(rel_time**2) + depth_100m", groups="individual_id",
                  data=tx, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Independence()).fit()
    lo, hi = np.exp(fit.conf_int().loc["first_in_bout"])
    out["X_tactic_by_search_phase"] = {
        "b_share_first_in_bout": float(tx.loc[tx.first_in_bout == 1, "is_b"].mean()),
        "b_share_within_bout": float(tx.loc[tx.first_in_bout == 0, "is_b"].mean()),
        "n_first": int((tx.first_in_bout == 1).sum()), "n_within": int((tx.first_in_bout == 0).sum()),
        "odds_ratio_first_vs_within": float(np.exp(fit.params["first_in_bout"])),
        "ci_low": float(lo), "ci_high": float(hi), "p": float(fit.pvalues["first_in_bout"]),
        "note": "first_in_bout = preceded by a gap above the bout threshold (arrival after travel)"}
    bt_ = tx.merge(dives[["bottom_start_s", "bottom_end_s"]], left_on="trajectory_id", right_index=True, how="left")
    bt_ = bt_[(bt_.buzz_start_s >= bt_.bottom_start_s) & (bt_.buzz_start_s < bt_.bottom_end_s)].copy()
    bt_["rel_bottom"] = (bt_.buzz_start_s - bt_.bottom_start_s) / (bt_.bottom_end_s - bt_.bottom_start_s)
    fit_b = smf.gee("is_b ~ first_in_bout + rel_bottom + I(rel_bottom**2) + depth_100m", groups="individual_id",
                    data=bt_, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Independence()).fit()
    lo_b, hi_b = np.exp(fit_b.conf_int().loc["first_in_bout"])
    out["X_tactic_by_search_phase_bottom_only"] = {
        "b_share_first_in_bout": float(bt_.loc[bt_.first_in_bout == 1, "is_b"].mean()),
        "b_share_within_bout": float(bt_.loc[bt_.first_in_bout == 0, "is_b"].mean()),
        "n_first": int((bt_.first_in_bout == 1).sum()), "n_within": int((bt_.first_in_bout == 0).sum()),
        "odds_ratio_first_vs_within": float(np.exp(fit_b.params["first_in_bout"])),
        "ci_low": float(lo_b), "ci_high": float(hi_b), "p": float(fit_b.pvalues["first_in_bout"])}
    pre = ars[ars.type.isin(["A", "B"])].pivot_table(index="individual_id", columns="type", values="pre", aggfunc="median").dropna()
    out["X_pre_buzz_turning_by_type"] = {"median_pre_A_deg_s": float(pre.A.median()),
                                         "median_pre_B_deg_s": float(pre.B.median()),
                                         **whale_wilcoxon(pre.B - pre.A)}
    out["X_pre_buzz_turning_by_type"]["note"] = "n_negative counts whales turning less before Type B than before Type A"

    (OUT / "trajectory_tests.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out, indent=2, default=float))


if __name__ == "__main__":
    main()
