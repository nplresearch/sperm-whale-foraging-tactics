# Submission reconciliation: manuscript, code, and data

Status: updated 2026-08-15. This checklist is intended for the revision made after the
preprint has been online for a short period. It distinguishes checks that could
change reported results from release and documentation work. The preprint
snapshot can remain fixed while these checks are run.

## Numbered remaining-issue index

1. **Azores manuscript alignment:** choose the operative classification and
   window definitions and regenerate corrected sequence intervals.
2. **Comeback analysis:** choose one recurrence definition and classifier.
3. **Terminal-buzz count:** reconcile the event definition and type counts.
4. **CETI roll panel:** release a safe derived input, label it legacy, or remove
   the panel.
5. **Buzz-centred release hygiene:** commit the corrected implementation and
   outputs and retire or clearly mark the obsolete null-result notebook.
6. **Trajectory/L\'evy output freeze:** rerun and checksum the corrected
   trajectory statistics and figures; the fitter wording itself is resolved.
7. **Trajectory-reconstruction freeze:** regenerate the reviewed comparison
   output and retain the correct 219-m aggregation wording.
8. **DSWP Markov/pause freeze:** freeze the ten-deployment, gap-preserving
   Markov outputs and resolve pause quantities consistently with issue 3.
9. **Data-steward approval:** approve every derived release input and rerun the
   safety audit.
10. **Map reproducibility boundary:** document or release the permissible map
    inputs without exposing protected locations or identifiers.
11. **Manuscript-artifact crosswalk:** bind every claim and figure to frozen
    code, inputs, checksums and tolerances.
12. **Bibliography cleanup:** repair the remaining style/metadata warnings.

The corrected buzz-centred scientific result, the custom L\'evy fitter Methods
description, the plateau-threshold diagnostic, the classifier-speed provenance,
the energetic-model alignment and the DSWP Markov resampling description are
resolved; only their explicitly listed release-freeze tasks remain open. For the plateau diagnostic, the
Methods and Supplementary Fig. S10 now identify 0.7 as a robust operating point
rather than a unique optimum and report the deterministic sweep values; the
production boundaries are unchanged.

## A. Result-affecting gates

### 1. Azores validation reproduction — completed; manuscript decisions remain

**Resolution.** The checksum-pinned Dryad files now drive the complete
publication-safe prey-field, kinematic, pause, geometry, robustness, and
sequence implementation in `validation.azores`. The operative 29/28/1 split
and a genuinely balanced 29/29 sensitivity are both exported and tested.

**Claims to reproduce.**

- 27 dives and 108 buzzes overall; 11 daytime dives and 58 analysed buzzes.
- The 29/29 extreme-corner classification and its conservative-split checks.
- Echo-count result: \(P=0.037\), \(d=0.35\), including its stated lack of
  robustness.
- Prey-depth result: \(P=0.003\), \(d=1.39\), plus conservative-split and
  threshold-free results.
- Nearest-prey-range null result.
- Signed vertical velocity, geometry, pause and Markov values in the SI.
- Main Fig. 4 and Supplementary Fig. S19.

**Implementation.** `src/validation/azores.py`,
`notebooks/validation/03_azores_derivation.ipynb`, and
`notebooks/validation/04_azores_manuscript_figures.ipynb`.

**Remaining decision.** Align the manuscript with the operative 29/28/1 sample
or choose the balanced sensitivity, describe the implemented buzz-window
definition, and regenerate Markov intervals from the duplicate-preserving dive
bootstrap. Do not combine the operative P values with balanced 29/29 wording.

### 1b. Correct the buzz-centred displacement time origin and refreeze the claim (resolved)

**Why this is substantial.** The SI's eight-whale null result is reproduced
only when the legacy notebook subtracts `dive_start` from click times that are
already dive-local. This drops most later dives. The corrected time origin with
the registered GMM retains 20 whales and yields significant A/B differences at
every tested positive lag.

**Implementation.** `trajectory.manuscript.buzz_centred_results` and
`notebooks/trajectory/02_manuscript_trajectory_figures.ipynb` expose the legacy
forensic and corrected paths separately. The public regression test reproduces
all archived eight-whale P values exactly.

**Resolution.** The registered GMM and dive-local time origin are now frozen as
the manuscript-facing path. The corrected `+-30 s` analysis retains 20 whales,
1,346 Type A windows, and 1,141 Type B windows. Type B exceeds Type A at all
eight tested positive lags, with all paired Wilcoxon P values below 0.001 after
Bonferroni correction. Corrected tables and figures are pipeline outputs; the
double-subtraction path remains only as provenance and a regression test.

**Release hygiene still required.** Before the public repository is frozen,
commit the corrected implementation, regression test, tables and figure
together. The exploratory Lévy notebook that generated the obsolete null result
must either be updated or clearly marked as legacy and non-manuscript-producing,
so that it cannot accidentally regenerate or be cited as the operative analysis.

### 2. Choose and register one comeback definition

**Why this is substantial.** The preprint deliberately retains the v1
horizontal 10/50-m analysis, whereas the recovered production context uses
20-s-subsampled three-dimensional trajectories and a 50/150-m rule.

**Current alternatives.**

- Legacy manuscript: 10/50 m, approximately 1–30%, \(n=1691\),
  OR \(=1.11\), 95% CI 0.78–1.59, \(P=0.56\), heterogeneity \(P=0.041\).
- Recovered production context with current labels: 50/150 m, 0–11.1%,
  \(n=1660\), OR \(=1.151\), 95% CI 0.807–1.642, \(P=0.433\),
  heterogeneity \(P=0.096\).

**Implementation target.** `src/dswp/comebacks.py` and
`results/dswp/comeback_*`.

**Pass condition.** One preregistered spatial definition and one classifier
version regenerate the SI prose, S8, S9 and all counts and inferential values.
Do not combine legacy labels with the recovered trajectory context.

### 3. Energetic-model reproduction — completed

**Resolution.** The manuscript and SI now describe the trajectory-driven
positive-acceleration model implemented in `src/dswp/energetics.py`. The
registered outputs and numerical regression test reproduce the reported
whale-level means and component values from the released reconstructed
trajectories. Goldbogen is cited as inspiration for the hydrodynamic framework,
not as a fitted prey-interception model.

**Claims to reproduce.**

- Type A: 1.275 MJ; Type B: 9.069 MJ; B/A \(=7.11\).
- Twenty paired whales, Type B above Type A in every whale, paired
  \(P<0.001\).
- Drag, positive-acceleration and resting components in the SI.
- Aoki sensitivity: 0.013 versus 0.111 MJ, B/A \(=8.51\), Type B above
  Type A in every whale.

**Implementation target.** `scripts/run_pipeline.py`,
`results/dswp/buzz_energy.csv`, `individual_energy.csv`,
`aoki_event_energy.csv` and `aoki_individual_energy.csv`.

**Verified result.** Fig. 2g and the SI values are reproduced: 1.275 MJ for
Type A, 9.069 MJ for Type B, Type B above Type A in all 20 paired whales, and
the registered drag, positive-acceleration, resting, and Aoki components. The
derivation is documented in `notebooks/dswp/02_energy_model_derivation.ipynb`.

### 4. Resolve the terminal-buzz/pause count mismatch

**Why this is substantial.** The Results report 36 terminal events
(32 Type B, 4 Type A), while the registered released table currently yields
32 (29 Type B, 3 Type A).

**Implementation target.** Recover and document the exact vocal-phase and
terminal-event rule used for the manuscript, or update the prose and binomial
calculation from `results/dswp/pause_categories.csv` and
`pause_association.json`.

**Pass condition.** One event definition regenerates the count, type split,
binomial result and pause panels. Terminal counts must not be inferred from the
Markov end probabilities.

### 5. Decide how to handle the CETI roll-speed time course

**Why this is substantial.** The safe CETI release table reproduces the
per-buzz kinematic contrasts but not the raw 25-Hz roll-speed time-course panel.

**Implementation target.** Either:

1. obtain approval for a binned, derived roll-time-course table and regenerate
   the panel;
2. explicitly label the current panel as a non-reproducible legacy
   illustration; or
3. remove the panel.

**Pass condition.** Every CETI SI panel has an approved safe input and a
deterministic generator. The validation remains limited to 231 kinematic
buzzes from 10 tags/19 dives and 149 heading-resolved buzzes from five tags,
without demographic, prey-field or full-GMM claims.

### 5b. Resolve classifier-speed provenance (resolved)

The primary GMM retains the original constant-speed-derived buzz-average 3-D
speed and therefore preserves the reported A/B/unassigned counts and all
downstream figures and tests. The Methods and SI now state this provenance
explicitly and distinguish the classifier input from the pitch-adaptive
trajectories used for trajectory-scale and energetic analyses.

An otherwise identical pitch-adaptive-speed refit gives 1,350 A, 1,176 B and
1,160 unassigned events, compared with 1,346 A, 1,142 B and 1,198 unassigned
under the primary classifier. No event confidently assigned by both versions
switches directly between A and B; only posterior-boundary membership changes.
`results/dswp/classifier_speed_sensitivity.json` and the registered regression
test freeze the exact comparison. No downstream result was silently combined
across classifier versions.

## B. Important numerical and methodological confirmations

### 6. Freeze the trajectory and Lévy-like outputs

The manuscript Methods already describe the operative custom 30-candidate
cut-off sweep and retain the cautious term “Lévy-like.” This remaining item is
only the clean rerun, numerical comparison and artifact freeze.

Run `trajectory.analysis.analyze_release` on float64 reconstructed paths and
compare:

- 209 dives and 20 individuals;
- \(\mu=2.354\) dive median, 2.364 individual median and 2.155 pooled;
- global MSD exponent \(\alpha=1.909\) and the reported scale-specific values;
- the 30-candidate, 5th–80th-percentile KS cut-off procedure;
- main Fig. 1c–d and the supplementary robustness panels.

**Pass condition.** `results/trajectory/per_dive_levy_msd.csv`,
`timescale_msd.csv` and `population_summary.json` reproduce the manuscript to
declared tolerances. Retain “Lévy-like”; do not claim a unique or optimal Lévy
mechanism.

### 7. Freeze the trajectory-reconstruction comparison

Regenerate `results/dswp/reconstruction_method_summary.csv` from the reviewed
aggregate reconstruction-error table.

**Pass condition.** The selected method has the lowest mean error across
deployments and the mean of deployment-specific median errors is 219.398 m.
Do not revert to “pooled median” or “unique winner” language.

### 8. Freeze Markov and pause-transition outputs

Regenerate the deployment-resampled Markov analysis using 200 resamples that
exclude ten deployments and preserve ambiguous gaps.

**Pass condition.** `results/dswp/buzz_markov_transitions.csv` and the figure
recover Start→B 0.54, A→A 0.55, B→B 0.42, A→End 0.06 and B→End 0.13 with the
reported uncertainties. Resolve item 4 separately.

## C. Data-release and reproducibility obligations

### 9. Obtain explicit steward approval for every derived release input

The DSWP derived inputs, reconstructed trajectories and CETI feature table are
currently marked `steward_review_required`.

**Pass condition.**

- Every public file has an approved status and checksum in `data/manifest.csv`.
- No raw audio, raw sensor stream, absolute position, original identifier,
  private path or crosswalk enters the public repository.
- `scripts/check_release_safety.py` passes in a clean clone.
- The private identifier crosswalk and export log remain outside the release.

### 10. Define the reproducibility boundary for map artwork

Main Fig. 1’s regional map and named representative track are not currently
generated by the public code, intentionally avoiding location-bearing data.

**Pass condition.** Either release permissible bathymetry/layout inputs and a
generator, or state clearly that numerical trajectory analyses are
reproducible while the geographic presentation asset is not. Scrub private
names and tag identifiers from release artifacts.

### 11. Run a final manuscript–artifact crosswalk

For every main and supplementary figure/table, record:

- manuscript label and exact numerical claims;
- generating script/notebook and version;
- approved input file and checksum;
- output artifact and checksum;
- tolerance used for numerical comparison.

**Pass condition.** Compile without unresolved references; all displayed
numbers agree with the frozen outputs; then record the manuscript commit, code
commit, data-bundle version, environment lock and archive DOI together.

### 12. Clear the remaining bibliography warnings

The manuscript compiles, but BibTeX still warns that `Tonnesen2020dataset` uses
an unsupported entry type and that `Leitao_2025` lacks a journal field.

**Pass condition.** Both records use complete, style-compatible metadata and a
fresh build produces no missing-field or unsupported-entry warnings.

## Recommended execution order

1. Issues 2 and 1: comeback definition, then Azores manuscript alignment.
2. Issues 3 and 4: terminal-count reconciliation and CETI roll-panel decision.
3. Issues 5--8: buzz-centred, trajectory/L\'evy, reconstruction and Markov
   release freezes.
4. Issues 9--10: steward review, safety audit and map boundary.
5. Issues 12 and 11: bibliography cleanup, final manuscript--artifact crosswalk
   and version freeze.
