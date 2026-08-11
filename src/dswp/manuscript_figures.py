"""Thin plotting adapters for the released DSWP manuscript components.

The functions here deliberately compose the existing analysis modules.  They
return Matplotlib figures and metadata; they never write files or embed data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .classification import attach_labels, gmm_model_selection, classifier_robustness
from .figures import (
    plot_classifier, plot_comeback_forest, plot_individual_energy,
    plot_markov, plot_pause_categories, plot_pause_distribution,
    plot_roll_timecourse,
)
from .statistics import geometry_association, markov_leave_subset_out, compare_groups
from .comebacks import detect_comeback_events, attach_comeback_context, stratified_comeback_association
from .io import load_buzz_events


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
        proportions.pivot(index="buzz_type", columns="geometry", values="proportion").plot.bar(ax=axes[1, 2])
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
        proportions = events[events.buzz_type.isin(["A", "B"])].groupby(["individual_id", "buzz_type"]).size().unstack(fill_value=0)
        proportions.div(proportions.sum(axis=1), axis=0).plot.bar(stacked=True, ax=axes[2, 0], color=["#2A92D5", "#D56D2A"])
        axes[2, 0].set(title="Individual tactic proportions", ylabel="Proportion", xlabel="Individual")
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
        axes[2, 2].set(title=f"Geometry residuals (p={geometry_test['p_value']:.3g})", xticks=range(len(residual.columns)), xticklabels=residual.columns, yticks=range(len(residual.index)), yticklabels=residual.index)
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
    return fig, {"available": available_panels,
                 "unavailable": ["full_record", "regional_map", "exact_assembly"]}


def dswp_model_selection_figure(events):
    """Return the registered GMM BIC and classifier-robustness figures."""
    selection = gmm_model_selection(events)
    agreement, _ = classifier_robustness(events)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for name, group in selection.groupby("feature_pair", sort=False):
        axes[0].plot(group["n_components"], group["delta_bic_from_k1"], marker="o", label=name)
    axes[0].axhline(0, color=".5", lw=.7)
    axes[0].set(xlabel="Components k", ylabel="Delta BIC from k=1", title="GMM model selection")
    axes[0].legend(frameon=False, fontsize=8)
    agreement.plot.bar(x="comparison", y="agreement", ax=axes[1], legend=False)
    axes[1].set_ylabel("Agreement with registered GMM")
    axes[1].tick_params(axis="x", rotation=25)
    return fig, {"selection": selection, "agreement": agreement}


def comeback_alternatives(events_path, index_path, legacy_labels_path=None):
    """Compute legacy/current comeback alternatives without selecting one."""
    events = attach_labels(load_buzz_events(events_path, require_classifier=True), method="gmm")
    detected, deployments = detect_comeback_events(index_path)
    current = attach_comeback_context(events, detected)
    current_strata, current_summary = stratified_comeback_association(current)
    result = {"current": (current_strata, current_summary), "deployments": deployments}
    if legacy_labels_path is not None:
        legacy = pd.read_csv(legacy_labels_path)
        key = "event_id" if "event_id" in legacy and "event_id" in events else None
        legacy_column = "legacy_buzz_type" if "legacy_buzz_type" in legacy else "buzz_type"
        if key is not None and legacy_column in legacy:
            legacy_events = events.drop(columns=["buzz_type"], errors="ignore").merge(
                legacy[[key, legacy_column]].rename(columns={legacy_column: "buzz_type"}),
                on=key, how="left"
            )
            legacy_events = attach_comeback_context(legacy_events, detected)
            result["legacy"] = stratified_comeback_association(legacy_events)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), constrained_layout=True)
    plot_comeback_forest(current_strata, current_summary, ax=axes[0])
    axes[0].set_title("Registered current labels")
    if "legacy" in result:
        legacy_strata, legacy_summary = result["legacy"]
        plot_comeback_forest(legacy_strata, legacy_summary, ax=axes[1])
        axes[1].set_title("Archived manuscript labels")
    else:
        _unavailable(axes[1], "archived label table not supplied")
    return fig, result
