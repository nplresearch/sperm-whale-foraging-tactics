# Licence decision for public release

No licence is granted by the current private review copy. A public release
needs one explicit project decision covering code and one covering the derived
data owned by the contributing projects.

## Proposed licence split

- **Analysis code:** MIT License. This is short, permissive, and compatible
  with scientific reuse while retaining attribution and the warranty
  disclaimer.
- **Repository-authored derived tables and local-coordinate reconstructed
  paths:** Creative Commons Attribution 4.0 International (CC BY 4.0). This
  permits reuse with attribution and is distinct from the licence on the code.
- **Azores source data:** unchanged; the authoritative Dryad record is CC0 1.0
  and is cited rather than mirrored here.

The raw DSWP and CETI records are not part of the proposed licence because they
are not distributed in this repository.

## Approval needed

Before changing the repository visibility, record written confirmation that:

1. the software copyright holders approve MIT;
2. the DSWP data steward approves the listed DSWP derived files under CC BY 4.0;
3. the Project CETI data steward approves `data/ceti2024/buzz_features.csv`
   under CC BY 4.0; and
4. all parties approve the pseudonymization and public-data boundary described
   in `DATA_POLICY.md`.

After those confirmations, add `LICENSE` and `LICENSE-DATA` with the approved
texts, change the manifest statuses from `steward_review_required` to the
agreed release status, rerun the safety audit, and then mint the archival DOI.
