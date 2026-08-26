"""Numerical regression tests for the paper's registered aggregate results."""

from pathlib import Path

import numpy as np
import pandas as pd

from dswp.aoki import (
    event_aoki_energy_from_trajectories,
    paired_individual_aoki,
)
from dswp.classification import (
    attach_labels,
    classifier_robustness,
    classifier_speed_sensitivity,
    classify_gmm,
    gmm_model_selection,
)
from dswp.comebacks import (
    attach_comeback_context,
    detect_comeback_events,
    stratified_comeback_association,
)
from dswp.energetics import (
    event_energy_from_trajectories,
    paired_individual_energy,
)
from dswp.io import load_buzz_events
from trajectory.analysis import analyze_release
from validation.ceti2024 import classify_corner

ROOT = Path(__file__).resolve().parents[1]


def test_dswp_classifier_counts():
    events = load_buzz_events(ROOT / "data/dswp/buzz_events.csv")
    assert classify_gmm(events).value_counts().to_dict() == {
        "A": 1346,
        "?": 1198,
        "B": 1142,
    }


def test_classifier_speed_sensitivity():
    events = load_buzz_events(ROOT / "data/dswp/buzz_events.csv")
    result = classifier_speed_sensitivity(events)
    assert result["primary_counts"] == {"A": 1346, "B": 1142, "?": 1198}
    assert result["pitch_adaptive_counts"] == {
        "A": 1350,
        "B": 1176,
        "?": 1160,
    }
    assert result["shared_confident"] == 2417
    assert result["shared_confident_A"] == 1306
    assert result["shared_confident_B"] == 1111
    assert result["shared_confident_A_to_B_or_B_to_A"] == 0
    assert result["primary_confident_to_unassigned"] == 71
    assert result["primary_unassigned_to_pitch_adaptive_confident"] == 109


def test_gmm_model_selection_minima():
    events = load_buzz_events(ROOT / "data/dswp/buzz_events.csv")
    selection = gmm_model_selection(events)
    optimum = (
        selection.loc[
            selection.groupby("feature_pair")["bic"].idxmin(),
            ["feature_pair", "n_components"],
        ]
        .set_index("feature_pair")["n_components"]
        .to_dict()
    )
    assert optimum == {
        "ramp_up_vs_3d_speed": 2,
        "max_click_rate_vs_roll": 2,
        "total_duration_vs_median_click_rate": 3,
    }


def test_classifier_robustness_matches_si():
    events = load_buzz_events(ROOT / "data/dswp/buzz_events.csv")
    summary, _ = classifier_robustness(events)
    values = summary.set_index("comparison")
    assert set(values["n"]) == {3488}
    assert np.isclose(values.loc["gmm_vertical_speed", "agreement"], 0.952695)
    assert np.isclose(values.loc["gmm_vertical_speed", "cohen_kappa"], 0.905034)
    assert np.isclose(values.loc["corner_3d_speed", "agreement"], 0.977924)
    assert np.isclose(values.loc["corner_3d_speed", "cohen_kappa"], 0.955774)
    assert np.isclose(values.loc["corner_vertical_speed", "agreement"], 0.944954)
    assert np.isclose(values.loc["corner_vertical_speed", "cohen_kappa"], 0.889839)


def test_trajectory_aggregates():
    _, summary, _ = analyze_release(ROOT / "data/dswp/trajectory_index.csv")
    assert summary["n_dives"] == 209
    assert summary["n_individuals"] == 20
    assert np.isclose(summary["mu_dive_median"], 2.354319927821409)
    assert np.isclose(summary["mu_individual_median"], 2.363747850635203)
    assert np.isclose(summary["mu_pooled"], 2.15463519416354)
    assert np.isclose(summary["alpha_dive_median"], 1.909046391036953)
    assert np.isclose(summary["alpha_short_le_1min_median"], 1.9786544101226304)
    assert np.isclose(summary["alpha_mid_1_5min_median"], 1.7453575687539202)
    assert np.isclose(summary["alpha_long_5_15min_median"], 1.5223574023174218)


def test_reported_energy_means():
    events = load_buzz_events(ROOT / "data/dswp/buzz_events.csv")
    events["buzz_type"] = classify_gmm(events)
    energy = event_energy_from_trajectories(events, ROOT / "data/dswp/trajectory_index.csv")
    paired = paired_individual_energy(energy)
    means_mj = paired[["A", "B"]].mean() / 1e6
    assert len(paired) == 20
    assert np.isclose(means_mj["A"], 1.2754630221287353)
    assert np.isclose(means_mj["B"], 9.069494397522456)

    efficiency = 0.25 * 0.75
    energy["E_metabolic_drag_J"] = energy["drag_work_J"] / efficiency
    energy["E_metabolic_positive_acceleration_J"] = (
        energy["positive_acceleration_work_J"] / efficiency
    )
    components_mj = (
        energy.loc[energy["buzz_type"].isin(["A", "B"])]
        .groupby(["individual_id", "buzz_type"])[
            [
                "E_metabolic_drag_J",
                "E_metabolic_positive_acceleration_J",
                "E_metabolic_rest_J",
            ]
        ]
        .mean()
        .groupby("buzz_type")
        .mean()
        / 1e6
    )
    assert np.allclose(
        components_mj.loc["A"],
        [0.009821, 1.228810, 0.036831],
        atol=5e-7,
    )
    assert np.allclose(
        components_mj.loc["B"],
        [0.075813, 8.924000, 0.069681],
        atol=5e-7,
    )


def test_aoki_directional_comparison():
    events = load_buzz_events(ROOT / "data/dswp/buzz_events.csv")
    events["buzz_type"] = classify_gmm(events)
    energy = event_aoki_energy_from_trajectories(events, ROOT / "data/dswp/trajectory_index.csv")
    paired = paired_individual_aoki(energy)
    means_mj = paired[["A", "B"]].mean() / 1e6
    assert len(paired) == 20
    assert np.isclose(means_mj["A"], 0.01307228084262739)
    assert np.isclose(means_mj["B"], 0.11124034997877447)
    assert np.isclose(means_mj["B"] / means_mj["A"], 8.509635871349314)
    assert (paired["B"] > paired["A"]).all()


def test_registered_comeback_associations():
    events = attach_labels(load_buzz_events(ROOT / "data/dswp/buzz_events.csv"))
    recurrence, deployment_summary = detect_comeback_events(
        ROOT / "data/dswp/comeback_trajectory_index.csv"
    )
    context = attach_comeback_context(events, recurrence).merge(
        pd.read_csv(ROOT / "data/dswp/comeback_manuscript_labels.csv"),
        on="event_id",
        validate="one_to_one",
    )

    _, manuscript = stratified_comeback_association(context, label_col="manuscript_buzz_type")
    assert manuscript["n_deployments"] == 18
    assert manuscript["n_buzzes"] == 1691
    assert np.isclose(manuscript["pooled_odds_ratio"], 1.1111190915)
    assert np.isclose(manuscript["p_value"], 0.5595676636)

    _, current = stratified_comeback_association(context)
    assert current["n_deployments"] == 18
    assert current["n_buzzes"] == 1660
    assert np.isclose(current["pooled_odds_ratio"], 1.1507709578)
    assert len(recurrence) == 144
    assert len(deployment_summary) == 30


def test_ceti2024_corner_counts():
    events = pd.read_csv(ROOT / "data/ceti2024/buzz_features.csv")
    assert classify_corner(events).value_counts().to_dict() == {
        "A": 115,
        "unclassified": 115,
        "B": 106,
    }
