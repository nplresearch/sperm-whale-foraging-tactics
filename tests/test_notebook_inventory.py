import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_NOTEBOOKS = (
    "notebooks/paper/00_manuscript_reproduction_status.ipynb",
    "notebooks/dswp/00_dataset_and_buzz_construction.ipynb",
    "notebooks/dswp/01_event_level_analysis.ipynb",
    "notebooks/dswp/02_energy_model_derivation.ipynb",
    "notebooks/dswp/03_manuscript_figure_components.ipynb",
    "notebooks/dswp/04_comeback_reproduction_audit.ipynb",
    "notebooks/trajectory/01_reconstructed_trajectory_analysis.ipynb",
    "notebooks/trajectory/02_manuscript_trajectory_figures.ipynb",
    "notebooks/validation/01_azores_open_data.ipynb",
    "notebooks/validation/02_ceti2024_derived_validation.ipynb",
    "notebooks/validation/03_azores_derivation.ipynb",
    "notebooks/validation/04_azores_manuscript_figures.ipynb",
    "notebooks/validation/05_ceti2024_manuscript_figures.ipynb",
)


def test_manuscript_notebook_inventory_is_complete_and_clean():
    for relative in EXPECTED_NOTEBOOKS:
        path = ROOT / relative
        assert path.is_file(), relative
        notebook = json.loads(path.read_text())
        assert notebook["nbformat"] == 4
        ids = [cell.get("id") for cell in notebook["cells"]]
        assert all(ids), f"{relative}: missing cell id"
        assert len(ids) == len(set(ids)), f"{relative}: duplicate cell id"
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                assert cell.get("execution_count") is None
                assert cell.get("outputs", []) == []


def test_decision_sensitive_notebooks_name_known_issue_touchpoints():
    sensitive = (
        "notebooks/paper/00_manuscript_reproduction_status.ipynb",
        "notebooks/dswp/00_dataset_and_buzz_construction.ipynb",
        "notebooks/dswp/03_manuscript_figure_components.ipynb",
        "notebooks/dswp/04_comeback_reproduction_audit.ipynb",
        "notebooks/trajectory/02_manuscript_trajectory_figures.ipynb",
        "notebooks/validation/04_azores_manuscript_figures.ipynb",
        "notebooks/validation/05_ceti2024_manuscript_figures.ipynb",
    )
    for relative in sensitive:
        assert "Known issue touchpoint" in (ROOT / relative).read_text(), relative
