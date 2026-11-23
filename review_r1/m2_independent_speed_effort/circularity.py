"""Is "Type B swims faster at matched body angle" independent of the A/B labels?

It is not. The registered classifier splits buzzes on ramp-up and *vertical speed*
(``avg_speed_3d_m_s`` has rho = 0.94 with measured vertical speed). OCDR speed is
``|vertical speed| / sin(pitch)``. Matching on pitch therefore leaves a contrast
that is implied by the labels. The honest control is to match on measured vertical
speed itself: if B/A -> 1 there, the speed contrast restates the label.

Usage:  python circularity.py            # writes results/review_r1/m2_circularity_*.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PKG = Path(__file__).resolve().parents[2]
RESULTS = PKG / "results" / "review_r1"


def prepare(labels: pd.DataFrame, kin: pd.DataFrame, thr: int = 30, min_cov: float = 0.5) -> pd.DataFrame:
    """Labelled A/B buzzes with valid OCDR speed (same selection as run_review_r1_speed.py)."""
    d = labels[["event_id", "buzz_type", "individual_id"]].merge(kin, on="event_id")
    d = d[d.buzz_type.isin(["A", "B"]) & (d[f"buzz_ocdr{thr}_coverage"] >= min_cov)]
    d = d.dropna(subset=[f"buzz_ocdr{thr}_speed_m_s", "buzz_vertical_speed_m_s"]).copy()
    d["speed"] = d[f"buzz_ocdr{thr}_speed_m_s"]
    d["abs_vz"] = d.buzz_vertical_speed_m_s.abs()
    return d


def binned_contrast(d: pd.DataFrame, n_bins: int = 4) -> pd.DataFrame:
    """Median OCDR speed of A and B inside quantile bins of |vertical speed|."""
    d = d.assign(vz_bin=pd.qcut(d.abs_vz, n_bins, labels=False, duplicates="drop"))
    rows = []
    for b, g in d.groupby("vz_bin"):
        a, bb = g[g.buzz_type == "A"].speed, g[g.buzz_type == "B"].speed
        rows.append({
            "vz_bin": int(b), "abs_vz_low": g.abs_vz.min(), "abs_vz_high": g.abs_vz.max(),
            "n_A": len(a), "n_B": len(bb), "median_A": a.median(), "median_B": bb.median(),
            "ratio_B_A": bb.median() / a.median() if len(a) and len(bb) else np.nan,
        })
    return pd.DataFrame(rows)


def adjusted_ratio(d: pd.DataFrame) -> dict:
    """B/A speed ratio with and without controlling for log |vertical speed|."""
    out = {}
    for name, formula in {
        "pitch_only": "np.log(speed) ~ C(buzz_type) + buzz_abs_pitch_deg",
        "pitch_and_vertical_speed": "np.log(speed) ~ C(buzz_type) + buzz_abs_pitch_deg + np.log(abs_vz)",
    }.items():
        fit = smf.ols(formula, d).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(d.individual_id)[0]})
        lo, hi = fit.conf_int().loc["C(buzz_type)[T.B]"]
        out[name] = {"B_over_A": float(np.exp(fit.params["C(buzz_type)[T.B]"])),
                     "ci_low": float(np.exp(lo)), "ci_high": float(np.exp(hi)),
                     "p": float(fit.pvalues["C(buzz_type)[T.B]"])}
    return out


def run(thr: int = 30) -> None:
    labels = pd.read_csv(PKG / "results/dswp/buzz_events_labelled.csv")
    kin = pd.read_csv(PKG / "data/dswp/buzz_kinematics.csv")
    d = prepare(labels, kin, thr)
    binned = binned_contrast(d)
    adj = pd.DataFrame(adjusted_ratio(d)).T.rename_axis("model").reset_index()
    binned.insert(0, "threshold_deg", thr)
    adj.insert(0, "threshold_deg", thr)
    binned.to_csv(RESULTS / f"m2_circularity_binned_{thr}.csv", index=False)
    adj.to_csv(RESULTS / f"m2_circularity_adjusted_{thr}.csv", index=False)
    print(binned.round(2).to_string(index=False))
    print(adj.round(3).to_string(index=False))


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
