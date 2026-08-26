"""Manuscript-facing figure adapters for Azores and CETI validation."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import fisher_exact

from .azores import run_azores_validation
from .ceti2024 import classify_corner, kinematic_statistics, sequence_statistics


def _bar_contrasts(ax, table, title):
    if table.empty:
        ax.text(0.5, 0.5, "No contrast", ha="center", va="center")
        ax.set_axis_off()
        return
    value = "mean_A" if "mean_A" in table else "median_A"
    other = "mean_B" if "mean_B" in table else "median_B"
    table.set_index("metric")[[value, other]].plot.bar(ax=ax)
    ax.set_title(title)
    ax.set_ylabel("A/B estimate")


def azores_manuscript_figure(result):
    """Show operative 28/28/2 and balanced 29/29 contrasts side by side."""
    fig, axes = plt.subplots(3, 4, figsize=(15, 10), constrained_layout=True)
    metrics = list(result["operative_contrasts"]["metric"].drop_duplicates())
    for row, table, title in (
        (0, result["operative_contrasts"], "Operative 28/28/2"),
        (1, result["balanced_contrasts"], "Balanced 29/29 sensitivity"),
    ):
        for col, metric in enumerate(metrics):
            ax = axes[row, col]
            group = table[table["metric"].eq(metric)]
            ax.bar(
                ["A", "B"],
                [group["median_a"].iloc[0], group["median_b"].iloc[0]],
                color=["#2A92D5", "#D56D2A"],
            )
            ax.set_title(f"{title}\n{metric.replace('_', ' ')}")
    geometry = (
        result["geometry"]
        .pivot(index="operative_type", columns="geometry_group", values="proportion")
        .reindex(index=["A", "B"], columns=["oscillatory", "persistent"])
    )
    geometry.plot.bar(stacked=True, ax=axes[0, 3], color=["#7AA6C2", "#D7A86E"])
    axes[0, 3].set(title="Vertical geometry", ylabel="Proportion", xlabel="Type")
    robustness = result["robustness"]
    corner = robustness[robustness["analysis"].eq("corner_split")]
    for metric, group in corner.groupby("metric"):
        axes[1, 3].plot(
            group["n_per_corner"], group["p_value"], marker="o", label=metric.replace("_", " ")
        )
    axes[1, 3].axhline(0.05, color=".4", ls="--", lw=0.8)
    axes[1, 3].set(title="Corner-size robustness", xlabel="Events per corner", ylabel="P value")
    axes[1, 3].legend(frameon=False, fontsize=7)
    events = result["events"]
    events.plot.scatter(
        "ramp_rank",
        "speed_rank",
        ax=axes[2, 0],
        c=events["operative_type"].map({"A": "#2A92D5", "B": "#D56D2A", "unclassified": "#999999"}),
    )
    axes[2, 0].set(title="Rank-space classification", xlabel="Ramp rank", ylabel="Speed rank")
    events.boxplot(column="pre_buzz_vertical_speed_m_s", by="operative_type", ax=axes[2, 1])
    axes[2, 1].set_title("Pre-buzz vertical speed")
    events.boxplot(column="post_buzz_pause_s", by="operative_type", ax=axes[2, 2])
    axes[2, 2].set_title("Pause categories/durations")
    axes[2, 2].figure.suptitle("")
    markov = result["markov"]
    matrix = markov.pivot(index="from_state", columns="to_state", values="probability")
    axes[2, 3].imshow(matrix.fillna(0), vmin=0, vmax=1, cmap="Blues")
    axes[2, 3].set_title("Markov transitions")
    return fig


def run_and_plot_azores(source_directory, *, output_directory=None, n_boot=2000):
    """Run the checksummed analysis and return its in-memory figure."""
    result = run_azores_validation(source_directory, output_directory, n_boot=n_boot)
    fig = azores_manuscript_figure(result)
    return result, fig


def ceti2024_manuscript_figure(df):
    """Plot supported CETI classification, kinematics, and sequence panels."""
    labels = classify_corner(df)
    stats = kinematic_statistics(df, labels)
    sequence = sequence_statistics(df, labels)
    fig, axes = plt.subplots(1, 5, figsize=(19, 4), constrained_layout=True)
    valid = df.dropna(subset=["ramp_up_duration_s", "speed_3d_mps"]).copy()
    valid["label"] = labels.loc[valid.index]
    for label, group in valid.groupby("label"):
        axes[0].scatter(group.ramp_up_duration_s, group.speed_3d_mps, s=18, label=label)
    axes[0].set(xlabel="Ramp-up duration (s)", ylabel="3-D speed (m/s)", title="Classification")
    axes[0].legend(frameon=False)
    if not stats.empty:
        stats.set_index("metric")[["median_A", "median_B"]].plot.bar(ax=axes[1], legend=False)
    axes[1].set_title("Supported kinematics")
    matrix = sequence.pivot(index="from_state", columns="to_state", values="probability").fillna(0)
    axes[2].imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    axes[2].set_title("Sequence transitions")
    geometry_valid = valid[
        valid["label"].isin(["A", "B"])
        & valid["vertical_direction_before"].isin([-1, 1])
        & valid["vertical_direction_after"].isin([-1, 1])
    ].copy()
    geometry_valid["geometry_group"] = (
        geometry_valid["vertical_direction_before"]
        .eq(geometry_valid["vertical_direction_after"])
        .map({True: "persistent", False: "oscillatory"})
    )
    contingency = pd.crosstab(geometry_valid["label"], geometry_valid["geometry_group"]).reindex(
        index=["A", "B"], columns=["persistent", "oscillatory"], fill_value=0
    )
    if contingency.shape == (2, 2):
        fisher_p = fisher_exact(contingency.to_numpy())[1]
    else:
        fisher_p = float("nan")
    proportions = contingency.div(contingency.sum(axis=1), axis=0)
    proportions.T.plot.bar(ax=axes[3])
    axes[3].set_title(f"Geometry proportions; Fisher p={fisher_p:.3g}")
    axes[3].set_ylabel("Proportion")
    axes[4].text(
        0.5,
        0.5,
        "Unavailable: per-bin roll time course\nrequires reviewed roll data",
        ha="center",
        va="center",
    )
    axes[4].set_axis_off()
    return fig, {
        "labels": labels,
        "kinematic_statistics": stats,
        "sequence_statistics": sequence,
        "geometry_proportions": proportions,
        "fisher_p": fisher_p,
        "unavailable": ["per_bin_roll_time_course"],
    }
