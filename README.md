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

The repository begins from publication-safe derived data. It does not contain raw
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
CETI release is intentionally limited to the buzz-level validation;
reconstructed CETI paths and the high-frequency roll time course are not part
of this version.

## Version and citation

Version 1.0.0 accompanies the submitted manuscript and the bioRxiv preprint:

> Zaffina, L., Monti, C., Poetto, S., et al. (2026). *Sperm whale foraging
> combines persistent search with flexible prey-capture tactics*. bioRxiv.
> <https://doi.org/10.64898/2026.07.29.741536>

Machine-readable citation metadata are provided in
[`CITATION.cff`](CITATION.cff). The paired manuscript source is commit
`435c3d0`.

## Data use and licensing

Analysis code is released under the MIT License. Repository-authored derived
tables and local-coordinate reconstructed paths are released under CC BY 4.0.
See [`LICENSING.md`](LICENSING.md), [`LICENSE`](LICENSE), and
[`LICENSE-DATA`](LICENSE-DATA) for the exact scope.

The Azores source dataset remains governed by its own CC0 terms at
<https://doi.org/10.5061/dryad.tqjq2bvwg>.
