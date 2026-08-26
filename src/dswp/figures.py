"""Small, data-safe figure helpers for numerical DSWP event-table panels."""

import matplotlib.pyplot as plt
import numpy as np

from .pauses import PAUSE_LABELS, pause_category_table

COLOR_A, COLOR_B = "#2A92D5", "#D56D2A"


def plot_pause_distribution(events, *, ax=None):
    """Plot normalized A/B pause densities and the manuscript bin boundaries."""
    ax = ax or plt.subplots(figsize=(5, 3.5))[1]
    for typ, color in (("A", COLOR_A), ("B", COLOR_B)):
        x = events.loc[events.buzz_type.eq(typ), "post_buzz_pause_s"].dropna()
        if len(x):
            ax.hist(
                x,
                bins=35,
                density=True,
                histtype="step",
                lw=2,
                color=color,
                label=f"Type {typ} (n={len(x)})",
            )
    for value in (1.3, 3.4, 6.0):
        ax.axvline(value, color="0.4", lw=0.8, ls="--")
    ax.set(xlabel="Post-buzz pause (s)", ylabel="Probability density")
    ax.legend(frameon=False)
    return ax


def plot_pause_categories(events, *, ax=None):
    """Plot A/B category proportions with binomial standard-error bars."""
    ax = ax or plt.subplots(figsize=(5, 3.5))[1]
    table = pause_category_table(events)
    width = 0.36
    positions = np.arange(len(PAUSE_LABELS))
    for offset, typ, color in ((-width / 2, "A", COLOR_A), (width / 2, "B", COLOR_B)):
        data = table[table.buzz_type.eq(typ)].set_index("pause_category").reindex(PAUSE_LABELS)
        ax.bar(
            positions + offset,
            data.proportion,
            width,
            yerr=data.binomial_se,
            color=color,
            capsize=2,
            label=f"Type {typ}",
        )
    ax.set(
        xticks=positions,
        xticklabels=[x.replace("_", " ") for x in PAUSE_LABELS],
        ylabel="Proportion",
    )
    ax.legend(frameon=False)
    return ax


def plot_individual_energy(paired, *, ax=None):
    """Paired A/B energy panel from approved opaque individual-level means."""
    ax = ax or plt.subplots(figsize=(4.5, 4))[1]
    for _, row in paired.dropna(subset=["A", "B"]).iterrows():
        ax.plot([0, 1], [row.A / 1e6, row.B / 1e6], color=".7", lw=0.8, zorder=1)
    for x, col, label in ((0, "A", "Type A"), (1, "B", "Type B")):
        data = paired[col].dropna() / 1e6
        ax.scatter(
            np.repeat(x, len(data)),
            data,
            color=COLOR_A if col == "A" else COLOR_B,
            label=label,
            zorder=2,
        )
    ax.set(
        xticks=[0, 1],
        xticklabels=["Type A", "Type B"],
        ylabel="Mean estimated energy per buzz (MJ)",
    )
    return ax


def plot_classifier(events, *, ax=None):
    """Plot the registered acoustic--kinematic classifier plane."""
    ax = ax or plt.subplots(figsize=(5, 4.5))[1]
    for label, color, zorder in (
        ("?", ".75", 1),
        ("A", COLOR_A, 2),
        ("B", COLOR_B, 2),
    ):
        group = events[events["buzz_type"].eq(label)]
        ax.scatter(
            group["ramp_up_duration_s"],
            group["avg_speed_3d_m_s"],
            s=10,
            alpha=0.45,
            color=color,
            label=f"{label} (n={len(group)})",
            zorder=zorder,
        )
    ax.set(
        xscale="log",
        xlabel="Ramp-up duration (s)",
        ylabel="Classifier 3-D speed (m/s)",
    )
    ax.legend(frameon=False, markerscale=1.5)
    return ax


def plot_gmm_model_selection(selection, *, axes=None):
    """BIC curves for each registered acoustic--kinematic feature pair."""
    names = list(selection["feature_pair"].drop_duplicates())
    if axes is None:
        _, axes = plt.subplots(1, len(names), figsize=(11, 3.5))
    axes = np.atleast_1d(axes)
    for ax, name in zip(axes, names):
        group = selection.loc[selection["feature_pair"].eq(name)]
        optimum = int(group.loc[group["bic"].idxmin(), "n_components"])
        ax.plot(
            group["n_components"],
            group["delta_bic_from_k1"],
            marker="o",
            color="#4C72B0",
        )
        ax.axvline(optimum, color="#C44E52", linestyle=":")
        ax.set(
            xlabel="Components k",
            ylabel="ΔBIC from k=1",
            title=name.replace("_", " "),
            xticks=group["n_components"],
        )
    return axes


def plot_reconstruction_error_summary(errors, *, axes=None):
    """Plot safe, deployment-level reconstruction-error summaries."""
    order = [
        "pitch_adaptive_hybrid",
        "ocdr",
        "constant_speed",
        "depth_derived",
    ]
    labels = [
        "Pitch-adaptive",
        "Optimized\nconstant",
        "Constant\nspeed",
        "Depth-rate",
    ]
    colors = ["#2CA02C", "#FF7F0E", "#1F77B4", "#D62728"]
    if axes is None:
        _, axes = plt.subplots(
            1,
            3,
            figsize=(11, 4),
            gridspec_kw={"width_ratios": [1.8, 1.8, 1.0]},
        )
    axes = np.atleast_1d(axes)
    for ax, column, title in (
        (axes[0], "mean_error_m", "Mean error per deployment"),
        (axes[1], "median_error_m", "Median error per deployment"),
    ):
        values = [
            errors.loc[errors["reconstruction_method"].eq(method), column].to_numpy()
            for method in order
        ]
        violin = ax.violinplot(values, showextrema=False)
        for body, color in zip(violin["bodies"], colors):
            body.set_facecolor(color)
            body.set_alpha(0.35)
        for position, (sample, color) in enumerate(zip(values, colors), start=1):
            ax.scatter(
                np.full(len(sample), position),
                sample,
                s=18,
                color=color,
                alpha=0.75,
            )
            ax.hlines(
                np.median(sample),
                position - 0.16,
                position + 0.16,
                color="black",
                linewidth=1.5,
            )
        ax.set(
            xticks=np.arange(1, len(order) + 1),
            xticklabels=labels,
            ylabel="Reconstruction error (m)",
            title=title,
        )
        ax.tick_params(axis="x", labelrotation=20)

    winners = (
        errors.loc[errors.groupby("deployment_id")["mean_error_m"].idxmin()][
            "reconstruction_method"
        ]
        .value_counts()
        .reindex(order, fill_value=0)
    )
    axes[2].bar(np.arange(len(order)), winners.to_numpy(), color=colors)
    axes[2].set(
        xticks=np.arange(len(order)),
        xticklabels=labels,
        ylabel="Deployments with lowest mean error",
        title="Best method",
    )
    axes[2].tick_params(axis="x", labelrotation=20)
    return axes


def plot_roll_timecourse(events, roll_bins, *, ax=None):
    """Mean and standard error of the released 2-s roll-rate bins."""
    ax = ax or plt.subplots(figsize=(5.5, 3.8))[1]
    values = roll_bins.merge(
        events[["event_id", "buzz_type"]], on="event_id", validate="many_to_one"
    )
    values = values[values["buzz_type"].isin(["A", "B"])]
    summary = (
        values.groupby(["buzz_type", "time_bin_s"])["roll_speed_deg_s"]
        .agg(["mean", "sem"])
        .reset_index()
    )
    for label, color in (("A", COLOR_A), ("B", COLOR_B)):
        group = summary[summary["buzz_type"].eq(label)]
        ax.plot(group["time_bin_s"], group["mean"], color=color, label=f"Type {label}")
        ax.fill_between(
            group["time_bin_s"],
            group["mean"] - group["sem"],
            group["mean"] + group["sem"],
            color=color,
            alpha=0.2,
            linewidth=0,
        )
    ax.axvline(0, color=".3", linewidth=0.8)
    ax.set(
        xlabel="Time relative to buzz (s)",
        ylabel="Mean roll speed (deg/s)",
        xlim=(-10, 10),
    )
    ax.legend(frameon=False)
    return ax


def plot_markov(transitions, *, ax=None):
    """Heatmap of the released Start/A/B/End transition probabilities."""
    ax = ax or plt.subplots(figsize=(4.5, 3.5))[1]
    sources = ["S", "A", "B"]
    targets = ["A", "B", "E"]
    value_column = "mean_probability" if "mean_probability" in transitions else "probability"
    matrix = (
        transitions.pivot(index="from_state", columns="to_state", values=value_column)
        .reindex(index=sources, columns=targets)
        .fillna(0)
    )
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    ax.set(
        xticks=range(len(targets)),
        xticklabels=["A", "B", "End"],
        yticks=range(len(sources)),
        yticklabels=["Start", "A", "B"],
        xlabel="Next state",
        ylabel="Current state",
    )
    for i in range(len(sources)):
        for j in range(len(targets)):
            ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center")
    ax.figure.colorbar(image, ax=ax, label="Probability")
    return ax


def plot_comeback_forest(strata, summary, *, ax=None):
    """Deployment-level and pooled recurrence/tactic odds ratios."""
    ax = ax or plt.subplots(figsize=(6, 6))[1]
    values = strata.sort_values("deployment_id", ascending=False).reset_index(drop=True)
    y = np.arange(1, len(values) + 1)
    odds = values["odds_ratio_corrected"].to_numpy()
    low = values["ci_low_corrected"].to_numpy()
    high = values["ci_high_corrected"].to_numpy()
    ax.errorbar(
        odds,
        y,
        xerr=[odds - low, high - odds],
        fmt="o",
        color="teal",
        ecolor=".65",
        capsize=2,
        label="Deployment",
    )
    pooled = summary["pooled_odds_ratio"]
    ax.errorbar(
        pooled,
        0,
        xerr=[
            [pooled - summary["ci_low"]],
            [summary["ci_high"] - pooled],
        ],
        fmt="D",
        color="darkorange",
        ecolor="darkorange",
        label="Pooled CMH",
    )
    ax.axvline(1, color=".25", linestyle="--", linewidth=1)
    ax.set(
        xscale="log",
        yticks=np.r_[0, y],
        yticklabels=["Pooled", *values["deployment_id"]],
        xlabel="Odds ratio: Type A versus Type B in recurrence context",
        ylabel="Anonymous deployment",
    )
    ax.legend(frameon=False)
    return ax


def plot_comeback_depths(events, *, ax=None):
    """Median depth distribution of detected recurrence events."""
    ax = ax or plt.subplots(figsize=(5, 3.7))[1]
    ax.hist(
        events["event_depth_median_m"],
        bins=20,
        histtype="stepfilled",
        color="teal",
        edgecolor="teal",
        alpha=0.35,
    )
    ax.axvline(200, color=".35", linestyle="--", linewidth=1)
    ax.set(xlabel="Median recurrence-event depth (m)", ylabel="Count")
    return ax


def plot_comeback_ratios(deployments, *, ax=None):
    """Comeback-sample ratios for anonymous reconstructed deployments."""
    ax = ax or plt.subplots(figsize=(7, 3.7))[1]
    values = deployments.sort_values("comeback_ratio", ascending=False)
    ax.bar(
        np.arange(len(values)),
        100 * values["comeback_ratio"],
        color="teal",
        width=0.8,
    )
    ax.set(
        xticks=np.arange(len(values)),
        xticklabels=values["deployment_id"],
        xlabel="Anonymous deployment",
        ylabel="Comeback samples (%)",
    )
    ax.tick_params(axis="x", labelrotation=90, labelsize=7)
    return ax
