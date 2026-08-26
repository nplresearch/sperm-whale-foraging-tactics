"""Compact figure-source plots for the trajectory-scale results."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np


def plot_mu_distribution(per_dive, *, ax=None):
    ax = ax or plt.subplots(figsize=(5, 3.8))[1]
    values = per_dive["mu"].dropna()
    ax.hist(values, bins=30, color="#2A92D5", edgecolor="white")
    ax.axvline(values.median(), color="#D56D2A", label=f"median = {values.median():.2f}")
    ax.axvline(2, color="#338833", linestyle="--", label="mu = 2")
    ax.axvspan(1, 3, color="#338833", alpha=0.06)
    ax.set(xlabel="Per-dive step exponent, mu", ylabel="Number of dives")
    ax.legend(frameon=False)
    return ax


def plot_timescale_msd(timescale, *, ax=None):
    ax = ax or plt.subplots(figsize=(5.5, 3.8))[1]
    columns = [
        "alpha_short_le_1min",
        "alpha_mid_1_5min",
        "alpha_long_5_15min",
        "alpha_very_long_ge_15min",
    ]
    labels = ["<=1 min", "1-5 min", "5-15 min", ">=15 min"]
    values = [timescale[column].dropna().to_numpy() for column in columns]
    positions = np.arange(len(columns))
    ax.boxplot(values, positions=positions, showfliers=False)
    ax.plot(positions, [np.median(value) for value in values], "o", color="#D56D2A")
    ax.axhline(1, color=".55", linestyle="--", label="Brownian")
    ax.axhline(2, color=".2", linestyle=":", label="Ballistic")
    ax.set(
        xticks=positions,
        xticklabels=labels,
        xlabel="Lag window",
        ylabel="MSD exponent, alpha",
    )
    ax.legend(frameon=False)
    return ax
