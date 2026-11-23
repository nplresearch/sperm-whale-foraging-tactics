"""Where did the -4.4 min per unit Type-B share go? Same dives, all vs bottom-only."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_review_r1_foraging_models import mixed  # noqa: E402

ev = pd.read_csv(ROOT / "results/dswp/buzz_events_labelled.csv")
dives = pd.read_csv(ROOT / "data/dswp/dive_kinematics.csv").dropna(
    subset=["dive_duration_s", "bottom_start_s", "bottom_end_s", "max_depth_m"])
ev = ev.merge(dives, on=["dive_id", "deployment_id"], how="inner")
ev["phase"] = np.select([ev.buzz_start_s < ev.bottom_start_s, ev.buzz_start_s < ev.bottom_end_s],
                        ["descent", "bottom"], "ascent")
ab = ev[ev.buzz_type.isin(["A", "B"])].assign(is_b=lambda x: (x.buzz_type == "B").astype(int))
whale = ev.groupby("dive_id").individual_id.first()

d = dives.set_index("dive_id").assign(individual_id=whale).dropna(subset=["individual_id"])
d["dive_min"] = d.dive_duration_s / 60
d["bottom_min"] = (d.bottom_end_s - d.bottom_start_s) / 60
d["depth_100m"] = d.max_depth_m / 100
d["n_buzz"] = ev.groupby("dive_id").size()
d["share_all"] = ab.groupby("dive_id").is_b.mean()
d["n_cls"] = ab.groupby("dive_id").size()
bot, tr = ab[ab.phase == "bottom"], ab[ab.phase != "bottom"]
d["share_bottom"] = bot.groupby("dive_id").is_b.mean()
d["n_bottom"] = bot.groupby("dive_id").size()
d["n_transit"] = tr.groupby("dive_id").size()
d["n_transit_b"] = tr.groupby("dive_id").is_b.sum()
d = d.fillna({"n_transit": 0, "n_transit_b": 0, "n_bottom": 0})
d["transit_frac"] = d.n_transit / d.n_cls
d = d.reset_index()

full = d[d.n_cls >= 5]
same = d[(d.n_cls >= 5) & (d.n_bottom >= 5)]

def row(label, r):
    print(f"{label:58s} n={r['n']:3d}  {r['coef']:+6.2f} min  [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}]  p={r['p']:.3f}")

print("== dive_min ~ share + log(n_buzz) + depth ==")
row("1 all-buzz share, original sample (>=5 classified)", mixed("dive_min ~ share_all + np.log(n_buzz) + depth_100m", full, "share_all"))
row("2 all-buzz share, same dives as bottom-only", mixed("dive_min ~ share_all + np.log(n_buzz) + depth_100m", same, "share_all"))
row("3 bottom-only share, same dives", mixed("dive_min ~ share_bottom + np.log(n_buzz) + depth_100m", same, "share_bottom"))
row("4 all-buzz share + transit fraction, same dives", mixed("dive_min ~ share_all + transit_frac + np.log(n_buzz) + depth_100m", same, "share_all"))
row("   ...transit fraction coefficient", mixed("dive_min ~ share_all + transit_frac + np.log(n_buzz) + depth_100m", same, "transit_frac"))
row("5 transit fraction alone, same dives", mixed("dive_min ~ transit_frac + np.log(n_buzz) + depth_100m", same, "transit_frac"))

print("\n== the mechanism ==")
print("B share: bottom %.2f | descent %.2f | ascent %.2f" % tuple(ab[ab.phase == p].is_b.mean() for p in ("bottom", "descent", "ascent")))
print("per dive (same dives), median: transit buzzes %.0f, bottom buzzes %.0f, transit fraction %.2f"
      % (same.n_transit.median(), same.n_bottom.median(), same.transit_frac.median()))
for x in ("n_transit", "n_bottom", "transit_frac", "share_all", "share_bottom"):
    rho, p = spearmanr(same[x], same.dive_min)
    print(f"Spearman {x:13s} vs dive_min: rho={rho:+.2f} p={p:.3g}")
q = pd.qcut(same.dive_min, 3, labels=["short", "mid", "long"])
print(same.groupby(q, observed=True)[["dive_min", "n_transit", "n_bottom", "transit_frac", "share_all", "share_bottom"]].median().round(2))

print("\n== split the all-buzz share into its bottom and transit parts (they sum to it) ==")
s = same.copy()
s["n_bottom_b"] = bot.groupby("dive_id").is_b.sum().reindex(s.dive_id).fillna(0).values
s["bottom_b_frac"] = s.n_bottom_b / s.n_cls
s["transit_b_frac"] = s.n_transit_b / s.n_cls
f = "dive_min ~ bottom_b_frac + transit_b_frac + np.log(n_buzz) + depth_100m"
row("6a bottom-B part", mixed(f, s, "bottom_b_frac"))
row("6b transit-B part", mixed(f, s, "transit_b_frac"))

print("\n== what the log(n_buzz) covariate does ==")
row("7 all-buzz share, no n_buzz control", mixed("dive_min ~ share_all + depth_100m", s, "share_all"))
row("8 bottom-only share, no n_buzz control", mixed("dive_min ~ share_bottom + depth_100m", s, "share_bottom"))
s["bottom_rate"] = s.n_bottom / s.bottom_min
s["all_rate"] = s.n_buzz / s.dive_min
for x, y in (("share_all", "all_rate"), ("share_bottom", "bottom_rate")):
    rho, p = spearmanr(s[x], s[y])
    print(f"Spearman {x} vs {y}: rho={rho:+.2f} p={p:.3g}")
rho, p = spearmanr(s.n_buzz, s.dive_min); print(f"Spearman n_buzz vs dive_min: rho={rho:+.2f} p={p:.3g}")

# --- Does the -4.4 hold if transit Type B is defined acoustically? -------------
# Acoustics-only logistic model (as in transit_tests / energy_tests): trained on
# bottom-phase labelled buzzes; bottom buzzes get grouped cross-validated
# predictions, transit buzzes get the model fitted on all bottom buzzes.
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import GroupKFold, cross_val_predict  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

feats = ["log_ramp_up_duration_s", "log_buzz_duration_s", "median_click_rate_hz", "max_click_rate_hz"]
ac = ab.copy()
for c in ("ramp_up_duration_s", "buzz_duration_s"):
    ac[f"log_{c}"] = np.log(ac[c].clip(lower=0.05))
ok = ac[feats].notna().all(axis=1)
tr_bot = ac[ok & (ac.phase == "bottom")]
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
ac["acoustic_b"] = ac.is_b.astype(float)  # fallback: keep the label (1 buzz lacks features)
ac.loc[tr_bot.index, "acoustic_b"] = (cross_val_predict(
    model, tr_bot[feats], tr_bot.is_b, groups=tr_bot.individual_id,
    cv=GroupKFold(n_splits=5), method="predict_proba")[:, 1] > 0.5).astype(float)
model.fit(tr_bot[feats], tr_bot.is_b)
tmask = ok & (ac.phase != "bottom")
ac.loc[tmask, "acoustic_b"] = (model.predict_proba(ac.loc[tmask, feats])[:, 1] > 0.5).astype(float)
ac["transit"] = ac.phase != "bottom"
t_ = ac[ac.transit]
print("\n== acoustic check of transit buzzes ==")
print("labelled B in transit: %d, acoustically B: %d (%.0f%%); labelled A in transit: %d, acoustically B: %d"
      % (t_.is_b.sum(), (t_.is_b & (t_.acoustic_b == 1)).sum(), 100 * (t_.acoustic_b[t_.is_b == 1]).mean(),
         (t_.is_b == 0).sum(), ((t_.is_b == 0) & (t_.acoustic_b == 1)).sum()))

variants = {
    "V0 original labels": ac.is_b,
    "V1 transit B only if labelled B AND acoustically B (else counted A)":
        np.where(ac.transit, ac.is_b * ac.acoustic_b, ac.is_b),
    "V2 transit type fully acoustic":
        np.where(ac.transit, ac.acoustic_b, ac.is_b),
    "V3 acoustic type everywhere":
        ac.acoustic_b,
}
print("\n== dive_min ~ B share (all buzzes) + log(n_buzz) + depth, same 192 dives ==")
for name, lab in variants.items():
    ac["b_v"] = lab
    s2 = same.copy()
    g = ac.groupby("dive_id")
    s2["share_v"] = g.b_v.mean().reindex(s2.dive_id).values
    s2["bot_part"] = ac[~ac.transit].groupby("dive_id").b_v.sum().reindex(s2.dive_id).fillna(0).values / s2.n_cls
    s2["tr_part"] = ac[ac.transit].groupby("dive_id").b_v.sum().reindex(s2.dive_id).fillna(0).values / s2.n_cls
    s2["n_tr_b"] = ac[ac.transit].groupby("dive_id").b_v.sum().reindex(s2.dive_id).fillna(0).values
    s2["n_tr_a"] = s2.n_transit - s2.n_tr_b
    row(name, mixed("dive_min ~ share_v + np.log(n_buzz) + depth_100m", s2, "share_v"))
    f2 = "dive_min ~ bot_part + tr_part + np.log(n_buzz) + depth_100m"
    row("    split: bottom-B part", mixed(f2, s2, "bot_part"))
    row("    split: transit-B part", mixed(f2, s2, "tr_part"))
    f3 = "dive_min ~ n_tr_b + n_tr_a + n_bottom + depth_100m"
    row("    counts: each transit B (min per buzz)", mixed(f3, s2, "n_tr_b"))
    row("    counts: each transit A (min per buzz)", mixed(f3, s2, "n_tr_a"))

# --- First and last buzz of the dive, by phase (Markov Start/End claims) -----------
o = ab.sort_values(["dive_id", "buzz_start_s"])
first, last = o.groupby("dive_id").head(1), o.groupby("dive_id").tail(1)
ob = o[o.phase == "bottom"]
print("\n== first / last classified buzz of each dive ==")
print("first: Type B %.2f, in descent %.2f; first bottom-phase buzz Type B %.2f"
      % (first.is_b.mean(), (first.phase == "descent").mean(), ob.groupby("dive_id").head(1).is_b.mean()))
print("last:  Type B %.2f, in ascent %.2f; last bottom-phase buzz Type B %.2f; bottom-phase mean %.2f"
      % (last.is_b.mean(), (last.phase == "ascent").mean(), ob.groupby("dive_id").tail(1).is_b.mean(), ob.is_b.mean()))
