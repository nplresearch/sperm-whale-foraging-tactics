# Azores source data

Retrieve the source data from the authoritative Dryad record, not from this
repository: https://doi.org/10.5061/dryad.tqjq2bvwg

Citation: Tonnesen, P. (2020). *The long-range echo scene of the sperm whale
biosonar* [Dataset]. Dryad. https://doi.org/10.5061/dryad.tqjq2bvwg

License: CC0 1.0 (Dryad data-publication terms).

`source_manifest.csv` pins the four required source files from Dryad version 1
by file ID, byte size, SHA-256 digest, and expected MATLAB variable. Download
those files into `local-data/azores/` (ignored by Git), then run:

```bash
python scripts/validate_azores_sources.py local-data/azores
```

This repository does not mirror the `.mat` files. The DOI remains the
authoritative source; the manifest prevents a silently changed or incorrectly
named local copy from entering the analysis.

The validation module reproduces the published main and supplementary Azores
statistics from these local, checksummed inputs and exports only safe derived
tables to `results/azores/`:

```bash
python scripts/run_azores_validation.py local-data/azores
```

The operative nearest-corner implementation has one overlapping event, so its
actual labels are 29 Type A, 28 Type B, and one unclassified buzz rather than a
balanced 29/29 split. The export includes a disjoint balanced assignment as a
sensitivity analysis. See `docs/known_issues.md` for the resulting manuscript
corrections and the corrected Markov bootstrap procedure.
