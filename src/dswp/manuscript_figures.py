"""Thin plotting adapters for the released DSWP manuscript components.

The functions here deliberately compose the existing analysis modules.  They
return Matplotlib figures and metadata; they never write files or embed data.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Patch
from mpl_toolkits.mplot3d.art3d import Line3DCollection

from trajectory.analysis import load_trajectory

from .classification import attach_labels, classifier_robustness, gmm_model_selection
from .comebacks import (
    attach_comeback_context,
    detect_comeback_events,
    stratified_comeback_association,
)
from .figures import (
    plot_classifier,
    plot_comeback_forest,
    plot_individual_energy,
    plot_markov,
    plot_pause_categories,
    plot_pause_distribution,
    plot_roll_timecourse,
)
from .io import load_buzz_events
from .pauses import PAUSE_LABELS, pause_category_table
from .statistics import (
    compare_groups,
    geometry_association,
    markov_leave_subset_out,
    roll_speed_bin_tests,
)

COLOR_A = "#2A92D5"
COLOR_B = "#D56D2A"
COLOR_UNKNOWN = "#B8B8B8"
PANEL_FONT = {"fontsize": 15, "fontweight": "bold"}


def _paper_axis(ax):
    """Apply the open-axis style used by the assembled manuscript figures."""
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.4)
    ax.spines["bottom"].set_linewidth(1.4)
    ax.tick_params(direction="out", width=1.3, length=4, labelsize=9)
    return ax


def _panel_label(ax, label, *, x=-0.13, y=1.05):
    if hasattr(ax, "text2D"):
        ax.text2D(x, y, f"({label})", transform=ax.transAxes, **PANEL_FONT)
    else:
        ax.text(x, y, f"({label})", transform=ax.transAxes, **PANEL_FONT)


def _ranked_classifier_panel(events, ax):
    values = events[["ramp_up_duration_s", "avg_speed_3d_m_s", "buzz_type"]].dropna()
    values = values.assign(
        ramp_rank=values["ramp_up_duration_s"].rank(pct=True),
        speed_rank=values["avg_speed_3d_m_s"].rank(pct=True),
    )
    for label, color, alpha, zorder in (
        ("?", COLOR_UNKNOWN, 0.14, 1),
        ("A", COLOR_A, 0.58, 2),
        ("B", COLOR_B, 0.58, 3),
    ):
        group = values.loc[values["buzz_type"].eq(label)]
        if len(group) > 2:
            sns.kdeplot(
                data=group,
                x="ramp_rank",
                y="speed_rank",
                fill=True,
                levels=8,
                thresh=0.05,
                clip=((0, 1), (0, 1)),
                color=color,
                alpha=alpha,
                ax=ax,
                zorder=zorder,
            )
    ax.text(0.18, 0.18, "Cluster A", ha="center", va="center", fontsize=9)
    ax.text(0.80, 0.82, "Cluster B", ha="center", va="center", fontsize=9)
    ax.set(
        xlim=(0, 1),
        ylim=(0, 1),
        xlabel="Duration of ramp-up (rank)",
        ylabel="Average 3D speed (rank)",
        xticks=np.linspace(0, 1, 6),
        yticks=np.linspace(0, 1, 6),
    )
    _paper_axis(ax)
    return values


def _individual_counts_panel(events, ax):
    counts = (
        events.loc[events["buzz_type"].isin(["A", "B"])]
        .groupby(["individual_id", "buzz_type"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["A", "B"], fill_value=0)
    )
    counts = counts.assign(total=counts.sum(axis=1)).sort_values("total", ascending=False)
    x = np.arange(len(counts))
    ax.bar(x, counts["A"], width=0.8, color=COLOR_A, alpha=0.82)
    ax.bar(x, counts["B"], width=0.8, bottom=counts["A"], color=COLOR_B, alpha=0.82)
    for position, (individual, row) in enumerate(counts.iterrows()):
        ax.text(
            position,
            row["total"] + 4,
            individual,
            rotation=90,
            ha="center",
            va="bottom",
            fontsize=6.5,
        )
    ax.set(
        xlim=(-0.6, len(counts) - 0.4),
        ylim=(0, max(400, counts["total"].max() + 45)),
        xticks=[],
        yticks=[0, 100, 200, 300, 400],
        xlabel="Whale ID",
        ylabel="Number of buzzes",
    )
    _paper_axis(ax)
    return counts.drop(columns="total")


def _vertical_speed_panel(events, ax):
    bins = np.linspace(-3, 3, 43)
    for label, color in (("A", COLOR_A), ("B", COLOR_B)):
        values = events.loc[
            events["buzz_type"].eq(label), "pre_buzz_vertical_velocity_m_s"
        ].dropna()
        ax.hist(values, bins=bins, density=True, histtype="stepfilled", color=color, alpha=0.35)
        ax.hist(values, bins=bins, density=True, histtype="step", color=color, linewidth=1.0)
        sns.kdeplot(x=values, color=color, linewidth=1.4, clip=(-3, 3), ax=ax)
    ax.axvline(0, color="0.45", linestyle="--", linewidth=0.8)
    ax.text(-1.55, 0.48, "Negative speed:\ngoing up", ha="center", color="0.35", fontsize=7)
    ax.text(1.55, 0.48, "Positive speed:\ngoing down", ha="center", color="0.35", fontsize=7)
    ax.set(xlim=(-3, 3), ylim=(0, 0.85), xlabel="Vertical speed (m/s)", ylabel="Density")
    ax.legend(
        handles=[
            Patch(color=COLOR_A, alpha=0.5, label="Type A"),
            Patch(color=COLOR_B, alpha=0.5, label="Type B"),
        ],
        frameon=False,
        fontsize=8,
    )
    _paper_axis(ax)


def _roll_panel(events, roll_bins, ax):
    values = roll_bins.merge(
        events[["event_id", "buzz_type"]], on="event_id", validate="many_to_one"
    )
    values = values.loc[values["buzz_type"].isin(["A", "B"])]
    summary = (
        values.groupby(["buzz_type", "time_bin_s"])["roll_speed_deg_s"]
        .agg(["mean", "sem"])
        .reset_index()
    )
    for label, color in (("A", COLOR_A), ("B", COLOR_B)):
        group = summary.loc[summary["buzz_type"].eq(label)].sort_values("time_bin_s")
        x = group["time_bin_s"].to_numpy(float)
        mean = group["mean"].to_numpy(float)
        sem = group["sem"].to_numpy(float)
        ax.fill_between(x, mean - sem, mean + sem, color=color, alpha=0.2, linewidth=0)
        ax.plot(x, mean, color=color, marker="o", markersize=3.5, linewidth=1.6)
    ax.axvspan(-1, 1, color="0.7", alpha=0.16, zorder=0)
    tests = roll_speed_bin_tests(events, roll_bins)
    y_top = max(11.0, float((summary["mean"] + summary["sem"]).max()) * 1.15)
    for row in tests.loc[tests["significant_0_05"]].itertuples(index=False):
        stars = (
            "***"
            if row.p_value_bonferroni < 0.001
            else "**"
            if row.p_value_bonferroni < 0.01
            else "*"
        )
        local = summary.loc[summary["time_bin_s"].eq(row.time_bin_s)]
        y = float((local["mean"] + local["sem"]).max()) + 0.18
        ax.text(row.time_bin_s, y, stars, ha="center", va="bottom", fontsize=7, fontweight="bold")
    ticks = np.arange(-10, 11, 2)
    ax.set(
        xlim=(-11, 11),
        ylim=(4, y_top),
        xticks=ticks,
        xticklabels=[f"+{value}" if value > 0 else str(value) for value in ticks],
        xlabel="Time relative to buzz (s)",
        ylabel="Roll speed (deg/s)",
    )
    _paper_axis(ax)
    return summary, tests


def _geometry_panel(events, ax):
    geometry, test = geometry_association(events)
    table = geometry.pivot(index="buzz_type", columns="geometry", values="count").reindex(
        index=["A", "B"]
    )
    order = ["down_to_down", "up_to_up", "down_to_up", "up_to_down"]
    table = table.reindex(columns=order, fill_value=0)
    proportions = table.div(table.sum(axis=1), axis=0)
    colors = ["#CC6B6B", "#E1B64F", "#D9C2DA", "#72409A"]
    labels = ["down-down", "up-up", "down-up", "up-down"]
    bottom = np.zeros(2)
    x = np.arange(2)
    for column, color, label in zip(order, colors, labels):
        values = proportions[column].to_numpy(float)
        ax.bar(
            x,
            values,
            bottom=bottom,
            width=0.42,
            color=color,
            edgecolor="white",
            linewidth=1,
            label=label,
        )
        for position, value, base in zip(x, values, bottom):
            if value >= 0.07:
                ax.text(
                    position,
                    base + value / 2,
                    f"{100 * value:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                )
        bottom += values
    ax.set(
        xticks=x,
        xticklabels=["A", "B"],
        ylim=(0, 1),
        xlabel="Buzz type",
        ylabel="Proportion of buzzes",
    )
    ax.legend(frameon=False, fontsize=6.5, loc="center", bbox_to_anchor=(0.5, 0.5))
    _paper_axis(ax)
    return proportions, test


def _energy_panel(events, energy_events, order, ax):
    values = energy_events.loc[energy_events["buzz_type"].isin(["A", "B"])].copy()
    order = [individual for individual in order if individual in set(values["individual_id"])]
    positions = np.arange(len(order))
    for label, color, offset in (("A", COLOR_A, -0.18), ("B", COLOR_B, 0.18)):
        samples = [
            values.loc[
                (values["individual_id"].eq(individual)) & (values["buzz_type"].eq(label)),
                "E_total_J",
            ].dropna()
            for individual in order
        ]
        box = ax.boxplot(
            samples,
            positions=positions + offset,
            widths=0.32,
            patch_artist=True,
            showfliers=True,
            manage_ticks=False,
            medianprops={"color": "white", "linewidth": 0.8},
            whiskerprops={"color": "black", "linewidth": 0.7},
            capprops={"color": "black", "linewidth": 0.7},
            flierprops={"marker": ".", "markersize": 1.5, "markeredgecolor": color, "alpha": 0.5},
        )
        for patch in box["boxes"]:
            patch.set_facecolor(color)
            patch.set_alpha(0.62)
            patch.set_edgecolor(color)
    ax.set(
        xlim=(-0.7, len(order) - 0.3),
        xticks=[],
        xlabel="Whale ID",
        ylabel="Total energy per buzz (J)",
    )
    ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    for position, individual in enumerate(order):
        ax.text(
            position,
            0.97,
            individual,
            transform=ax.get_xaxis_transform(),
            rotation=90,
            ha="center",
            va="top",
            fontsize=6,
        )
    ax.legend(
        handles=[
            Patch(facecolor=COLOR_A, alpha=0.62, label="Type A"),
            Patch(facecolor=COLOR_B, alpha=0.62, label="Type B"),
        ],
        frameon=False,
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(0.0, 0.87),
    )
    _paper_axis(ax)


def _representative_trajectory_panel(events, trajectory_index_path, ax, *, trajectory_id="T127"):
    index_path = Path(trajectory_index_path)
    metadata = pd.read_csv(index_path).set_index("trajectory_id").loc[trajectory_id]
    xyz = load_trajectory(index_path.parent / metadata["file"])
    fs_hz = float(metadata["sampling_rate_hz"])
    speed = np.linalg.norm(np.diff(xyz, axis=0), axis=1) * fs_hz
    window_samples = int(round(6 * fs_hz))
    speed = np.convolve(speed, np.ones(window_samples) / window_samples, mode="valid")
    offset = len(xyz) - 1 - len(speed)
    aligned_xyz = xyz[offset : offset + len(speed)]
    time_s = np.arange(len(speed)) / fs_hz
    selected = events.loc[events["trajectory_id"].eq(trajectory_id)].sort_values(
        "buzz_order_in_dive"
    )
    centre = float(selected.loc[selected["buzz_order_in_dive"].eq(15), "buzz_start_s"].iloc[0])
    half_window_s = 50.0
    mask = (time_s >= centre - half_window_s) & (time_s <= centre + half_window_s)
    segment_xyz = aligned_xyz[mask]
    segment_speed = speed[mask]
    points = segment_xyz.reshape(-1, 1, 3)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    line = Line3DCollection(segments, cmap="plasma", norm=plt.Normalize(1, 2), linewidth=2.1)
    line.set_array(segment_speed[:-1])
    ax.add_collection3d(line)
    ax.set_xlim(segment_xyz[:, 0].min(), segment_xyz[:, 0].max())
    ax.set_ylim(segment_xyz[:, 1].min(), segment_xyz[:, 1].max())
    ax.set_zlim(segment_xyz[:, 2].min(), segment_xyz[:, 2].max())
    ax.invert_zaxis()
    ax.set_box_aspect((2.0, 1.0, 0.75), zoom=1.35)
    ax.view_init(elev=18, azim=-78)
    ax.grid(False)
    ax.xaxis.set_pane_color((1, 1, 1, 0))
    ax.yaxis.set_pane_color((1, 1, 1, 0))
    ax.zaxis.set_pane_color((1, 1, 1, 0))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zlabel("Depth (m)", labelpad=2, fontsize=8)
    ax.tick_params(labelsize=7, pad=-2)
    shown = selected.loc[
        selected["buzz_start_s"].between(centre - half_window_s, centre + half_window_s)
    ]
    for event in shown.itertuples(index=False):
        nearest = int(np.argmin(np.abs(time_s - float(event.buzz_start_s))))
        position = aligned_xyz[nearest]
        color = (
            COLOR_A
            if event.buzz_type == "A"
            else COLOR_B
            if event.buzz_type == "B"
            else COLOR_UNKNOWN
        )
        ax.scatter(
            *position,
            color=color,
            edgecolor="black",
            linewidth=0.6,
            s=48,
            depthshade=False,
            zorder=20,
        )
        if event.buzz_type in ("A", "B"):
            ax.text(*position, f"  Buzz {event.buzz_type}", fontsize=7, zorder=30)
    color_axis = ax.inset_axes([0.28, 0.93, 0.48, 0.025])
    colorbar = ax.figure.colorbar(line, cax=color_axis, orientation="horizontal", ticks=[1, 2])
    colorbar.ax.xaxis.set_ticks_position("top")
    colorbar.ax.xaxis.set_label_position("top")
    colorbar.set_label("Speed (m/s)", fontsize=7, labelpad=-1)
    colorbar.ax.tick_params(labelsize=6, length=2, pad=1)
    ax.annotate(
        "Direction\nof movement",
        xy=(0.63, 0.20),
        xytext=(0.49, 0.30),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "->", "color": "0.25", "connectionstyle": "arc3,rad=-0.25"},
        ha="center",
        fontsize=6.5,
    )
    return {
        "trajectory_id": trajectory_id,
        "centre_buzz_order": 15,
        "duration_s": 2 * half_window_s,
    }


def dswp_tactics_manuscript_figure(events, *, roll_bins, energy_events, trajectory_index_path):
    """Recreate the seven-panel DSWP tactics figure from safe release inputs."""
    events = events if "buzz_type" in events else attach_labels(events)
    fig = plt.figure(figsize=(13.2, 10.6))
    grid = fig.add_gridspec(
        3,
        14,
        height_ratios=[1.02, 1.0, 0.70],
        left=0.06,
        right=0.985,
        bottom=0.07,
        top=0.965,
        wspace=1.15,
        hspace=0.40,
    )
    axes = {
        "trajectory": fig.add_subplot(grid[0, :6], projection="3d"),
        "classifier": fig.add_subplot(grid[0, 6:10]),
        "individuals": fig.add_subplot(grid[0, 10:]),
        "vertical_speed": fig.add_subplot(grid[1, :5]),
        "roll": fig.add_subplot(grid[1, 5:10]),
        "geometry": fig.add_subplot(grid[1, 10:]),
        "energy": fig.add_subplot(grid[2, :]),
    }
    trajectory = _representative_trajectory_panel(events, trajectory_index_path, axes["trajectory"])
    ranks = _ranked_classifier_panel(events, axes["classifier"])
    counts = _individual_counts_panel(events, axes["individuals"])
    _vertical_speed_panel(events, axes["vertical_speed"])
    roll_summary, roll_tests = _roll_panel(events, roll_bins, axes["roll"])
    geometry, geometry_test = _geometry_panel(events, axes["geometry"])
    _energy_panel(events, energy_events, counts.index, axes["energy"])
    for label, key in zip("abcdef", list(axes)[:6]):
        _panel_label(axes[key], label)
    _panel_label(axes["energy"], "g", x=-0.045, y=1.05)
    return fig, {
        "trajectory": trajectory,
        "classifier_ranks": ranks,
        "individual_counts": counts,
        "roll_summary": roll_summary,
        "roll_tests": roll_tests,
        "geometry_proportions": geometry,
        "geometry_test": geometry_test,
    }


def _transition_lookup(transitions):
    value = "mean_probability" if "mean_probability" in transitions else "probability"
    std = "std_probability" if "std_probability" in transitions else None
    return {
        (row.from_state, row.to_state): (
            float(getattr(row, value)),
            float(getattr(row, std)) if std else np.nan,
        )
        for row in transitions.itertuples(index=False)
    }


def _markov_graph_panel(transitions, ax):
    values = _transition_lookup(transitions)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    node = {"B": (0.30, 0.70), "A": (0.72, 0.32)}

    def edge(start, end, *, color="black", rad=0.0, width=1.5):
        patch = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=width,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=16,
            shrinkB=16,
        )
        ax.add_patch(patch)

    edge((0.10, 0.14), node["B"], color="0.5", rad=-0.18, width=1.8)
    edge((0.12, 0.10), node["A"], color="0.5", rad=0.22, width=1.8)
    edge(node["B"], (0.91, 0.87), color="0.5", rad=-0.18, width=1.8)
    edge(node["A"], (0.92, 0.78), color="0.5", rad=0.15, width=1.8)
    edge(node["B"], node["A"], rad=-0.22, width=1.7)
    edge(node["A"], node["B"], rad=-0.29, width=1.7)
    for key, center, theta1, theta2 in (("B", node["B"], 5, 300), ("A", node["A"], 185, 500)):
        ax.add_patch(
            Arc(center, 0.22, 0.21, theta1=theta1, theta2=theta2, linewidth=1.7, color="black")
        )
    ax.add_patch(
        FancyArrowPatch(
            (0.235, 0.79), (0.248, 0.765), arrowstyle="-|>", mutation_scale=12, color="black"
        )
    )
    ax.add_patch(
        FancyArrowPatch(
            (0.79, 0.25), (0.77, 0.245), arrowstyle="-|>", mutation_scale=12, color="black"
        )
    )
    for label, color in (("A", COLOR_A), ("B", COLOR_B)):
        ax.add_patch(Circle(node[label], 0.095, facecolor=color, edgecolor="none", zorder=5))
        ax.text(
            *node[label],
            label,
            ha="center",
            va="center",
            color="white",
            fontsize=22,
            fontweight="bold",
            zorder=6,
        )
    ax.text(0.03, 0.05, "Start", fontsize=14, fontstyle="italic")
    ax.text(0.91, 0.91, "End", fontsize=14, fontstyle="italic")

    def probability(left, right):
        mean, std = values[(left, right)]
        return f"{mean:.2f}" + (f"$\\pm${std:.2f}" if np.isfinite(std) else "")

    labels = {
        ("S", "B"): (0.03, 0.39),
        ("S", "A"): (0.42, 0.06),
        ("B", "E"): (0.49, 0.88),
        ("A", "E"): (0.79, 0.62),
        ("B", "A"): (0.46, 0.55),
        ("A", "B"): (0.38, 0.25),
        ("B", "B"): (0.13, 0.90),
        ("A", "A"): (0.75, 0.13),
    }
    for transition, position in labels.items():
        ax.text(*position, probability(*transition), fontsize=9, ha="center")


def _straightness_panel(events, metric, title, ax):
    comparison = compare_groups(events, metric)
    for label, color in (("A", COLOR_A), ("B", COLOR_B)):
        values = events.loc[events["buzz_type"].eq(label), metric].dropna()
        sns.kdeplot(
            x=values, color=color, linewidth=1.8, fill=True, alpha=0.28, clip=(0.85, 1), ax=ax
        )
    p_value = comparison["p_value"]
    p_text = "p < 0.01" if p_value < 0.01 else f"p = {p_value:.2f}"
    ax.text(
        0.38,
        0.58,
        p_text + f"\n$\\delta$={comparison['cliffs_delta']:.2f}",
        transform=ax.transAxes,
        fontsize=10,
    )
    ax.set(xlim=(0.85, 1.0), xlabel="Straightness index", title=title)
    _paper_axis(ax)
    return comparison


def _pause_distribution_panel(events, ax):
    bins = np.linspace(0, 15, 26)
    for label, color in (("A", COLOR_A), ("B", COLOR_B)):
        values = events.loc[events["buzz_type"].eq(label), "post_buzz_pause_s"].dropna()
        ax.hist(values, bins=bins, density=True, histtype="stepfilled", alpha=0.30, color=color)
        ax.hist(values, bins=bins, density=True, histtype="step", linewidth=1.5, color=color)
    for boundary in (1.3, 3.4, 6.0):
        ax.axvline(boundary, color="0.75", linestyle="--", linewidth=0.7)
    for label, x in (("Short", 0.65), ("Medium", 2.35), ("Long", 4.7), ("Very long", 7.2)):
        ax.text(
            x,
            0.96,
            label,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            color="0.45",
            fontsize=8,
        )
    ax.set(
        xlim=(0, 15),
        ylim=(0, 0.4),
        xticks=[0, 3, 6, 9, 12, 15],
        xlabel="Pause duration (s)",
        ylabel="Density",
    )
    _paper_axis(ax)
    inset = ax.inset_axes([0.58, 0.56, 0.36, 0.31])
    inset.set_xlim(0, 1)
    inset.set_ylim(0, 1)
    inset.axis("off")
    inset.plot([0.05, 0.95], [0.5, 0.5], color="0.75", linestyle="--", linewidth=1)
    for x, height in zip(np.linspace(0.10, 0.35, 8), [0.35, 0.55, 0.75, 0.9, 0.7, 0.55, 0.4, 0.25]):
        inset.plot([x, x], [0.5 - height / 4, 0.5 + height / 4], color=COLOR_A, linewidth=1.5)
    inset.plot([0.70, 0.70], [0.28, 0.72], color="#352F7E", linewidth=2)
    inset.annotate(
        "", xy=(0.69, 0.22), xytext=(0.39, 0.22), arrowprops={"arrowstyle": "|-|", "color": "0.25"}
    )
    inset.text(0.54, 0.08, "Pause", ha="center", fontsize=8)
    inset.text(0.22, 0.82, "Buzz", color=COLOR_A, ha="center", fontsize=7)
    inset.text(
        0.70,
        0.82,
        "First click\nafter buzz",
        color="#352F7E",
        ha="center",
        fontsize=6.5,
        linespacing=0.8,
    )


def _pause_categories_panel(events, ax):
    table = pause_category_table(events)
    x = np.arange(len(PAUSE_LABELS))
    for label, color, offset in (("A", COLOR_A, -0.08), ("B", COLOR_B, 0.08)):
        group = (
            table.loc[table["buzz_type"].eq(label)]
            .set_index("pause_category")
            .reindex(PAUSE_LABELS)
        )
        ax.errorbar(
            x + offset,
            group["proportion"],
            yerr=group["binomial_se"],
            fmt="o",
            color=color,
            markersize=7,
            capsize=4,
            linewidth=1.8,
        )
    ax.set(
        xticks=x,
        xticklabels=["Short\npause", "Medium\npause", "Long\npause", "Very long\npause"],
        ylim=(0.15, 0.355),
        yticks=[0.15, 0.20, 0.25, 0.30, 0.35],
        ylabel="Proportion",
    )
    _paper_axis(ax)
    return table


def dswp_sequence_manuscript_figure(events, *, straightness, transitions):
    """Recreate the four-panel sequence, straightness, and pause figure."""
    events = events if "buzz_type" in events else attach_labels(events)
    columns = [column for column in straightness if column != "event_id"]
    if not set(columns).issubset(events):
        events = events.merge(straightness, on="event_id", how="left", validate="one_to_one")
    fig = plt.figure(figsize=(13.2, 8.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 10, height_ratios=[1, 1.05])
    axes = {
        "markov": fig.add_subplot(grid[0, :4]),
        "straight_before": fig.add_subplot(grid[0, 4:7]),
        "straight_after": fig.add_subplot(grid[0, 7:]),
        "pause_distribution": fig.add_subplot(grid[1, :6]),
        "pause_categories": fig.add_subplot(grid[1, 6:]),
    }
    _markov_graph_panel(transitions, axes["markov"])
    before = _straightness_panel(
        events, "straightness_before_20m", r"20 m $\it{before}$ buzz", axes["straight_before"]
    )
    after = _straightness_panel(
        events, "straightness_after_20m", r"20 m $\it{after}$ buzz", axes["straight_after"]
    )
    axes["straight_before"].set_ylabel("Density")
    axes["straight_after"].set_ylabel("")
    _pause_distribution_panel(events, axes["pause_distribution"])
    categories = _pause_categories_panel(events, axes["pause_categories"])
    _panel_label(axes["markov"], "a", x=-0.04)
    _panel_label(axes["straight_before"], "b", x=-0.18)
    _panel_label(axes["pause_distribution"], "c", x=-0.08)
    _panel_label(axes["pause_categories"], "d", x=-0.16)
    return fig, {
        "straightness_before": before,
        "straightness_after": after,
        "pause_categories": categories,
    }


def _unavailable(ax, message: str):
    ax.text(0.5, 0.5, "Unavailable\n" + message, ha="center", va="center", wrap=True)
    ax.set_axis_off()
    return ax


def dswp_component_figure(events, *, roll_bins=None, energy=None, transitions=None):
    """Assemble supported DSWP panels and report data-gated panels."""
    events = events if "buzz_type" in events else attach_labels(events)
    fig, axes = plt.subplots(4, 4, figsize=(15, 13), constrained_layout=True)
    plot_classifier(events, ax=axes[0, 0])
    plot_pause_distribution(events, ax=axes[0, 1])
    plot_pause_categories(events, ax=axes[0, 2])
    if roll_bins is not None:
        plot_roll_timecourse(events, roll_bins, ax=axes[0, 3])
    else:
        _unavailable(axes[0, 3], "released roll-bin table not supplied")
    if energy is not None and {"A", "B"}.issubset(energy.columns):
        plot_individual_energy(energy, ax=axes[1, 0])
    else:
        _unavailable(axes[1, 0], "individual energy table")
    if transitions is None:
        transitions = markov_leave_subset_out(events)
    plot_markov(transitions, ax=axes[1, 1])
    geometry, geometry_test = geometry_association(events)
    if not geometry.empty:
        proportions = geometry.assign(
            proportion=lambda x: x["count"] / x.groupby("buzz_type")["count"].transform("sum")
        )
        proportions.pivot(index="buzz_type", columns="geometry", values="proportion").plot.bar(
            ax=axes[1, 2]
        )
        axes[1, 2].set_ylabel("Proportion")
    else:
        _unavailable(axes[1, 2], "geometry summaries")
    metrics = ["avg_vertical_speed_m_s", "avg_roll_speed_deg_s", "straightness_before_20m"]
    available = [m for m in metrics if m in events]
    if available:
        rows = [compare_groups(events, metric) for metric in available]
        pd.DataFrame(rows).set_index("metric")[["median_A", "median_B"]].plot.bar(ax=axes[1, 3])
        axes[1, 3].set_ylabel("Group median")
    else:
        _unavailable(axes[1, 3], "kinematic summaries")
    if "individual_id" in events:
        proportions = (
            events[events.buzz_type.isin(["A", "B"])]
            .groupby(["individual_id", "buzz_type"])
            .size()
            .unstack(fill_value=0)
        )
        proportions.div(proportions.sum(axis=1), axis=0).plot.bar(
            stacked=True, ax=axes[2, 0], color=["#2A92D5", "#D56D2A"]
        )
        axes[2, 0].set(
            title="Individual tactic proportions", ylabel="Proportion", xlabel="Individual"
        )
    else:
        _unavailable(axes[2, 0], "individual identifiers")
    if "avg_depth_m" in events:
        events.boxplot(column="avg_depth_m", by="buzz_type", ax=axes[2, 1])
        axes[2, 1].set(title="Buzz depth", ylabel="Depth (m)")
        axes[2, 1].figure.suptitle("")
    else:
        _unavailable(axes[2, 1], "depth summaries")
    if not geometry.empty:
        residual = geometry.pivot(index="buzz_type", columns="geometry", values="pearson_residual")
        axes[2, 2].imshow(residual, cmap="coolwarm", vmin=-2, vmax=2)
        axes[2, 2].set(
            title=f"Geometry residuals (p={geometry_test['p_value']:.3g})",
            xticks=range(len(residual.columns)),
            xticklabels=residual.columns,
            yticks=range(len(residual.index)),
            yticklabels=residual.index,
        )
        axes[2, 2].tick_params(axis="x", rotation=35)
    else:
        _unavailable(axes[2, 2], "geometry residuals")
    if "straightness_before_20m" in events:
        events.boxplot(column="straightness_before_20m", by="buzz_type", ax=axes[2, 3])
        axes[2, 3].set(title="Straightness", ylabel="Straightness index")
        axes[2, 3].figure.suptitle("")
    else:
        _unavailable(axes[2, 3], "straightness summaries")
    robustness, _ = classifier_robustness(events)
    robustness.plot.bar(x="comparison", y="agreement", ax=axes[3, 0], legend=False)
    axes[3, 0].set(title="Classifier robustness", ylabel="Agreement")
    axes[3, 0].tick_params(axis="x", rotation=35)
    _unavailable(axes[3, 1], "full-record dive panel requires unreleased traces")
    _unavailable(axes[3, 2], "trajectory distributions are reproduced in the trajectory notebook")
    _unavailable(axes[3, 3], "regional map and vessel track are not released")
    available_panels = ["classifier", "pause", "markov", "geometry"]
    if roll_bins is not None:
        available_panels.append("roll")
    if energy is not None and {"A", "B"}.issubset(energy.columns):
        available_panels.append("energy")
    if "straightness_before_20m" in events:
        available_panels.append("straightness")
    return fig, {
        "available": available_panels,
        "unavailable": ["full_record", "regional_map", "exact_assembly"],
    }


def dswp_model_selection_figure(events):
    """Recreate the manuscript SI BIC panel and return robustness tables."""
    selection = gmm_model_selection(events)
    agreement, _ = classifier_robustness(events)
    primary = selection.loc[selection["feature_pair"].eq("ramp_up_vs_3d_speed")]
    optimum = int(primary.loc[primary["bic"].idxmin(), "n_components"])
    fig, ax = plt.subplots(figsize=(6.0, 4.8), constrained_layout=True)
    ax.axvspan(optimum - 0.18, optimum + 0.18, color=COLOR_A, alpha=0.10)
    ax.axvline(optimum, color=COLOR_A, linestyle="--", linewidth=1.2)
    ax.plot(
        primary["n_components"],
        primary["delta_bic_from_k1"],
        color="0.15",
        marker="o",
        markerfacecolor="white",
        markeredgecolor="0.15",
        linewidth=1.6,
    )
    ax.axhline(0, color="0.65", linewidth=0.8)
    ax.annotate(
        f"minimum at k={optimum}",
        xy=(optimum, primary.loc[primary["n_components"].eq(optimum), "delta_bic_from_k1"].iloc[0]),
        xytext=(3.2, primary["delta_bic_from_k1"].min() * 0.72),
        arrowprops={"arrowstyle": "->", "color": "0.35"},
        fontsize=9,
    )
    ax.set(
        xlabel="Number of GMM components, k",
        ylabel=r"$\Delta$BIC relative to k=1",
        xticks=primary["n_components"],
    )
    _paper_axis(ax)
    return fig, {"selection": selection, "agreement": agreement}


def comeback_classifier_comparison(events_path, index_path, manuscript_labels_path=None):
    """Plot the manuscript recurrence result and current-classifier sensitivity."""
    events = attach_labels(load_buzz_events(events_path, require_classifier=True), method="gmm")
    detected, deployments = detect_comeback_events(index_path)
    current = attach_comeback_context(events, detected)
    current_strata, current_summary = stratified_comeback_association(current)
    result = {"current": (current_strata, current_summary), "deployments": deployments}
    if manuscript_labels_path is not None:
        manuscript_labels = pd.read_csv(manuscript_labels_path)
        key = "event_id" if "event_id" in manuscript_labels and "event_id" in events else None
        label_column = (
            "manuscript_buzz_type" if "manuscript_buzz_type" in manuscript_labels else "buzz_type"
        )
        if key is not None and label_column in manuscript_labels:
            manuscript_events = events.drop(columns=["buzz_type"], errors="ignore").merge(
                manuscript_labels[[key, label_column]].rename(columns={label_column: "buzz_type"}),
                on=key,
                how="left",
            )
            manuscript_events = attach_comeback_context(manuscript_events, detected)
            result["manuscript"] = stratified_comeback_association(manuscript_events)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), constrained_layout=True)
    plot_comeback_forest(current_strata, current_summary, ax=axes[0])
    axes[0].set_title("Current-classifier sensitivity")
    if "manuscript" in result:
        manuscript_strata, manuscript_summary = result["manuscript"]
        plot_comeback_forest(manuscript_strata, manuscript_summary, ax=axes[1])
        axes[1].set_title("Manuscript labels")
    else:
        _unavailable(axes[1], "manuscript label table not supplied")
    return fig, result
