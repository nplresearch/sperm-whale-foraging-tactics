#!/usr/bin/env python3
"""Reviewer 1: are the Azores prey-depth and persistence results descent/ascent effects?

In DSWP, buzzes made while descending or ascending are mostly labelled Type B
because Type B is largely defined by vertical speed.  The Azores split ranks
pressure-derived vertical speed directly, and a buzz made on the way up is
shallower by construction, so its prey are shallower too.  This script labels
each of the 58 daytime Azores buzzes as descent, bottom or ascent from the dive
depth profile and reruns the prey-depth and persistence contrasts.

Needs the four checksummed Dryad files (see data/azores/README.md).  Prints
aggregates only; writes nothing.

    python scripts/run_review_r1_azores_phase.py [source_directory]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validation.azores import (  # noqa: E402
    _cohens_d,
    load_azores_sources,
    run_azores_validation,
)

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "repo/Clean_notebooks_figures/Azores_code"


def scalar(v):
    return float(np.ravel(v)[0])


def phase_bounds(dive, frac):
    """First and last time (s, dive clock) the whale is deeper than frac * max depth."""
    depth = np.asarray(dive["depth_data"], float).ravel()
    fs = scalar(dive["depth_fs"])
    deep = np.flatnonzero(depth >= frac * np.nanmax(depth))
    return scalar(dive["dive_start"]) + deep[0] / fs, scalar(dive["dive_start"]) + deep[-1] / fs


def whale_depth(dive, t):
    depth = np.asarray(dive["depth_data"], float).ravel()
    k = int(np.clip(round((t - scalar(dive["dive_start"])) * scalar(dive["depth_fs"])), 0, len(depth) - 1))
    return float(depth[k])


def resid(y, x):
    """Residual of y after a straight-line fit on x."""
    return y - np.poly1d(np.polyfit(x, y, 1))(x)


def contrast(ev, metric, label="operative_type"):
    a = ev.loc[ev[label] == "A", metric].dropna()
    b = ev.loc[ev[label] == "B", metric].dropna()
    if len(a) < 3 or len(b) < 3:
        return f"{metric}: n_A={len(a)} n_B={len(b)} (too few)"
    p = mannwhitneyu(a, b, alternative="two-sided").pvalue
    return (f"{metric}: n_A={len(a)} n_B={len(b)}  median A {a.median():.0f} vs B {b.median():.0f}"
            f"  p={p:.3f}  d={_cohens_d(a, b):.2f}")


src = load_azores_sources(SRC)
dives = src["diving"]
ev = run_azores_validation(SRC)["events"]
mid = (ev._buzz_start_s + ev._buzz_end_s) / 2
ev["whale_depth_m"] = [whale_depth(dives.iloc[int(r.dive_no) - 1], t) for r, t in zip(ev.itertuples(), mid)]
ev["prey_rel_m"] = ev.mean_prey_depth_m - ev.whale_depth_m   # >0: prey below the whale

for name, frac in {"70": 0.7, "80": 0.8, "dataset": None}.items():
    if frac is None:
        b = {i + 1: (scalar(d["descent_end"]), scalar(d["ascent_start"])) for i, d in dives.iterrows()}
    else:
        b = {i + 1: phase_bounds(d, frac) for i, d in dives.iterrows()}
    s, e = ev.dive_no.map(lambda k: b[k][0]), ev.dive_no.map(lambda k: b[k][1])
    ev[f"phase_{name}"] = np.select([ev._buzz_start_s < s, ev._buzz_start_s < e], ["descent", "bottom"], "ascent")

print(f"Azores daytime buzzes: {len(ev)}; dives {ev.dive_no.nunique()}")
print("\n== Phase x type (operative 28/28 split) ==")
for name in ("70", "80", "dataset"):
    print(f"-- bottom = {name}{'% of max depth' if name != 'dataset' else ' (descent_end/ascent_start)'}")
    print(pd.crosstab(ev[f"phase_{name}"], ev.operative_type, margins=True).to_string())

print("\n== Whale depth at buzz (all 58) ==")
print(contrast(ev, "whale_depth_m"))
print("rank corr whale depth vs prey depth: rho=%.2f p=%.4f" % spearmanr(ev.whale_depth_m, ev.mean_prey_depth_m, nan_policy="omit"))

print("\n== Prey depth, published (all buzzes) ==")
print(contrast(ev, "mean_prey_depth_m"))
print(contrast(ev, "prey_rel_m"))
ok = ev.dropna(subset=["mean_prey_depth_m"])
ok = ok.assign(is_b=(ok.operative_type == "B").astype(int))[ok.operative_type.isin(["A", "B"])]
fit = smf.ols("mean_prey_depth_m ~ is_b + whale_depth_m", ok).fit()
print("OLS prey depth ~ type + whale depth: B-A = %.1f m (p=%.3f); whale depth slope %.2f (p=%.4f); n=%d"
      % (fit.params.is_b, fit.pvalues.is_b, fit.params.whale_depth_m, fit.pvalues.whale_depth_m, len(ok)))
diag = ok.ramp_rank + ok.speed_rank
r0 = spearmanr(diag, ok.mean_prey_depth_m)
r1 = spearmanr(resid(diag, ok.whale_depth_m), resid(ok.mean_prey_depth_m, ok.whale_depth_m))
print("threshold-free: rho(diag rank, prey depth)=%.2f p=%.4f; partial on whale depth: rho=%.2f p=%.3f"
      % (r0.statistic, r0.pvalue, r1.statistic, r1.pvalue))

for name in ("70", "80", "dataset"):
    bot = ev[ev[f"phase_{name}"] == "bottom"]
    print(f"\n== Bottom phase only ({name}): {len(bot)} buzzes, A {sum(bot.operative_type=='A')}, B {sum(bot.operative_type=='B')} ==")
    print("  labels kept  ", contrast(bot, "mean_prey_depth_m"))
    print("               ", contrast(bot, "prey_rel_m"))
    print("               ", contrast(bot, "whale_depth_m"))
    print("               ", contrast(bot, "prey_echo_count"))
    # re-rank within the bottom phase and assign each buzz to the closer corner (ties left out)
    rel = bot.copy()
    n = len(rel)
    ra = (rel.ramp_up_duration_s.rank() - 1) / (n - 1)
    sp = (rel.avg_vertical_speed_m_s.rank() - 1) / (n - 1)
    gap = np.hypot(ra, sp) - np.hypot(1 - ra, 1 - sp)
    rel["operative_type"] = np.select([np.isclose(gap, 0), gap < 0], ["unclassified", "A"], "B")
    print("  re-split     ", contrast(rel, "mean_prey_depth_m"))
    v = bot.dropna(subset=["mean_prey_depth_m"])
    r = spearmanr(v.ramp_rank + v.speed_rank, v.mean_prey_depth_m)
    print(f"  threshold-free diag rank vs prey depth: rho={r.statistic:.2f} p={r.pvalue:.3f} (n={len(v)})")
    g = bot[bot.operative_type.isin(["A", "B"]) & (bot.geometry_group != "unavailable")]
    tab = pd.crosstab(g.operative_type, g.geometry_group)
    print("  persistence: " + "; ".join(f"{t}: {int(tab.loc[t].get('persistent', 0))}/{int(tab.loc[t].sum())} persistent"
                                         for t in tab.index))

print("\n== Persistence by phase (70%) ==")
g = ev[ev.operative_type.isin(["A", "B"]) & (ev.geometry_group != "unavailable")]
print(pd.crosstab([g.phase_70, g.operative_type], g.geometry_group).to_string())
print("\n== Prey depth by phase (70%) ==")
print(ev.groupby(["phase_70", "operative_type"]).agg(n=("dive_no", "size"), n_prey=("mean_prey_depth_m", "count"),
      whale=("whale_depth_m", "median"), prey=("mean_prey_depth_m", "median"),
      vspeed=("avg_vertical_speed_m_s", "median")).round(1).to_string())

print("\n== Is 'Type B is shallower' built into the vertical-speed feature? (all 58) ==")
ev["max_depth_m"] = ev.dive_no.map(lambda k: float(np.nanmax(np.asarray(dives.iloc[k - 1]["depth_data"], float))))
ev["above_max_m"] = ev.max_depth_m - ev.whale_depth_m
for f in ("ramp_rank", "speed_rank"):
    r = spearmanr(ev[f], ev.whale_depth_m)
    q = spearmanr(ev[f], ev.above_max_m)
    print(f"{f:10s} vs whale depth rho={r.statistic:+.2f} p={r.pvalue:.4f} | vs height above dive max rho={q.statistic:+.2f} p={q.pvalue:.4f}")
r = spearmanr(resid(ev.ramp_rank, ev.speed_rank), ev.whale_depth_m)
print(f"ramp-up net of vertical speed vs whale depth: rho={r.statistic:+.2f} p={r.pvalue:.3f}")
print(contrast(ev, "above_max_m"))

print("\n== Buzzes within a dive are not independent: random intercept per dive ==")
ab = ev[ev.operative_type.isin(["A", "B"])].assign(is_b=lambda x: (x.operative_type == "B").astype(int))
for y in ("whale_depth_m", "above_max_m"):
    f = smf.mixedlm(f"{y} ~ is_b", ab, groups=ab.dive_no).fit()
    print(f"{y}: B - A = {f.params.is_b:+.0f} m, p={f.pvalues.is_b:.4f} (58 buzzes in 11 dives)")
ok2 = ab.dropna(subset=["mean_prey_depth_m"])
f = smf.mixedlm("mean_prey_depth_m ~ is_b + whale_depth_m", ok2, groups=ok2.dive_no).fit()
print(f"prey depth ~ type + whale depth: B - A = {f.params.is_b:+.1f} m, p={f.pvalues.is_b:.3f} (n={len(ok2)})")

# ---------------------------------------------------------------------------
# Why was Type A deeper?  Height above the seafloor (from the seafloor echoes,
# independent of the whale's depth) and the depth path into each buzz.
# ---------------------------------------------------------------------------
print("\n\n######## Why was Type A deeper? ########")


def depth_at(dive_no, t, key="depth_data"):
    dive = dives.iloc[dive_no - 1]
    x = np.asarray(dive[key], float).ravel()
    k = int(round((t - scalar(dive["dive_start"])) * scalar(dive["depth_fs"])))
    return float(x[k]) if 0 <= k < len(x) else np.nan


buzz_src = src["buzz"].assign(height_m=lambda x: x.bottom_dist * 750)   # two-way travel time -> m
ev = ev.merge(buzz_src[["dive_no", "start", "height_m"]].rename(columns={"start": "_buzz_start_s"}),
              on=["dive_no", "_buzz_start_s"], how="left")
keys = list(zip(ev.dive_no.astype(int), ev._click_first_s, ev._click_last_s))
ev["down_60s_m"] = [depth_at(k, a) - depth_at(k, a - 60) for k, a, _ in keys]       # + = went deeper
ev["after_60s_m"] = [depth_at(k, b + 60) - depth_at(k, b) for k, _, b in keys]
ev["pitch_10s_deg"] = [np.nanmean([depth_at(k, a - s, "pitch_data") for s in np.arange(0, 10, 0.5)]) for k, a, _ in keys]
ev["height_60s_before_m"] = ev.height_m + ev.down_60s_m
ev["since_bottom_s"] = ev._click_first_s - ev.dive_no.map(lambda k: phase_bounds(dives.iloc[k - 1], 0.7)[0])
ab = ev[ev.operative_type.isin(["A", "B"])].assign(is_b=lambda x: (x.operative_type == "B").astype(int))
print(f"seafloor distance available: A {ab[ab.is_b == 0].height_m.notna().sum()}/28, B {ab[ab.is_b == 1].height_m.notna().sum()}/28;"
      f" buzzes >= 2 min into the bottom phase: {int((ab.since_bottom_s >= 120).sum())}/56")
print(ab.groupby("operative_type")[["height_60s_before_m", "height_m", "down_60s_m", "pitch_10s_deg", "after_60s_m"]]
      .median().round(0).to_string())
for y in ("height_m", "height_60s_before_m", "down_60s_m", "pitch_10s_deg", "after_60s_m"):
    x = ab.dropna(subset=[y])
    f = smf.mixedlm(f"{y} ~ is_b", x, groups=x.dive_no).fit()
    print(f"  {y}: B - A = {f.params.is_b:+.1f}, p={f.pvalues.is_b:.4f} (random intercept per dive, n={len(x)})")
x = ab.dropna(subset=["height_m"]).assign(floor_m=lambda v: v.whale_depth_m + v.height_m)
f = smf.mixedlm("floor_m ~ is_b", x, groups=x.dive_no).fit()
print(f"  seafloor depth under the buzz: B - A = {f.params.is_b:+.1f} m, p={f.pvalues.is_b:.3f}")
print("  climbed > 10 m in the 60 s before: A %d/28, B %d/28" % ((ab[ab.is_b == 0].down_60s_m < -10).sum(), (ab[ab.is_b == 1].down_60s_m < -10).sum()))

# Where the whale searches, and where prey echoes are: 10-s windows of regular clicking in the bottom phase
rows = []
for i in range(11):
    dive, r = dives.iloc[i], src["echo"].iloc[i]
    t = scalar(dive["dive_start"]) + np.arange(len(np.ravel(dive["depth_data"]))) / scalar(dive["depth_fs"])
    z = np.asarray(dive["depth_data"], float).ravel()
    bt = np.concatenate([np.asarray(q)[:, 0] for q in r.bottom])
    floor = np.interp(bt, t, z) + np.concatenate([np.asarray(q)[:, 1] for q in r.bottom]) * 750
    clicks, prey_t = np.asarray(r.CLclean, float).ravel(), np.asarray(r.prey_midtime, float).ravel()
    b0, b1 = phase_bounds(dive, 0.7)
    for w0 in np.arange(b0, b1, 10.0):
        near = np.abs(bt - (w0 + 5)) < 30
        if np.count_nonzero((clicks >= w0) & (clicks < w0 + 10)) < 5 or not near.any():
            continue
        rows.append({"dive": i + 1, "h": np.median(floor[near]) - np.interp(w0 + 5, t, z),
                     "prey": np.count_nonzero((prey_t >= w0) & (prey_t < w0 + 10))})
pf = pd.DataFrame(rows)
print(f"\nsearch height above seafloor (bottom phase): median {pf.h.median():.0f} m, IQR {pf.h.quantile(.25):.0f}-{pf.h.quantile(.75):.0f} ({len(pf)} windows)")
print("prey echo streams per 10 s of search, by height above seafloor:")
print(pf.groupby(pd.cut(pf.h, [0, 50, 75, 100, 150, 250, 1000]), observed=True)
      .agg(windows=("prey", "size"), prey_per_10s=("prey", "mean")).round(2).to_string())
for t in "AB":
    h = ab[ab.operative_type == t].height_m.dropna()
    print(f"Type {t}: {np.mean(h < pf.h.quantile(.25)):.0%} of buzzes below the lowest quarter of search heights")

# DSWP comparison: approach direction in the bottom phase (no seafloor data there)
dsw = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv").merge(
    pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv"), on=["dive_id", "deployment_id"])
dsw = dsw[dsw.buzz_type.isin(["A", "B"]) & (dsw.buzz_start_s >= dsw.bottom_start_s + 120)
          & (dsw.buzz_start_s < dsw.bottom_end_s)]
print(f"\nDSWP, bottom phase >= 2 min in ({len(dsw)} buzzes, {dsw.individual_id.nunique()} whales): share approached going down")
print((dsw.groupby("buzz_type").vertical_direction_before.apply(lambda v: (v > 0).mean())).round(2).to_string())

# ---------------------------------------------------------------------------
# Is the drop before Type A a by-product of the split?  The split ranks the
# mean |vertical speed| during the buzz, so slow moments on an up-and-down track
# could simply be the bottoms of dips.  Apply the same speed split to random
# search moments, separate the acoustic (ramp-up) and pressure (speed) halves of
# the split, and check that seafloor ranges are vertical heights.
# ---------------------------------------------------------------------------
print("\n\n######## Is the drop before Type A built into the split? ########")


def track(k):
    d = dives.iloc[k - 1]
    return (np.asarray(d["depth_data"], float).ravel(), np.asarray(d["pitch_data"], float).ravel(),
            scalar(d["depth_fs"]), scalar(d["dive_start"]))


def net_rate(z, fs, t0, a, b):
    """Net depth rate over [a, b] (m/s; + = going deeper)."""
    i, j = int((a - t0) * fs), int((b - t0) * fs)
    j = max(j, i + 2)
    return (z[min(j, len(z) - 1)] - z[i]) / ((j - i) / fs)


def abs_rate(z, fs, t0, a, b):
    """Smoothed mean |depth rate| over [a, b], as in the classifier."""
    i, j = int((a - t0) * fs), int((b - t0) * fs)
    s = np.abs(np.diff(z[i:max(j, i + 2) + 1]) * fs)
    return np.nanmean(np.convolve(s, np.ones(3) / 3, mode="same"))


ab["rate_during"] = [net_rate(z, fs, t0, a, b) for (z, _, fs, t0), a, b in
                     zip(map(track, ab.dive_no.astype(int)), ab._click_first_s, ab._click_last_s)]
print("direction during the buzz (net depth rate; |rate| > 0.1 m/s counts as moving):")
for t in "AB":
    x = ab[ab.operative_type == t].rate_during
    print(f"  {t}: going up {np.mean(x < -0.1):.0%}, level {np.mean(x.abs() <= 0.1):.0%}, going down {np.mean(x > 0.1):.0%}")

print("acoustic (ramp-up) and pressure (speed) halves of the split, in one model with a random intercept per dive:")
for y in ("down_60s_m", "height_m", "pitch_10s_deg"):
    x = ab.dropna(subset=[y])
    f = smf.mixedlm(f"{y} ~ ramp_rank + speed_rank", x, groups=x.dive_no).fit()
    print(f"  {y}: ramp_rank {f.params.ramp_rank:+.1f} (p={f.pvalues.ramp_rank:.3f}), "
          f"speed_rank {f.params.speed_rank:+.1f} (p={f.pvalues.speed_rank:.3f}), n={len(x)}")

rng = np.random.default_rng(1)
durs = (ab._click_last_s - ab._click_first_s).to_numpy()
rows = []
for k in sorted(ab.dive_no.unique().astype(int)):
    z, p, fs, t0 = track(k)
    b0, b1 = phase_bounds(dives.iloc[k - 1], 0.7)
    bz = ev.loc[ev.dive_no == k, ["_click_first_s", "_click_last_s"]].to_numpy()
    for a in rng.uniform(b0 + 120, b1 - 10, 400):
        if np.any((a > bz[:, 0] - 60) & (a < bz[:, 1] + 60)):
            continue
        b = a + rng.choice(durs)
        rows.append({"dive_no": k, "absv": abs_rate(z, fs, t0, a, b),
                     "down_60s_m": depth_at(k, a) - depth_at(k, a - 60)})
nl = pd.DataFrame(rows).dropna()
nl["slow"] = nl.groupby("dive_no").absv.transform(lambda v: v <= v.median()).astype(int)
f = smf.mixedlm("down_60s_m ~ slow", nl, groups=nl.dive_no).fit()
real = ab[ab.is_b == 0].down_60s_m.median() - ab[ab.is_b == 1].down_60s_m.median()
print(f"random search moments (no buzz within 60 s; n={len(nl)}), split at each dive's median |vertical speed|:")
print(f"  slow minus fast half, depth gained in the previous 60 s: {f.params.slow:+.1f} m (p={f.pvalues.slow:.1g})")
print(f"  real buzzes, Type A minus Type B (medians): {real:+.1f} m")

x = ab.dropna(subset=["height_m"]).assign(floor_m=lambda v: v.whale_depth_m + v.height_m)
f = smf.mixedlm("floor_m ~ pitch_10s_deg", x, groups=x.dive_no).fit()
print(f"seafloor range is vertical height: floor estimate vs pitch {f.params.pitch_10s_deg:+.2f} m/deg "
      f"(p={f.pvalues.pitch_10s_deg:.2f}); within-dive SD {x.groupby('dive_no').floor_m.std().median():.0f} m; "
      f"no seafloor echo: {ab[ab.height_m.isna()].operative_type.value_counts().to_dict()}")

# Was the target heard before the drop began?  Target stream = the prey echo stream
# ending closest to buzz onset (10 s before to 3 s after), at under 20 m.
rows = []
for k, a, t in zip(ab.dive_no.astype(int), ab._click_first_s, ab.operative_type):
    z, _, fs, t0 = track(k)
    tt = np.arange(a - 120, a, 0.5)
    t_top = tt[np.argmin(np.interp(tt, t0 + np.arange(len(z)) / fs, z))]   # top of the last descent
    streams = [np.asarray(s, float).reshape(-1, 3) for s in src["echo"].loc[src["echo"].dive_no == k].iloc[0].prey]
    cand = [s for s in streams if a - 10 <= s[-1, 0] <= a + 3 and s[-1, 1] * 750 < 20]
    if cand:
        s = min(cand, key=lambda s: abs(s[-1, 0] - a))
        rows.append({"type": t, "lead_s": a - s[0, 0], "range0_m": s[0, 1] * 750,
                     "drop_began_s": a - t_top, "heard_before_drop": s[0, 0] <= t_top + 2})
tg = pd.DataFrame(rows)
print(f"target echo stream found for {len(tg)} of {len(ab)} buzzes "
      f"(A {sum(tg.type == 'A')}, B {sum(tg.type == 'B')}); first heard median {tg.lead_s.median():.0f} s "
      f"and {tg.range0_m.median():.0f} m before the buzz")
ta = tg[tg.type == "A"]
print(f"  Type A: drop began median {ta.drop_began_s.median():.0f} s before the buzz; "
      f"target heard before the drop began in {int(ta.heard_before_drop.sum())} of {len(ta)}")
