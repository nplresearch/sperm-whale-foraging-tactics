# Review of the overnight R1 rebuttal work (2026-11-23)

**Scope of this review.** Done: read `REVIEW_R1_PLAN.md` and `overleaf/R1_MANUSCRIPT_CHANGES.md` in
full and the core modules (`kinematics.py`, `speed_regimes.py`, `heading_steps.py`); ran the 74
existing tests; checked **97 numbers** from the plan against `results/review_r1/` (all match,
`claims.yaml`); re-derived the converged-BIC claim; ran one new analysis (circularity, M2).
**Not done:** recomputing pipelines from raw tags; re-running the Azores phase script (needs Dryad
files); the 1.8k-line legacy scripts were not line-reviewed; the 32-slide team deck was not inspected
(it may carry the issues below).

**Verdict:** the arithmetic is sound and reproducible. The *inference* has one circular result and
the written plan is internally inconsistent in places. Fixable in days, not weeks.

## Problems, most serious first
| # | Severity | Problem | Evidence | Fix | Module |
|---|---|---|---|---|---|
| 1 | **Critical** | "Type B swims 1.72× faster at matched pitch/direction/depth", "AUC 0.84", "B accelerates into the buzz" and the 2.5–2.7× energy/buzz are implied by the labels. Labels are built on vertical speed (alone AUC 0.93 for the labels); OCDR = \|vz\|/sin(pitch). | Adding log\|vz\| to the model gives B/A **1.00 (0.98–1.02)**; medians coincide inside vz quartiles; synthetic reproduction. | Drop these from letter/abstract. Lead with stroke effort + coverage (4.5 % of A valid). Independent speed needs raw DTAG audio/accelerometer. | M2, M4 |
| 2 | High | Plan and change list contradict themselves. D3/D4 rows still read "Supported"; abstract proposal (`:118`) says dives end sooner with Type B; conclusion (`:344`) says "oxygen-limited choice of tactic"; "chain" step 4 struck through in one place, live in another; H3 still framed as to-test; abstract "about 2.5×" rests on #1. | Plan lines ~433–434, 828, 838, 920–927. | Apply `CORRECTIONS_TO_PLAN.md`; regenerate the change list from `claims.yaml` statuses. | all |
| 3 | High | The evidence for **two modes** rests on vertical-speed axes. On a speed-free axis (ramp-up × stroke) k=2 is *not* supported (ΔBIC +16, p 0.085), though the split reproduces 91 % of labels. | `classifier_kinematic_retest.csv`, `kinematics_summary.json`. | Say so plainly: partition is robust, discreteness is conditional on vertical motion. Don't claim "two discrete tactics". | M3 |
| 4 | High | Per-buzz cost ratio 2.4–2.7× is mostly duration (B buzzes 1.9× longer; intensity 1.27×). | `energy_rebuilt_summary.csv`. | State "longer and ~1.3× harder", not "2.5× costlier". | M4 |
| 5 | Medium | Heading-turn response near buzzes checked against roll but not **pitch**; heading is poorly defined at steep pitch and Type B buzzes are steep. | M5 README. | Re-fit stratified by \|pitch\| bins; exclude blocks with mean \|pitch\| > 60°. | M5, M6 |
| 6 | Medium | ~25 post hoc tests, p-values to 10⁻³¹ from autocorrelated 5-s blocks. Significant `mu ~ buzz rate` (p 0.009, 15 dives) is not mentioned; MVT result flips to p 0.097 with last bouts. | `trajectory_tests.json`. | One SI table, all results incl. these, whale-level or cluster-permutation inference, "very small" not exact p. | M5, M6 |
| 7 | Medium | Azores: one juvenile, 11 dives, 58 buzzes; plan says "make it stronger". Phase/seafloor numbers exist only in printed output. | `run_review_r1_azores_phase.py`. | "Consistent, single-whale"; make the script write JSON. | M7 |
| 8 | Medium | 17 buzzes with 180° pitch/heading error: not checked whether the constant-speed reconstruction (and so the registered labels) used the bad values. | plan "Data issues". | Check on raw tags; report affected labels. | M0 |
| 9 | Low | Inherited SI error: BIC selection with unconverged EM (ΔBIC −5.3 vs −43); "minimum at k=2" is a k=2/k=3 tie. | `test_converged_em_…`. | Regenerate SI figure. | M3 |
| 10 | Low | `.venv` has no packages (`check_release_safety.py` fails there); `pyyaml` undeclared; plan says 70 tests, now 74. Repo has many uncommitted edits not from this work (not committed here). | — | Rebuild venv from `pyproject`; add pyyaml to `test` extra (not done: `pyproject.toml` has others' uncommitted edits). | — |
| 11 | Info | Numbers only in the plan, no file: sampling-rate dependence of μ, 0.14° heading change, 17 buzzes, Azores phase results. | `claims.yaml` (`printed_only`). | Make scripts write them. | M0, M5, M7 |

## What holds up (safe to build on)
Speed-regime accounting (M1); stroke-effort evidence and the 4.5 % coverage figure (M2); converged
GMM/bootstrap results (M3); the withdrawal of the oxygen/termination story and its transit-buzz
explanation (M6); trajectory two-mode finding and the sampling-artefact diagnosis (M5, with #5).
