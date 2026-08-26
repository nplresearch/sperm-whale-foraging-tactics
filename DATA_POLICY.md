# Public data boundary

## Purpose

The release goal is to reproduce the paper's analyses while keeping the
original biologging and field data out of a public GitHub release. At the
defined public boundary, a result is reproducible when it can be regenerated
from documented, publication-approved derived inputs; upstream signal
processing from raw tag files is deliberately out of scope. The Azores
analysis is recovered from checksummed open inputs, and the CETI component is
explicitly scoped to the buzz-level validation.

## Included

Only the minimum derived information required by the analyses may be committed:

- pseudonymous deployment, individual, dive, and event identifiers;
- relative time within a deployment or dive;
- reconstructed three-dimensional trajectories in a local coordinate frame;
- derived depth, speed, orientation, turning, and displacement measures needed
  for the trajectory analysis;
- derived buzz timing, acoustic summaries, kinematic summaries, tactic labels
  or probabilities, sequence position, and model-estimated energetic values;
- aggregate numerical results, uncertainty estimates, and figure source data;
- source-independent simulated or toy data used by tests.

Repeated deployments of one whale may share a stable pseudonymous individual
identifier where this is analytically necessary. The crosswalk to names,
field identifiers, or other direct identifiers must remain outside the public
repository.

## Excluded

The following must not be committed:

- raw or calibrated audio;
- raw pressure, accelerometer, magnetometer, or other sensor streams;
- original tag, MATLAB, field-log, or vessel-follow files;
- absolute timestamps or dates when relative time is sufficient;
- absolute whale or vessel GPS positions;
- whale names, field identifiers, tag serial numbers, age/sex metadata, social
  associations, kinship records, or identifier crosswalks;
- unpublished prey echograms or other source data whose release has not been
  approved;
- private download links, credentials, access tokens, personal filesystem
  paths, or institutional storage paths;
- opaque serialized Python or MATLAB objects whose contents cannot be audited.

## Dataset-specific rules

### DSWP

The release may contain pseudonymized reconstructed trajectories and the
derived buzz-level table needed for the primary analyses. Reconstruction from
the original sensor streams is intentionally outside the public reproducibility
boundary.

### CETI 2024

This release contains only pseudonymized derived buzz information. Reviewed
reconstructed paths are not part of the current release boundary. The release
must not contain source tag structures, audio, raw sensor channels, GPS, field
metadata, or an identifier crosswalk.

### Azores

The repository should point to the authoritative open archive and document how
to retrieve and verify it. Open upstream data should not be copied into this
repository unless its licence, attribution requirements, and size have been
reviewed explicitly.

## Format and minimization

- Prefer CSV for small tables and Parquet for larger typed tables.
- Prefer compressed NumPy arrays only when tabular formats are unsuitable and
  document every array and unit.
- Do not use pickle files in the public release.
- Express horizontal trajectories relative to a local origin. Keep absolute
  location only if the data owners explicitly approve it and it is required by
  a reported analysis.
- Round values no more finely than the analysis requires.
- Keep input and generated-output directories separate.

## Release validation

`python scripts/check_release_safety.py` checks every release for raw-data file
types, unsafe fields, identifying paths, embedded notebook outputs, and opaque
arrays. The v1 DSWP derived tables and local-coordinate trajectories were
reviewed and approved by the data owner for public release. Raw DSWP records
remain excluded.
