import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import pandas as pd
import pytest

from dswp.classification import attach_labels
from dswp.manuscript_figures import (
    comeback_classifier_comparison,
    dswp_component_figure,
    dswp_model_selection_figure,
    dswp_sequence_manuscript_figure,
    dswp_tactics_manuscript_figure,
)
from validation.azores import run_azores_validation
from validation.manuscript_figures import azores_manuscript_figure, ceti2024_manuscript_figure

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = [
    ROOT / "notebooks/dswp/03_manuscript_figure_components.ipynb",
    ROOT / "notebooks/dswp/04_comeback_analysis.ipynb",
    ROOT / "notebooks/validation/04_azores_manuscript_figures.ipynb",
    ROOT / "notebooks/validation/05_ceti2024_manuscript_figures.ipynb",
]


def test_notebooks_are_output_free_and_have_stable_ids():
    for path in NOTEBOOKS:
        notebook = json.loads(path.read_text())
        ids = [cell["id"] for cell in notebook["cells"]]
        assert len(ids) == len(set(ids))
        assert all(
            cell.get("execution_count") is None
            for cell in notebook["cells"]
            if cell["cell_type"] == "code"
        )
        assert all(
            not cell.get("outputs") for cell in notebook["cells"] if cell["cell_type"] == "code"
        )
        assert any(
            "Production note:" in "".join(cell.get("source", [])) for cell in notebook["cells"]
        )


def test_dswp_manuscript_adapters_return_figures():
    events = attach_labels(pd.read_csv(ROOT / "data/dswp/buzz_events.csv"))
    roll = pd.read_csv(ROOT / "data/dswp/roll_speed_bins.csv")
    figure, availability = dswp_component_figure(events, roll_bins=roll)
    assert figure.axes
    assert "full_record" in availability["unavailable"]
    model_figure, tables = dswp_model_selection_figure(events)
    assert model_figure.axes and not tables["selection"].empty
    figure.clf()
    model_figure.clf()


def test_dswp_manuscript_layouts_reproduce_registered_panels():
    events = attach_labels(pd.read_csv(ROOT / "data/dswp/buzz_events.csv"))
    roll = pd.read_csv(ROOT / "data/dswp/roll_speed_bins.csv")
    energy = pd.read_csv(ROOT / "results/dswp/buzz_energy.csv")
    straightness = pd.read_csv(ROOT / "results/dswp/buzz_straightness.csv")
    transitions = pd.read_csv(ROOT / "results/dswp/buzz_markov_transitions.csv")

    tactics, tactics_tables = dswp_tactics_manuscript_figure(
        events,
        roll_bins=roll,
        energy_events=energy,
        trajectory_index_path=ROOT / "data/dswp/trajectory_index.csv",
    )
    sequence, sequence_tables = dswp_sequence_manuscript_figure(
        events,
        straightness=straightness,
        transitions=transitions,
    )

    assert tactics_tables["trajectory"] == {
        "trajectory_id": "T127",
        "centre_buzz_order": 15,
        "duration_s": 100.0,
    }
    assert tactics_tables["individual_counts"].shape == (20, 2)
    assert tactics_tables["geometry_test"]["n"] == 2488
    assert sequence_tables["straightness_before"]["n_A"] == 1346
    assert sequence_tables["straightness_after"]["p_value"] == pytest.approx(
        0.3998199,
        rel=1e-5,
    )
    assert len(tactics.axes) >= 7
    assert len(sequence.axes) >= 5
    tactics.clf()
    sequence.clf()


def test_comeback_figure_keeps_manuscript_and_current_classifier_results():
    figure, result = comeback_classifier_comparison(
        ROOT / "data/dswp/buzz_events.csv",
        ROOT / "data/dswp/comeback_trajectory_index.csv",
        ROOT / "data/dswp/comeback_manuscript_labels.csv",
    )
    assert "current" in result and "manuscript" in result
    figure.clf()


def test_azores_figure_adapter_preserves_two_splits(tmp_path):
    source = ROOT.parent / "repo/Clean_notebooks_figures/Azores_code"
    if not source.exists():
        import pytest

        pytest.skip("production Azores source files are not available")
    result = run_azores_validation(source, tmp_path / "azores", n_boot=4)
    assert result["summary"]["operative_counts"].get("A") == 28
    assert result["summary"]["operative_counts"].get("B") == 28
    assert result["summary"]["operative_counts"].get("unclassified") == 2
    assert result["summary"]["balanced_counts"].get("A") == 29
    assert result["summary"]["balanced_counts"].get("B") == 29
    figure = azores_manuscript_figure(result)
    assert figure.axes
    figure.clf()


def test_ceti_figure_adapter_marks_roll_gate():
    data = pd.read_csv(ROOT / "data/ceti2024/buzz_features.csv")
    figure, tables = ceti2024_manuscript_figure(data)
    assert "per_bin_roll_time_course" in tables["unavailable"]
    assert not tables["sequence_statistics"].empty
    assert tables["geometry_proportions"].notna().any().any()
    assert pd.notna(tables["fisher_p"])
    figure.clf()
