# Sperm whale foraging across scales

This repository accompanies the manuscript **“Sperm whale foraging combines
persistent search with flexible prey-capture tactics.”** It provides the code,
documented notebooks, derived inputs, numerical outputs, and figure components
used to reproduce the paper's analyses.

The central result is a multiscale description of foraging: persistent,
Lévy-like movement at the trajectory scale, within which whales alternate
between two acoustic–kinematic prey-capture tactics.

## At a glance

| Dataset | Role in the paper | Reproducible here |
| --- | --- | --- |
| DSWP, Dominica (2014–2018) | Discovery dataset | Buzz classification, sequence analysis, reconstructed-trajectory statistics, energetics, and associated numerical figure components |
| Azores | Prey-field validation | Final 28/28/two-tie analysis from checksummed data in the open Dryad record |
| Project CETI, Dominica (2024) | Independent validation | Buzz-level acoustic and kinematic validation |

The release begins from publication-safe derived data. It does not contain raw
audio, raw tag sensor streams, absolute GPS positions, field identifiers, or
the private identifier crosswalks. The DSWP trajectories are reconstructed
paths in local coordinates, not raw movement records.

## Reproduce the analyses

Python 3.11 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[analysis,notebooks,test]"
python scripts/check_release_safety.py
pytest
python scripts/run_pipeline.py
```

The pipeline writes numerical summaries to `results/` and figure components to
`figures/`. The Azores source files are not duplicated here; download and
verify them using the instructions in
[`data/azores/README.md`](data/azores/README.md), then run the validation step
described there.

## Repository guide

- `src/dswp/` — discovery-dataset classification, behavioural contrasts,
  sequence analysis, and energetics;
- `src/trajectory/` — reconstructed-trajectory and Lévy-like movement analyses;
- `src/validation/` — Azores and CETI 2024 validation workflows;
- `notebooks/` — readable walkthroughs that call the tested analysis code;
- `data/` — pseudonymized derived inputs and open-data retrieval metadata;
- `results/` — machine-readable numerical outputs;
- `figures/` — regenerated figure components; and
- `tests/` — numerical regression, schema, and release-safety checks.

For a result-by-result map, see
[`docs/result_map.md`](docs/result_map.md). For a fuller walkthrough, see
[`docs/reproduction_guide.md`](docs/reproduction_guide.md).

## Reproduction boundary

The public workflow reproduces the numerical analyses reported in the paper
from derived or openly archived inputs. Upstream signal processing from the raw
DTAG records is outside this repository. The final regional map is a
presentation asset because its location-bearing inputs are not released. The
CETI release is intentionally limited to the buzz-level validation; reviewed
reconstructed CETI paths and the legacy high-frequency roll trace are not part
of this version.

These scope choices do not change the manuscript's numerical results. The
technical audit trail, including the accepted exploratory comeback-analysis
provenance, is kept in [`docs/known_issues.md`](docs/known_issues.md) without
making it the entry point for readers.

## Version and citation

The frozen analysis underlying the current production manuscript is tagged
`production-code-2026-08-25`; the paired manuscript commit is `9e4ee80`.
Citation metadata are provided in [`CITATION.cff`](CITATION.cff). Add the
bioRxiv or journal DOI to that file once the manuscript record exists, and add
the repository archival DOI after the public archive is minted.

## Data use and licensing

The repository is currently private while the data owners confirm the final
derived-data release and the project selects software and data licences. Until
the corresponding licence files are added, the repository is available for
review but does not grant permission for public reuse. The proposed licence
split and the short approval checklist are in
[`LICENSING.md`](LICENSING.md) and
[`docs/release_readiness.md`](docs/release_readiness.md).

The Azores source dataset remains governed by its own CC0 terms at
<https://doi.org/10.5061/dryad.tqjq2bvwg>.
