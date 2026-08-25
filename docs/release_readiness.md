# Public-release readiness

Last technical review: 25 August 2026.

## Completed technical work

- The derived-data bundle is pseudonymized with release-local individual,
  deployment, dive, trajectory, and buzz identifiers.
- Raw sensor streams, audio, absolute positions, field identifiers, private
  paths, and identifier crosswalks are excluded.
- The final Azores choices are fixed at 28 Type A, 28 Type B, and two boundary
  ties, using the full buzz-plus-margin echo window and the
  duplicate-preserving dive bootstrap.
- The CETI release boundary is fixed at the buzz-level acoustic and kinematic
  validation. Reconstructed CETI paths and the legacy high-frequency roll
  trace are not part of this version.
- The manuscript-facing classifier, Markov resampling, energetic model,
  trajectory reconstruction summary, Lévy-like fitter, buzz-centred
  displacement analysis, terminal-event denominator, and plateau diagnostic
  are aligned with the frozen code outputs.
- The exploratory comeback result is retained as an author-approved production
  exception, with the legacy and registered-current analyses named separately.
- The analysis tree and manuscript are paired to the versions recorded in
  `docs/production_freeze.md` and `CITATION.cff`.

The clean-environment run record and final checksums are written to the release
package generated for submission. The automated safety check must be rerun
after any change to `data/`, a notebook, or a release document.

## Human decisions still required before a public release

These steps cannot be completed by a technical audit:

- written data-steward approval for the final DSWP and CETI derived files;
- approval of the software and data licences proposed in `LICENSING.md`; and
- creation of the archival record, followed by insertion of its DOI and the
  bioRxiv or journal citation in `CITATION.cff`.

Until those items are recorded, keep the GitHub repository private. They do not
block confidential editorial or reviewer access, nor do they block submission
of the clean manuscript files.
