# Data directory

This directory contains only public-source instructions and approved,
pseudonymized derived inputs. It must conform to the top-level
[data policy](../DATA_POLICY.md).

## Layout

- `dswp/`: pseudonymized reconstructed trajectories and buzz-level
  measurements for the primary dataset;
- `ceti2024/`: derived buzz information for the independent 2024 validation;
- `azores/`: authoritative open-data citation, retrieval, checksum, and
  preprocessing documentation;
- `manifest.csv`: inventory and checksums for every distributed data file.

The raw-to-derived export is performed in the restricted internal environment.
Only its validated outputs cross into this repository.

Run `python scripts/build_data_manifest.py` after any approved input changes.
Every analytical input, including each reconstructed trajectory, is then
recorded with its schema version, row/sample count, SHA-256 checksum, and
release status.
