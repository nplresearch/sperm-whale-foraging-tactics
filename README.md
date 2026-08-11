# Multiscale sperm-whale foraging: reproducibility repository

This repository is a computational release candidate for the accompanying
paper on the multiscale organization of sperm-whale foraging. It contains the
tested analysis code, documented notebooks, and publication-safe derived data
currently available for release. It does not yet reproduce every panel: the
remaining analytical and data-steward gates are stated below and in
[docs/known_issues.md](docs/known_issues.md). The journal-submission decisions
and pass conditions are collected in
[docs/submission_reconciliation.md](docs/submission_reconciliation.md).

The repository is deliberately a **derived-data release**. It does not contain
raw DTAG audio, pressure, accelerometry, magnetometry, GPS tracks, field
records, or direct identifiers. The retained whale trajectories are
dead-reckoned reconstructions, and the retained buzz records are derived event
tables. See [DATA_POLICY.md](DATA_POLICY.md) for the precise boundary.

## What is reproduced

The analysis is organized around three datasets and two nested scales:

| Dataset | Reproduction status | Public input used here |
| --- | --- | --- |
| DSWP, Dominica (2014--2018) | Numerical primary analyses and component figures run; manuscript decisions listed in `known_issues.md` remain | Pseudonymized reconstructed trajectories and derived buzz-level measurements |
| Azores | Numerical prey-field, kinematic, geometry, pause, robustness, and sequence analyses run from checksummed open inputs; manuscript choices remain explicit | Retrieval instructions and checksum manifest for the openly archived source data |
| CETI, Dominica (2024) | Buzz-level validation runs; trajectory-dependent panels await steward-approved paths | Derived buzz information included; reviewed local-coordinate reconstructions are a documented release gate |

The code is split into:

- `src/dswp/`: primary buzz-level classification and statistical analyses;
- `src/trajectory/`: reconstructed-trajectory, Lévy-like movement, and
  robustness analyses;
- `src/validation/`: Azores and CETI 2024 validation workflows;
- `notebooks/`: readable, output-free walkthroughs of the paper analyses;
- `data/`: publication-safe inputs and dataset-specific documentation;
- `results/`: machine-readable numerical outputs;
- `figures/`: regenerated paper figures;
- `tests/`: numerical checks and release-safety tests.

## Quick start

Python 3.11 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[analysis,notebooks,test]"
python scripts/check_release_safety.py
pytest
```

The documented analyses can then be run in order:

```bash
python scripts/run_pipeline.py
```

The runner writes numerical summaries to `results/` and figures to `figures/`.
It never modifies the input data. Individual stages and expected outputs are
described in [docs/reproduction_guide.md](docs/reproduction_guide.md). The
paper-by-paper coverage and remaining gates are indexed in
[docs/result_map.md](docs/result_map.md).

## Data availability

No raw DSWP or CETI records are distributed here. The public derived-data
bundle is designed to reproduce the reported analyses without permitting the
original sensor streams to be reconstructed.

The Azores validation is based on an existing open dataset. Its authoritative
repository, citation, licence, checksum, and retrieval instructions are
documented under `data/azores/`; the open files are downloaded by the user and
are not silently mirrored here.

## Repository status

This is a release-candidate production repository and should not yet be pushed
to a public remote. Before public release:

1. approve the final derived-data tables and pseudonymization;
2. select a software and data licence with the data owners;
3. add the final paper citation and archival DOI;
4. resolve the documented Azores sample-count, echo-window, and bootstrap-CI
   manuscript choices;
5. decide whether to add the reviewed CETI reconstructed paths or explicitly
   scope the release to the buzz-level validation;
6. resolve the manuscript/code discrepancies in
   [docs/known_issues.md](docs/known_issues.md);
7. run the full pipeline in a clean environment; and
8. require the release-safety check to pass.

## Provenance

The initial extraction was made from internal analysis repository commit
`ecb9246711d7158fba62abbc769b9b00f30e5553`. The production code was then
refactored to consume explicit, documented derived tables rather than private
raw-data locations. See [docs/provenance.md](docs/provenance.md).

Important code--manuscript discrepancies found during extraction are recorded
in [docs/known_issues.md](docs/known_issues.md). The trajectory-driven energy
model is now aligned between the code, Methods, and SI. Remaining issues
include a comeback paragraph that combines a legacy classifier with recurrence
parameters different from those stated in the SI, plus Azores wording and
bootstrap choices that differ from the operative analysis. The release retains
both result-producing implementations, pins the open Azores sources, and makes
every unresolved decision explicit.

The repository also includes the published steady-drag formulation of Aoki et
al. (2012), applied to the same observed buzz intervals as additional evidence
for the direction and approximate scale of the Type-B/Type-A contrast. The
primary energetic calculation remains the trajectory-driven model described
in the manuscript and implemented in `src/dswp/energetics.py`.
