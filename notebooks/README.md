# Analysis notebooks

These notebooks explain the scientific analyses and call the same tested
functions used by the batch pipeline. They are not independent copies of the
implementation.

Run notebooks from anywhere inside the repository; each notebook locates the
repository root from `pyproject.toml`. Start with
`paper/00_manuscript_reproduction_status.ipynb`, which inventories the
paper-wide outputs and links each unresolved decision to the affected analysis.

The DSWP notebooks are:

1. `dswp/00_dataset_and_buzz_construction.ipynb` for the cohort, buzz phase
   construction, and plateau-threshold sensitivity;
2. `dswp/01_event_level_analysis.ipynb` for the primary event-level statistics;
3. `dswp/02_energy_model_derivation.ipynb` for the energetic-model derivation;
4. `dswp/03_manuscript_figure_components.ipynb` for main and supplementary
   tactic, kinematic, sequence, straightness, and pause panels; and
5. `dswp/04_comeback_reproduction_audit.ipynb` for the two deliberately
   separate spatial-recurrence label/definition results.

The trajectory notebooks are the registered numerical analysis in
`trajectory/01_reconstructed_trajectory_analysis.ipynb` and the expanded main
and supplementary figure derivations in
`trajectory/02_manuscript_trajectory_figures.ipynb`.

The validation notebooks are:

1. `validation/01_azores_open_data.ipynb` for source provenance and checksums;
2. `validation/02_ceti2024_derived_validation.ipynb` for the compact numerical
   CETI validation;
3. `validation/03_azores_derivation.ipynb` for Azores numerical outputs;
4. `validation/04_azores_manuscript_figures.ipynb` for Azores main and SI
   panels; and
5. `validation/05_ceti2024_manuscript_figures.ipynb` for the supported CETI SI
   panels and the explicit roll-time-course data gate.

All notebooks are stored without execution counts or outputs. This prevents
stale results and embedded local paths from entering the release. The
authoritative one-command run covers DSWP, trajectory, and CETI numerical
outputs. Azores remains an explicit checksummed local-input step:

```bash
python scripts/run_pipeline.py
```

Notebooks should be executed only after `python scripts/check_release_safety.py`
passes. Do not add private links, source identifiers, raw sensor arrays, or
downloaded Azores MATLAB files to a notebook.
