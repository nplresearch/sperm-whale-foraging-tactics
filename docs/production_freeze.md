# Production analysis freeze: 25 August 2026

This document defines the production code state paired with the manuscript
freeze of 25 August 2026. The corresponding Git tag is
`production-code-2026-08-25`.

## Included scope

- DSWP buzz construction from released derived click times;
- registered GMM classification and classifier-speed sensitivity;
- deployment-resampled sequence analysis with ambiguous events preserved as
  gaps;
- trajectory reconstruction summaries, Lévy-like trajectory statistics, and
  corrected buzz-centred displacement analysis;
- trajectory-driven energetic comparison and the Aoki drag-only sensitivity;
- final Azores 28/28/two-boundary-tie validation based on checksummed open
  inputs, including duplicate-preserving sequence bootstrap; and
- safe buzz-level CETI 2024 validation.

## Accepted production exception

The exploratory comeback result is frozen exactly as reported in the
manuscript. Its manuscript-producing legacy labels and recurrence choices are
not the same as the registered-current sensitivity analysis. Both outputs are
retained and named separately; neither is presented as a robustness
replication of the other. The author explicitly accepted this provenance
exception for the production paper.

## Excluded or separately governed scope

- reconstruction from raw DTAG audio or sensor streams;
- release of raw DSWP or CETI data, absolute locations, or identifier
  crosswalks;
- deterministic regeneration of presentation-only geographic artwork;
- the legacy CETI per-bin roll-speed time-course panel; and
- public archival publication of the derived-data bundle before steward and
  licence approval.

## Verification gates

The frozen tree passes the complete automated test suite and
`scripts/check_release_safety.py`. The paired manuscript and cumulative
bioRxiv redline compile without unresolved citations or references and were
visually inspected after rendering.

This technical freeze records a reproducible analysis state. It does not
replace data-owner approval, licence selection, or the final archival DOI and
manuscript--artifact checksum crosswalk.
