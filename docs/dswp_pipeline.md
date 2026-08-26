# Primary DSWP analysis

## Analytical starting point

The public pipeline starts from `data/dswp/buzz_events.csv` and the
pitch-adaptive reconstructions indexed by
`data/dswp/trajectory_index.csv`. These are derived, pseudonymized products;
the repository contains no code path that loads tag archives, audio, GPS fixes,
or opaque pickles.

## Spatial recurrence

The comeback calculation uses a separate coarse, deployment-scale
reconstruction input because recurrence can cross dive boundaries. The public
module:

1. identifies return points in the 20-s local-coordinate reconstruction;
2. groups return samples separated by at most 120 s into events;
3. retains events deeper than 200 m for the tactic association;
4. flags buzz starts within 120 s of those event intervals; and
5. applies a deployment-stratified Cochran--Mantel--Haenszel test.

The pipeline writes the result from the manuscript label table and a separate
current-classifier sensitivity. The manuscript calculation uses the documented
3-D 50/150-m return rule and reproduces the reported odds ratio.

The file-level schema and provenance are documented in
`data/dswp/README.md`. The release boundary is enforced by
`scripts/check_release_safety.py`.

## Tactic classification

`dswp.classification.classify_gmm` implements the paper classifier:

1. retain buzzes with a ramp-up duration and classifier 3-D speed;
2. quantile-transform both variables to normal marginals using all complete
   observations as quantiles;
3. fit a two-component, full-covariance Gaussian mixture with ten starts and
   random seed 1234;
4. name the higher-speed component Type B and the other Type A; and
5. label posterior probabilities below 0.75 as ambiguous.

The SI component-selection calculation is also reproduced from the released
features. `gmm_model_selection` quantile-transforms each of the three source
notebook feature pairs, fits full-covariance mixtures for `k=1,...,8` with ten
restarts, and writes BIC/AIC values to
`results/dswp/gmm_model_selection.csv`. The manuscript's model-selection claim
concerns the ramp-up-duration/3-D-speed plane, whose minimum is at `k=2`.
Max-click-rate/roll also selects `k=2`, whereas the diagnostic
ramp-plus-plateau-duration/median-click-rate pair selects `k=3`. The latter is
called “total duration” in the source notebook even though it excludes the
terminal segment. The regenerated figure marks each curve's actual optimum
rather than hard-coding `k=2`.

The threshold-free robustness comparisons are implemented separately from the
posterior-thresholded primary classifier. On the 3,488 buzzes with complete
features they reproduce the SI agreements: GMM 3-D versus GMM vertical speed
95.3% (`κ=0.905`), versus the 3-D extreme-corner rule 97.8% (`κ=0.956`), and
versus the vertical-speed extreme-corner rule 94.5% (`κ=0.890`). Tables and
confusion counts are written to `classifier_robustness*.csv`.

The released input regenerates 1,346 Type A, 1,142 Type B, and 1,198 ambiguous
events. Ambiguous events remain in the released table and are excluded only
from analyses explicitly comparing A and B.

The classifier variable is the original constant-speed summary, as stated in
the Methods and retained to reproduce the reported counts. The selected
pitch-adaptive speed is a separate column used for trajectory-derived analyses.

## Event contrasts and sequences

`dswp.statistics` provides two-sided Mann--Whitney tests and Cliff's delta for
derived event metrics. The registered depth analysis fits
`depth ~ is_A` by REML with random intercepts for individual and nested dive,
reproducing the reported A-minus-B estimate and interval. The roll time-course
analysis applies independent t-tests within each 2-s bin and Bonferroni
correction across all tested bins.

`markov_leave_subset_out` reproduces the published
transition figure. It orders events within each dive, adds Start and End
states, counts transitions with ambiguous events retained as explicit gaps,
then removes edges touching an ambiguous event before row normalization. It
runs 200 deterministic leave-subset-out resamples, excluding ten deployments
per iteration, and reports the mean and standard deviation.

That implementation follows the result-producing notebook and the Methods and
recovers the displayed Start and End probabilities. For an additional
sensitivity analysis, `markov_with_ci` filters to confident labels and
resamples whole dives to provide percentile intervals. Its output is written
separately and is not presented as the source of the paper graph.

## Straightness and vertical geometry

`dswp.trajectory_features` calculates straightness from the released
pitch-adaptive trajectories:

- cumulative 3-D path length is calculated for each dive;
- before windows end at first-click time;
- after windows begin at last-click time;
- 20, 30, and 40 m path-distance windows are extracted; and
- each window is spatially resampled at 1 m before calculating displacement
  divided by path length.

The regenerated 20 m post-buzz comparison is non-significant (`P = 0.40`),
matching the figure caption. Signed pre/post depth slopes in `buzz_events.csv`
support the four vertical-geometry categories without distributing depth
traces.

## Pauses and comeback

The post-buzz pause is the interval from the last click to the next derived
echolocation event. `dswp.pauses` applies the registered categories:

- short: <1.3 s;
- medium: 1.3 to <3.4 s;
- long: 3.4 to 6.0 s; and
- very long: >6.0 s.

Terminal events without a following echolocation have missing pause values.
Comeback indicators are already derived binary fields and can be summarized
by the regenerated labels; no absolute trajectory or raw field location is
needed.

## Energetics

`dswp.energetics.event_energy_from_trajectories` reconstructs instantaneous
speed from the released pitch-adaptive positions and reproduces the reported
across-individual means: 1.28 MJ for Type A and 9.07 MJ for Type B. Its full
first-click--last-click window, preceding-sample alignment, force components,
parameters, and within-individual aggregation match the current Methods and
SI. The model is trajectory-driven and inspired by the Goldbogen hydrodynamic
framework; it is not presented as the analytical prey-interception model.

`dswp.aoki` applies the published Aoki et al. (2012) steady-drag formulation to
the same observed speed series and intervals. It is retained as additional
directional evidence: it assigns different absolute costs but preserves a
large Type-B/Type-A contrast and Type B above Type A in every whale.

## Derived acoustic and roll time series

`buzz_clicks.csv` provides detector event times relative to buzz onset, making
click-rate and plateau sensitivities possible without audio. The
`roll_speed_bins.csv` file provides the 2-s mean-rate values used by the
buzz-centred panel without releasing the source orientation stream.

## Run

From the repository root:

```bash
python scripts/run_pipeline.py
```

The runner validates inputs, recomputes labels, event contrasts, Markov
transitions, straightness, energetics, trajectory-scale results, and CETI
validation outputs. Numerical results are written under `results/`; figures
are written under `figures/`.

Primary machine-readable outputs also include
`depth_mixed_model.json`, `roll_speed_bin_tests.csv`,
`pause_distribution_tests.json`, the paper-aligned
`buzz_markov_transitions.csv`, and a separate
`buzz_markov_dive_bootstrap.csv` robustness table. The safe
deployment-level GPS-distance comparison is summarized in
`reconstruction_method_summary.csv` and plotted as
`reconstruction_error_summary.{pdf,png}`.
