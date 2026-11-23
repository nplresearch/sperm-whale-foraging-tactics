# review_r1 — modular, independently testable pieces of the Reviewer-1 response

Branch `review-r1-modules`. Main is untouched. Read `REVIEW_OF_OVERNIGHT_WORK.md` first:
it lists what is wrong with the overnight draft, and one headline result is **circular**.

## How it is organised
One folder per point the letter makes. Each has a `README.md` (claim, method, inputs/outputs,
failure modes, what would falsify it), tests, a notebook, and a `run.py` that recomputes it.

| Module | Letter point | Status |
|---|---|---|
| [m0_data_audit](m0_data_audit) | inputs | ok; 1 manual check open |
| [m1_speed_regimes](m1_speed_regimes) | R1 pt 2: speed is assumed | verified |
| [m2_independent_speed_effort](m2_independent_speed_effort) | R1 pt 2: "could A be fast?" | ⚠ speed contrast circular; stroke effort ok |
| [m3_classifier_discreteness](m3_classifier_discreteness) | R1 pt 3 | verified; SI BIC error inherited |
| [m4_energetics](m4_energetics) | R1 pt 4 | sevenfold withdrawn; 2.5× circular/duration |
| [m5_trajectory_search](m5_trajectory_search) | pre-emptive (Lévy/steps) | verified, post hoc, pitch confound open |
| [m6_tactic_search_coupling](m6_tactic_search_coupling) | tactic ↔ search; phase check | coupling ok; oxygen/termination withdrawn |
| [m7_azores](m7_azores) | validation | echo ok; phase results printed-only |

R1 point 1 (framing) is writing, not code: see `overleaf/R1_MANUSCRIPT_CHANGES.md`.

## The safety net: `claims.yaml`
Every number the letter quotes is a row: module, result file, field, value-in-letter, tolerance,
and a **status** (`verified`, `circular`, `withdrawn`, `printed_only`). One test checks all of them:

```bash
pip install pyyaml                          # only extra dependency
pytest review_r1                            # everything (~15 s)
pytest review_r1/test_claims.py -k M3       # one module's numbers
pytest review_r1/m2_independent_speed_effort
```
Rules for contributors: if a claim fails, decide whether the letter, the file or the code is
wrong; never just widen the tolerance. Don't quote `circular` or `withdrawn` claims as support.
New number in the letter → add a row. Number only printed by a script → make the script write it,
then flip `printed_only` to `verified`.

## Recomputing
`python review_r1/mN_*/run.py` backs up `results/review_r1` to `results/review_r1_backup_<ts>`,
runs the legacy scripts (they overwrite results in place), then re-checks that module's claims.
Legacy scripts in `scripts/run_review_r1_*.py` are kept unchanged as provenance.

## Data
The kinematics tables (`data/dswp/*kinematic*.csv`) are `pending_steward_review` and are **not
committed** on this branch. Tests that need them skip with a clear reason; ask the steward for
access (or run `scripts/export_steward_kinematics.py` with the raw tag files) to run the full set.
Do not publish them or push this branch to a public remote before the steward signs off.

## Hand-off notebook
Each module's `notebook.ipynb` shows the letter-vs-file table (Part 1) and the evidence (Part 2).
