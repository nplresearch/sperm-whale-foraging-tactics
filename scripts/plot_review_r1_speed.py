#!/usr/bin/env python3
"""Figure for the reviewer-1 response: measured speed and effort, A vs B."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "review_r1"
COLORS = {"A": "#2a78d6", "B": "#eb6834"}  # paper convention; validated pair
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)


def profile(ax, prof, variable, ylabel, title):
    d = prof[prof.variable == variable].copy()
    d["t"] = d.bin_start_s + 1.0  # bin centre
    ends = {}
    for t, c in COLORS.items():
        g = d[d.buzz_type == t].sort_values("t")
        ax.fill_between(g.t, g["mean"] - g["sem"], g["mean"] + g["sem"], color=c, alpha=0.18, lw=0)
        ax.plot(g.t, g["mean"], color=c, lw=2, label=f"Type {t}")
        ends[t] = (g.t.iloc[-1], g["mean"].iloc[-1])
    # direct labels, pushed apart vertically when the line ends are close
    span = ax.get_ylim()[1] - ax.get_ylim()[0]
    (xa, ya), (xb, yb) = ends["A"], ends["B"]
    gap = 0.07 * span
    if abs(ya - yb) < gap:
        mid = (ya + yb) / 2
        ya, yb = (mid + gap / 2, mid - gap / 2) if ya >= yb else (mid - gap / 2, mid + gap / 2)
    for t, (x, y) in {"A": (xa, ya), "B": (xb, yb)}.items():
        ax.annotate(f"Type {t}", (x, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9, color=INK)
    ax.axvline(0, color=INK2, lw=1, ls="--")
    ax.set_xlabel("Time from buzz onset (s)", color=INK, fontsize=9)
    ax.set_ylabel(ylabel, color=INK, fontsize=9)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_xlim(-20, 23.5)
    style(ax)


def main():
    prof = pd.read_csv(RES / "speed_profiles.csv")
    models = pd.read_csv(RES / "speed_matched_models.csv")
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9), facecolor=SURFACE,
                             gridspec_kw={"width_ratios": [1, 1, 0.9]})
    profile(axes[0], prof, "ocdr30_speed_m_s", "Swim speed (m s$^{-1}$)",
            "a  Measured speed (depth-rate, |pitch| ≥ 30°)")
    profile(axes[1], prof, "stroke_rms_deg", "Stroke effort (deg RMS)",
            "b  Stroke effort (valid at any body angle)")
    axes[0].legend(frameon=False, fontsize=9, loc="lower left")

    ax = axes[2]
    labels = {
        "matched_posture_direction_depth": "Speed",
        "power_matched": "Drag power",
        "energy_per_buzz_matched": "Energy per buzz",
    }
    rows = models[models.model.isin(labels)].copy()
    rows["label"] = rows.model.map(labels)
    order = ["Speed", "Drag power", "Energy per buzz"]
    for i, name in enumerate(order):
        for j, thr in enumerate((30, 45)):
            r = rows[(rows.label == name) & (rows.threshold_deg == thr)].iloc[0]
            y = i + (j - 0.5) * 0.28
            ax.plot([r.ci_low, r.ci_high], [y, y], color=INK2, lw=2, solid_capstyle="round")
            ax.plot(r.B_over_A, y, "o", ms=8, color=INK if thr == 30 else SURFACE,
                    mec=INK, mew=1.5)
            ax.annotate(f"{r.B_over_A:.2f}", (r.ci_high, y), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.axvline(1, color=INK2, lw=1, ls="--")
    ax.set_yticks(range(len(order)), order, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0.8, 3.2)
    ax.set_xlabel("Type B ÷ Type A (95% CI)", color=INK, fontsize=9)
    ax.set_title("c  Matched for body angle, direction, depth", loc="left", fontsize=10, color=INK)
    ax.plot([], [], "o", color=INK, mec=INK, label="|pitch| ≥ 30°")
    ax.plot([], [], "o", color=SURFACE, mec=INK, mew=1.5, label="|pitch| ≥ 45°")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax)
    ax.grid(False)
    fig.tight_layout()
    out = RES / "figures" / "speed_effort_profiles.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(out)


if __name__ == "__main__":
    main()
