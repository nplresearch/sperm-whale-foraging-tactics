# M0 — Data audit (what every other module stands on)

**Supports:** all points. **Owner:** _unassigned_ **Status:** tests pass; one manual check open.

## Claim
The kinematic tables exported for this revision (`data/dswp/*_kinematics.csv`,
`buzz_kinematic_profiles.csv`) are keyed 1:1 to the public buzz table, carry no
physically impossible pitch, and contain nothing that breaks the release-safety gate.

## Inputs / outputs
- In: `data/dswp/buzz_events.csv`, `buzz_kinematics.csv`, `data/manifest.csv`.
- Out: none (assertions only). Steward export is `scripts/export_steward_kinematics.py`
  and needs the raw tag `.mat` files, which are **not** in this repo.

## Run
```bash
pytest review_r1/m0_data_audit
```
Tests needing the steward tables skip cleanly when they are absent.

## Known failure modes
- 17 buzzes in the internal table have pitch/heading shifted by exactly 180°. The export
  uses the tag record. **Open:** was the *constant-speed reconstruction* (hence the
  registered classifier) built from the bad pitch? Needs `repo/Data/big/…` — the skipped
  test marks where to put the answer.
- Two deployments have no orientation data (66 buzzes, 1.8 %): all pitch-based measures NaN.
- The last dive of 22 tags is incomplete (tag came off before surfacing).

## What would falsify it
Row-count or ID mismatch between kinematics and events; |pitch| > 90°; the safety gate
reporting raw-looking streams.

## Data policy
The four new tables are `pending_steward_review` in the manifest. **Do not publish them**
until the steward signs off (see `DATA_POLICY.md`). They are deliberately not committed on
this branch.
