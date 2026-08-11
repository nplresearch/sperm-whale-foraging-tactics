# CETI 2024 validation release

`buzz_features.csv` contains 336 derived buzz records under release-local
deployment and dive pseudonyms. The movement cohort comprises 231 events from
10 units and 19 dives; rows without movement retain their acoustic summaries
and explicit missing kinematics. Absolute clock times, original tags, names,
raw sensors, GPS, field metadata, and private paths are absent.

The table was created with
`validation.ceti2024.export_sanitized_ceti2024`, which uses a strict column
allowlist and never writes or returns an identifier crosswalk.

The corresponding reconstructed CETI 2024 trajectory arrays are not yet
present in the working release because no reviewed derived path bundle was
available locally. They remain a release gate: when supplied by the data
steward, they must use the same local-coordinate numeric-only NPZ format as the
DSWP paths and contain no raw movement channels. The public buzz-level
validation currently runs in full; heading/path panels requiring the missing
paths cannot be independently rebuilt from this directory.
