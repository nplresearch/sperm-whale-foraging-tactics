# Submission reconciliation: manuscript, code, and data

Status: updated 2026-08-25. This checklist is intended for the revision made after the
preprint has been online for a short period. It distinguishes checks that could
change reported results from release and documentation work. The preprint
snapshot can remain fixed while these checks are run.

## Remaining public-release actions

No result-affecting reconciliation item remains open. The CETI release is
formally scoped to the buzz-level validation, the regional map is documented as
a presentation-only asset, and `result_map.md` plus the release checksum
manifest provide the manuscript--artifact crosswalk.

Three external actions remain before changing the repository visibility:

1. record data-owner approval for the DSWP and CETI derived files;
2. approve and add the software and data licences proposed in `LICENSING.md`;
3. mint the archival record and add its DOI and the paper/preprint citation.

The Azores analysis, terminal-event denominator, reconstruction aggregation,
corrected buzz-centred result, custom L\'evy fitter, plateau-threshold diagnostic,
classifier-speed provenance, energetic-model alignment, DSWP Markov resampling,
and bibliography records are resolved. The comeback discrepancy is retained as
an author-approved production exception: both analytical variants remain
labelled, and the legacy path reproduces the frozen manuscript result. For the plateau diagnostic, the
Methods and Supplementary Fig. S10 now identify 0.7 as a robust operating point
rather than a unique optimum and report the deterministic sweep values; the
production boundaries are unchanged.

## A. Result-affecting gates

### Resolved A1. Azores validation reproduction and manuscript alignment

**Resolution.** The checksum-pinned Dryad files now drive the complete
publication-safe prey-field, kinematic, pause, geometry, robustness, and
sequence implementation in `validation.azores`. The final 28/28/two-tie split
and a disjoint 29/29 sensitivity are both exported and tested.

**Claims to reproduce.**

- 27 dives and 108 buzzes overall; 11 daytime dives and 58 analysed buzzes.
- The 28/28/two-tie extreme-corner classification and its conservative-split checks.
- Echo-count result: \(P=0.037\), \(d=0.36\), including its stated lack of
  robustness.
- Prey-depth result: \(P=0.004\), \(d=1.34\), plus conservative-split and
  threshold-free results.
- Nearest-prey-range null result.
- Signed vertical velocity, geometry, pause and Markov values in the SI.
- Main Fig. 4 and Supplementary Fig. S19.

**Implementation.** `src/validation/azores.py`,
`notebooks/validation/03_azores_derivation.ipynb`, and
`notebooks/validation/04_azores_manuscript_figures.ipynb`.

**Resolution.** The manuscript and registered outputs use the final classifier
from Andrea Santoro's `CETI_Foraging` commit `a74bab4`: two observations exactly
equidistant from both corners remain unclassified. The echo window runs from
10 s before buzz onset through 10 s after buzz end, nearest range is the minimum
over that interval, and the SI intervals use the duplicate-preserving dive
bootstrap. The regenerated SI figure is pixel-identical to the Overleaf asset.

### Resolved A2. Buzz-centred displacement time origin

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

The corrected implementation, regression test, tables and figure are registered
together. The double-subtraction path remains explicitly named as forensic
provenance and is not a manuscript-producing default.

### Accepted exception A3. Comeback definition and classifier provenance

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

**Production decision.** For the 2026-08-25 paper freeze, the author elected to
retain the exploratory legacy manuscript result and not rerun S8, S9 or their
prose. The registered-current calculation remains a separately labelled
sensitivity. This waiver closes the item for production without asserting that
the two analytical definitions are equivalent.

### Resolved A3. Energetic-model reproduction

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

### Resolved A4. Terminal-buzz/pause count

The registered event table contains 36 terminal buzzes: 29 Type B, 3 Type A,
and 4 unassigned. Thus 36 is the full terminal-event count and 32 the confidently
classified denominator; the observed B fraction is 29/32 = 0.91. The Results
state both denominators explicitly. Pause analyses remain unchanged because all
36 terminal events were already excluded.

### Resolved A6. CETI release scope and roll-speed time course

**Why this is substantial.** The safe CETI release table reproduces the
per-buzz kinematic contrasts but not the raw 25-Hz roll-speed time-course panel.

**Production decision.** Version 0.1 is explicitly a buzz-level CETI release.
It reproduces the 231-event kinematic validation from 10 tags and 19 dives, and
the heading-resolved summaries available in the derived buzz table, without
demographic, prey-field, or full-GMM claims. Reconstructed CETI paths and the
legacy high-frequency roll trace are not distributed or claimed as
deterministically regenerated by this repository. Adding either in a future
version requires a new steward-reviewed data release.

### Resolved A5. Classifier-speed provenance

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

### Resolved B1. Trajectory and Lévy-like outputs

The manuscript Methods describe the operative custom 30-candidate cut-off sweep
and retain the cautious term “Lévy-like.” The registered numerical outputs,
figures and regression tests freeze the following values:

Run `trajectory.analysis.analyze_release` on float64 reconstructed paths and
compare:

- 209 dives and 20 individuals;
- \(\mu=2.354\) dive median, 2.364 individual median and 2.155 pooled;
- global MSD exponent \(\alpha=1.909\) and the reported scale-specific values;
- the 30-candidate, 5th–80th-percentile KS cut-off procedure;
- main Fig. 1c–d and the supplementary robustness panels.

`results/trajectory/per_dive_levy_msd.csv`, `timescale_msd.csv` and
`population_summary.json` reproduce the manuscript to declared tolerances.
Future revisions should retain “Lévy-like” and avoid claiming a unique or
optimal Lévy mechanism.

### Resolved B2. Trajectory-reconstruction comparison

`results/dswp/reconstruction_method_summary.csv` records that the selected method has the lowest mean error across
deployments and the mean of deployment-specific median errors is 219.398 m.
Do not revert to “pooled median” or “unique winner” language.

### Resolved B3. Markov and pause-transition outputs

The registered analysis uses 200 resamples that exclude ten deployments and
preserve ambiguous gaps. `results/dswp/buzz_markov_transitions.csv` and the figure
recover Start→B 0.54, A→A 0.55, B→B 0.42, A→End 0.06 and B→End 0.13 with the
reported uncertainties. The terminal-event denominator is frozen separately in
Resolved A4.

## C. Data-release and reproducibility obligations

### External release action 1. Obtain explicit steward approval for every derived release input

The DSWP derived inputs, reconstructed trajectories and CETI feature table are
currently marked `steward_review_required`.

**Pass condition.**

- Every public file has an approved status and checksum in `data/manifest.csv`.
- No raw audio, raw sensor stream, absolute position, original identifier,
  private path or crosswalk enters the public repository.
- `scripts/check_release_safety.py` passes in a clean clone.
- The private identifier crosswalk and export log remain outside the release.

### Resolved C2. Reproducibility boundary for map artwork

Main Fig. 1’s regional map and named representative track are not currently
generated by the public code, intentionally avoiding location-bearing data.

**Resolution.** The regional map is explicitly a presentation-only manuscript
asset. The repository reproduces the coordinate-free reconstruction summaries
and trajectory statistics from local-coordinate paths but does not distribute
the absolute location-bearing inputs or claim pixel-identical regeneration of
the map.

### Resolved C3. Manuscript–artifact crosswalk and version freeze

For every main and supplementary figure/table, record:

- manuscript label and exact numerical claims;
- generating script/notebook and version;
- approved input file and checksum;
- output artifact and checksum;
- tolerance used for numerical comparison.

**Resolution.** `docs/result_map.md` maps every reported analysis and panel to
its public input, implementation, output, and scope. The production freeze
records analysis commit `c144ae3` and manuscript commit `9e4ee80`; the
submission package adds SHA-256 manifests for exported artifacts. The archival
DOI is an external record and will be inserted after it is minted.

### Resolved C1. Bibliography warnings

`Tonnesen2020dataset` uses a style-compatible `@misc` entry and `Leitao_2025`
includes its journal. A fresh build produces no unsupported-entry or
missing-field warning for either record.

## Remaining execution order

1. Obtain and record steward and licence approvals.
2. Rerun the safety check after inserting the approved licence files.
3. Make the repository public, create the archival record, and add the DOI and
   final paper/preprint citation to `CITATION.cff`.
