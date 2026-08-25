# CETI 2024 validation release

`buzz_features.csv` contains 336 derived buzz records under release-local
deployment and dive pseudonyms. The movement cohort comprises 231 events from
10 units and 19 dives; rows without movement retain their acoustic summaries
and explicit missing kinematics. Absolute clock times, original tags, names,
raw sensors, GPS, field metadata, and private paths are absent.

The table was created with
`validation.ceti2024.export_sanitized_ceti2024`, which uses a strict column
allowlist and never writes or returns an identifier crosswalk.

This release is intentionally scoped to the buzz-level validation. It does not
distribute reconstructed CETI paths or the legacy high-frequency roll trace.
Any later path release would be a new, separately reviewed data version using
local-coordinate numeric-only arrays and containing no raw movement channels.
