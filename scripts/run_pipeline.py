#!/usr/bin/env python3
"""Run the complete publication-safe analysis from the repository root."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from check_release_safety import audit  # noqa: E402
from dswp.aoki import (  # noqa: E402
    event_aoki_energy_from_trajectories,
    paired_individual_aoki,
)
from dswp.classification import (  # noqa: E402
    classifier_robustness,
    gmm_model_selection,
)
from dswp.comebacks import (  # noqa: E402
    attach_comeback_context,
    detect_comeback_events,
    stratified_comeback_association,
)
from dswp.energetics import (  # noqa: E402
    event_energy_from_trajectories,
    paired_individual_energy,
)
from dswp.figures import (  # noqa: E402
    plot_classifier,
    plot_comeback_depths,
    plot_comeback_forest,
    plot_comeback_ratios,
    plot_gmm_model_selection,
    plot_individual_energy,
    plot_markov,
    plot_pause_categories,
    plot_pause_distribution,
    plot_reconstruction_error_summary,
    plot_roll_timecourse,
)
from dswp.pauses import pause_association, pause_category_table  # noqa: E402
from dswp.pipeline import run as run_dswp  # noqa: E402
from dswp.statistics import (  # noqa: E402
    compare_groups,
    depth_mixed_model,
    geometry_association,
    pause_distribution_tests,
    roll_speed_bin_tests,
)
from dswp.trajectory_features import buzz_straightness  # noqa: E402
from trajectory.analysis import analyze_release  # noqa: E402
from trajectory.figures import plot_mu_distribution, plot_timescale_msd  # noqa: E402
from validation.ceti2024 import run_ceti2024_validation  # noqa: E402


def save_figure(ax, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ax.figure.tight_layout()
    ax.figure.savefig(path.with_suffix(".pdf"))
    ax.figure.savefig(path.with_suffix(".png"), dpi=250)
    plt.close(ax.figure)


def main() -> int:
    errors = audit(ROOT)
    if errors:
        raise RuntimeError(
            "Release-safety check failed before analysis:\n- " + "\n- ".join(errors)
        )

    data = ROOT / "data"
    results = ROOT / "results"
    figures = ROOT / "figures"
    dswp_results = results / "dswp"
    trajectory_results = results / "trajectory"
    dswp_figures = figures / "dswp"
    trajectory_figures = figures / "trajectory"
    for directory in (
        dswp_results,
        trajectory_results,
        dswp_figures,
        trajectory_figures,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    # Primary event analysis.
    events = run_dswp(
        data / "dswp" / "buzz_events.csv",
        dswp_results,
        n_boot=2000,
    )
    transitions = pd.read_csv(dswp_results / "buzz_markov_transitions.csv")
    model_selection = gmm_model_selection(events)
    model_selection.to_csv(
        dswp_results / "gmm_model_selection.csv", index=False
    )
    robustness, robustness_matrix = classifier_robustness(events)
    robustness.to_csv(
        dswp_results / "classifier_robustness.csv", index=False
    )
    robustness_matrix.to_csv(
        dswp_results / "classifier_robustness_confusion.csv", index=False
    )
    reconstruction_errors = pd.read_csv(
        data / "dswp" / "reconstruction_error_summary.csv"
    )
    reconstruction_method_summary = (
        reconstruction_errors.groupby("reconstruction_method")
        .agg(
            n_deployments=("deployment_id", "nunique"),
            n_reference_positions=("n_reference_positions", "sum"),
            mean_of_deployment_means_m=("mean_error_m", "mean"),
            median_of_deployment_means_m=("mean_error_m", "median"),
            mean_of_deployment_medians_m=("median_error_m", "mean"),
            median_of_deployment_medians_m=("median_error_m", "median"),
        )
        .reset_index()
    )
    wins = (
        reconstruction_errors.loc[
            reconstruction_errors.groupby("deployment_id")["mean_error_m"]
            .idxmin()
        ]["reconstruction_method"]
        .value_counts()
    )
    reconstruction_method_summary["n_lowest_mean_error"] = (
        reconstruction_method_summary["reconstruction_method"]
        .map(wins)
        .fillna(0)
        .astype(int)
    )
    reconstruction_method_summary.to_csv(
        dswp_results / "reconstruction_method_summary.csv", index=False
    )

    pauses = pause_category_table(events)
    pauses.to_csv(dswp_results / "pause_categories.csv", index=False)
    pause_test = pause_association(events)
    (dswp_results / "pause_association.json").write_text(
        json.dumps(pause_test, indent=2) + "\n"
    )
    pause_distribution = pause_distribution_tests(events)
    (dswp_results / "pause_distribution_tests.json").write_text(
        json.dumps(pause_distribution, indent=2) + "\n"
    )

    depth_model = depth_mixed_model(events)
    (dswp_results / "depth_mixed_model.json").write_text(
        json.dumps(depth_model, indent=2) + "\n"
    )

    geometry, geometry_test = geometry_association(events)
    geometry.to_csv(dswp_results / "vertical_geometry.csv", index=False)
    (dswp_results / "vertical_geometry_test.json").write_text(
        json.dumps(geometry_test, indent=2) + "\n"
    )

    straightness = buzz_straightness(
        events, data / "dswp" / "trajectory_index.csv"
    )
    straightness.to_csv(dswp_results / "buzz_straightness.csv", index=False)
    straightness_with_labels = events[["event_id", "buzz_type"]].merge(
        straightness, on="event_id", validate="one_to_one"
    )
    straightness_tests = []
    for phase in ("before", "after"):
        for window in (20, 30, 40):
            straightness_tests.append(
                compare_groups(
                    straightness_with_labels,
                    f"straightness_{phase}_{window}m",
                )
            )
    pd.DataFrame(straightness_tests).to_csv(
        dswp_results / "straightness_group_contrasts.csv", index=False
    )

    energy = event_energy_from_trajectories(
        events, data / "dswp" / "trajectory_index.csv"
    )
    energy.to_csv(dswp_results / "buzz_energy.csv", index=False)
    paired_energy = paired_individual_energy(
        energy, individual_col="individual_id"
    )
    paired_energy.to_csv(dswp_results / "individual_energy.csv", index=False)

    # Steady-drag sensitivity using the Aoki et al. (2012) locomotor-cost
    # equation over the same observed speed series and full-buzz intervals.
    aoki_energy = event_aoki_energy_from_trajectories(
        events, data / "dswp" / "trajectory_index.csv"
    )
    aoki_energy.to_csv(
        dswp_results / "aoki_event_energy.csv", index=False
    )
    paired_aoki = paired_individual_aoki(aoki_energy)
    paired_aoki.to_csv(
        dswp_results / "aoki_individual_energy.csv", index=False
    )

    # Spatial recurrence. Two label versions are reported deliberately:
    # ``legacy`` reproduces the currently archived manuscript forest plot,
    # while ``current`` applies the registered classifier used elsewhere.
    comeback_events, comeback_deployments = detect_comeback_events(
        data / "dswp" / "comeback_trajectory_index.csv"
    )
    comeback_events.to_csv(dswp_results / "comeback_events.csv", index=False)
    comeback_deployments.to_csv(
        dswp_results / "comeback_deployments.csv", index=False
    )
    comeback_context = attach_comeback_context(events, comeback_events).merge(
        pd.read_csv(data / "dswp" / "comeback_legacy_labels.csv"),
        on="event_id",
        validate="one_to_one",
    )
    comeback_context[
        ["event_id", "deep_comeback_context"]
    ].to_csv(dswp_results / "comeback_buzz_context.csv", index=False)
    comeback_summaries = {}
    comeback_strata = {}
    for version, label_column in (
        ("legacy_manuscript", "legacy_buzz_type"),
        ("current_classifier", "buzz_type"),
    ):
        strata, association = stratified_comeback_association(
            comeback_context, label_col=label_column
        )
        strata.to_csv(
            dswp_results / f"comeback_strata_{version}.csv", index=False
        )
        (dswp_results / f"comeback_association_{version}.json").write_text(
            json.dumps(association, indent=2) + "\n"
        )
        comeback_strata[version] = strata
        comeback_summaries[version] = association

    roll_bins = pd.read_csv(data / "dswp" / "roll_speed_bins.csv")
    roll_tests = roll_speed_bin_tests(events, roll_bins)
    roll_tests.to_csv(
        dswp_results / "roll_speed_bin_tests.csv", index=False
    )
    save_figure(plot_classifier(events), dswp_figures / "classifier")
    reconstruction_axes = plot_reconstruction_error_summary(
        reconstruction_errors
    )
    save_figure(
        reconstruction_axes[0],
        dswp_figures / "reconstruction_error_summary",
    )
    model_selection_axes = plot_gmm_model_selection(model_selection)
    save_figure(
        model_selection_axes[0],
        dswp_figures / "gmm_model_selection",
    )
    save_figure(
        plot_roll_timecourse(events, roll_bins),
        dswp_figures / "roll_speed_timecourse",
    )
    save_figure(plot_markov(transitions), dswp_figures / "markov_transitions")
    save_figure(
        plot_pause_distribution(events), dswp_figures / "pause_distribution"
    )
    save_figure(
        plot_pause_categories(events), dswp_figures / "pause_categories"
    )
    save_figure(
        plot_individual_energy(paired_energy),
        dswp_figures / "individual_energy",
    )
    save_figure(
        plot_comeback_forest(
            comeback_strata["legacy_manuscript"],
            comeback_summaries["legacy_manuscript"],
        ),
        dswp_figures / "comeback_forest_legacy_manuscript",
    )
    save_figure(
        plot_comeback_forest(
            comeback_strata["current_classifier"],
            comeback_summaries["current_classifier"],
        ),
        dswp_figures / "comeback_forest_current_classifier",
    )
    save_figure(
        plot_comeback_depths(comeback_events),
        dswp_figures / "comeback_event_depths",
    )
    save_figure(
        plot_comeback_ratios(comeback_deployments),
        dswp_figures / "comeback_ratios",
    )

    # Trajectory-scale search statistics.
    per_dive, trajectory_summary, timescale = analyze_release(
        data / "dswp" / "trajectory_index.csv"
    )
    per_dive.to_csv(trajectory_results / "per_dive_levy_msd.csv", index=False)
    timescale.to_csv(trajectory_results / "timescale_msd.csv", index=False)
    (trajectory_results / "population_summary.json").write_text(
        json.dumps(trajectory_summary, indent=2) + "\n"
    )
    save_figure(
        plot_mu_distribution(per_dive),
        trajectory_figures / "step_exponent_distribution",
    )
    save_figure(
        plot_timescale_msd(timescale),
        trajectory_figures / "timescale_msd",
    )

    # Independent preliminary CETI 2024 validation. Azores is intentionally a
    # documented external-data retrieval step rather than an implicit download.
    ceti_results = run_ceti2024_validation(
        data / "ceti2024" / "buzz_features.csv",
        results / "ceti2024",
    )

    energy_means_mj = (
        paired_energy[["A", "B"]].mean().div(1e6).to_dict()
    )
    summary = {
        "dswp": {
            "n_buzzes": int(len(events)),
            "buzz_type_counts": {
                str(key): int(value)
                for key, value in events["buzz_type"].value_counts().items()
            },
            "n_energy_individuals": int(len(paired_energy)),
            "mean_individual_energy_MJ": energy_means_mj,
            "mean_individual_aoki_drag_energy_MJ": (
                paired_aoki[["A", "B"]].mean().div(1e6).to_dict()
            ),
            "depth_mixed_model": depth_model,
            "comeback_association": comeback_summaries,
        },
        "trajectory": trajectory_summary,
        "ceti2024": {
            "n_buzzes": int(len(ceti_results["labels"])),
            "buzz_type_counts": {
                str(key): int(value)
                for key, value in ceti_results["labels"]["buzz_type"]
                .value_counts()
                .items()
            },
        },
        "azores": {
            "status": "external open-data retrieval; see data/azores/README.md"
        },
    }
    (results / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )

    final_errors = audit(ROOT)
    if final_errors:
        raise RuntimeError(
            "Release-safety check failed after analysis:\n- "
            + "\n- ".join(final_errors)
        )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
