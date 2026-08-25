# Multiscale sperm-whale foraging: reproducibility repository

This repository is the production analysis repository for the accompanying
paper on the multiscale organization of sperm-whale foraging. It contains the
tested analysis code, documented notebooks, and derived-data bundle used for
the frozen manuscript results. Its scope is deliberately narrower than an
upstream reconstruction from raw tags: protected raw sensor records and some
presentation-only or location-bearing panels are outside the public
reproduction boundary. The exact scope and release obligations are recorded in
[docs/known_issues.md](docs/known_issues.md) and
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
| DSWP, Dominica (2014--2018) | Primary numerical analyses and component figures are frozen; the manuscript's exploratory comeback result is retained as an explicitly documented legacy-production exception | Pseudonymized reconstructed trajectories and derived buzz-level measurements |
| Azores | Final 28/28/two-tie prey-field, kinematic, geometry, pause, robustness, and duplicate-preserving sequence analyses run from checksummed open inputs | Retrieval instructions and checksum manifest for the openly archived source data |
| CETI, Dominica (2024) | Buzz-level validation runs within the released scope; the legacy roll time course and any additional trajectory-dependent panels remain outside the deterministic public reproduction boundary | Derived buzz information included; reviewed local-coordinate reconstructions remain a separate data-governance decision |

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

The analysis code, numerical outputs, and manuscript-facing Azores validation
are frozen for paper production. The full test suite and release-safety audit
pass in the maintained environment. The comeback calculation is intentionally
retained exactly as used by the manuscript; its mixed legacy provenance is
documented rather than silently rewritten.
The exact frozen scope and accepted exception are summarized in
[docs/production_freeze.md](docs/production_freeze.md).

This technical freeze is not, by itself, authorization to publish the derived
data bundle. A public archival release still requires:

1. data-steward approval of the final derived tables and pseudonymization;
2. software and data licences selected with the data owners;
3. the final paper citation and archival DOI;
4. an explicit decision on whether CETI reconstructed paths enter the release;
5. a final manuscript--artifact checksum crosswalk; and
6. a clean-environment rerun of the pipeline and release-safety audit.

## Provenance

The initial extraction was made from internal analysis repository commit
`ecb9246711d7158fba62abbc769b9b00f30e5553`. The production code was then
refactored to consume explicit, documented derived tables rather than private
raw-data locations. See [docs/provenance.md](docs/provenance.md).

Important code--manuscript discrepancies found during extraction are recorded
in [docs/known_issues.md](docs/known_issues.md). The trajectory-driven energy
model, Azores validation, classifier provenance, sequence resampling, terminal
event denominator, and trajectory-scale analyses are aligned between code and
manuscript. The comeback paragraph remains a documented production exception:
the release retains both the manuscript-producing legacy calculation and the
registered-current alternative, without presenting them as interchangeable.

The repository also includes the published steady-drag formulation of Aoki et
al. (2012), applied to the same observed buzz intervals as additional evidence
for the direction and approximate scale of the Type-B/Type-A contrast. The
primary energetic calculation remains the trajectory-driven model described
in the manuscript and implemented in `src/dswp/energetics.py`.
