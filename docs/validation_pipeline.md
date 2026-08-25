# Validation data and analyses

This repository separates two validation sources with different access models.
It never contains raw CETI tag recordings or raw sensor streams.

## Azores: authoritative open source

The Azores re-analysis uses the authoritative Dryad deposition, **Tonnesen
(2020), _The long-range echo scene of the sperm whale biosonar_**, DOI
[10.5061/dryad.tqjq2bvwg](https://doi.org/10.5061/dryad.tqjq2bvwg).
The record contains `sw17_196a_buzz.mat`, `sw17_196a_data.mat`,
`sw17_196a_dive.mat`, and `sw17_196a_echo.mat`, as well as the original MATLAB
analysis scripts.  These are the source files used for the Azores prey-echo and
buzz analyses; do not substitute a local copy of the legacy project data.

License: **CC0 1.0**, under Dryad's data-publication terms.  Cite the dataset
in every reuse: *Tonnesen, P. (2020). The long-range echo scene of the sperm
whale biosonar [Dataset]. Dryad. https://doi.org/10.5061/dryad.tqjq2bvwg*.

The exact version-1 filenames, Dryad file IDs, sizes, SHA-256 digests and
MATLAB variable names are pinned in `data/azores/source_manifest.csv`.
Download the files to ignored `local-data/azores/`, then run
`scripts/validate_azores_sources.py local-data/azores`. The validator checks
all bytes before the narrow MATLAB struct reader exposes the `buzz`, `whale`,
`diving`, and `echo` tables. The `fetch_azores_file` helper can accept a current
file URL, but download URLs are deliberately not treated as stable
dependencies: the DOI and checksum manifest are authoritative.

`validation.azores` validates those sources and implements the operative
daytime-subset prey-depth, echo-count, nearest-range, pre-buzz speed, pause,
geometry, robustness, and Markov analyses. It writes only derived event and
aggregate products. The manuscript/code choices exposed by this reproduction
are recorded in `docs/known_issues.md`; loading the files alone is not treated
as successful reproduction.

## CETI 2024: reviewed derived data only

The CETI validation data are a minimal per-buzz feature table.  It may include
only the columns enumerated in `src/validation/ceti2024.py:FEATURE_COLUMNS`:
opaque unit/dive tokens, within-dive sequence order, buzz timing summaries,
click-rate summaries, depth/kinematic summaries, and derived sequence-context
metrics.  The table is sufficient for:

- rank-space extreme-corner A/B clustering;
- A/B kinematic and depth comparisons (Mann--Whitney U and Cliff's delta);
- pause/straightness/re-engagement comparisons when those derived columns are
  present; and
- Start--A/B--End transitions across anonymous dives.

It is not sufficient to recreate raw-sensor time courses.  In particular, the
legacy roll-speed trace around a buzz requires raw roll at 25 Hz and is not a
publication-safe result to regenerate from the minimal table.  The retained
kinematic summaries reproduce the corresponding per-buzz comparisons.

### Explicit exclusions

Do not add audio/waveforms, pressure, accelerometer/gyroscope/magnetometer
streams, source MATLAB structs, GPS/locations, original deployment or animal
identifiers, demographics, raw recording timestamps, private paths, or any
unreviewed columns. Version 0.1 is intentionally scoped to the buzz-level
validation and does not distribute CETI reconstructed trajectories. Any later
trajectory release would be a separately reviewed data version.

### Creating the reviewed table

Only a data steward with the existing *derived* CETI output should run:

```python
from validation.ceti2024 import export_sanitized_ceti2024
export_sanitized_ceti2024(
    "path/to/ceti2024_buzz_features.csv",
    "data/ceti2024/buzz_features.csv",
)
```

The exporter whitelists the derived fields, replaces original tag/dive labels
with release-local sequential pseudonyms, and drops absolute buzz-clock times.
It does not return or write the private crosswalk. Unsalted hashes are avoided
because the source identifier namespace is small enough to enumerate. Review
the resulting CSV, then run `validate_publication_table` before committing it.
The current release candidate includes this 336-row table for technical
reproduction, but it remains marked `steward_review_required` in
`data/manifest.csv` and must not be pushed publicly until that review is
recorded.

## Re-running CETI validation

With the package source on `PYTHONPATH` and a reviewed table present:

```bash
python -c "from validation.ceti2024 import run_ceti2024_validation; run_ceti2024_validation('data/ceti2024/buzz_features.csv', 'results/ceti2024')"
```

The resulting `labels.csv`, `kinematic_statistics.csv`, and
`sequence_statistics.csv` plus the corner-clustering, kinematic-summary and
sequence figures are fully derived, reviewable outputs.  The notebook is an
annotated front end to this same workflow, rather than a second analysis
implementation.
