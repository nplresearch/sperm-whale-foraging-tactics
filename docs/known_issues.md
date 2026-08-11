# Known release issues and manuscript checks

This file records discrepancies found while making the result-producing code
independent of the private analysis environment. They should be resolved
explicitly before the repository and manuscript are released together.

## Notebook touchpoint index

Unresolved choices are surfaced in the notebooks that they can change:

- `dswp/00_dataset_and_buzz_construction.ipynb`: the boundary between derived
  click-time reproduction and unavailable raw-audio/full-record processing;
- `trajectory/02_manuscript_trajectory_figures.ipynb`: reconstruction-error
  wording, location-bearing maps, the named Levy-like fitter, and the legacy
  buzz-centred time-origin/classifier path;
- `dswp/03_manuscript_figure_components.ipynb`: classifier speed, diagnostic
  duration, DSWP Markov resampling, and terminal-buzz denominator;
- `dswp/04_comeback_reproduction_audit.ipynb`: recurrence thresholds and
  legacy versus registered classifier labels;
- `validation/04_azores_manuscript_figures.ipynb`: 29/28/1 operative labels,
  balanced sensitivity, echo window, nearest-range definition, and corrected
  bootstrap intervals;
- `validation/05_ceti2024_manuscript_figures.ipynb`: unavailable per-bin roll
  time course and the reviewed trajectory-data gate; and
- `paper/00_manuscript_reproduction_status.ipynb`: paper-wide inventory of all
  these choices without selecting among unresolved alternatives.

Every affected notebook uses the phrase `Known issue touchpoint` so these
dependencies can be found mechanically before release.

## Plateau-threshold null diagnostic

The released click times reproduce the operative 0.3-s symmetric rate window,
0.05-s step, five-point smoothing, and 0.05--0.95 threshold sweep. At the
chosen alpha of 0.7, the median plateau ICI CV is 0.1198, matching the SI's
reported 0.12.

The null-window claim is less exact. With 20 uniformly sampled same-duration
windows per buzz and a recorded seed of 42, median excess regularity is 0.3052
at alpha 0.55 and 0.3027 at alpha 0.70. Thus 0.7 lies on a broad near-maximum,
but is not the numerical peak of this deterministic implementation. The source
tree contains no preserved threshold-figure code or random seed that explains
a unique 0.7 maximum. The derivative criterion is likewise descriptive rather
than a registered change-point rule.

The SI should report 0.7 as a robust, preselected operating point rather than a
unique optimum, or archive the exact randomization and formal selection rule
used for the plotted claim. The dataset/buzz-construction notebook keeps this
diagnostic visible and does not change the production boundaries.

## Energetic-model alignment (resolved)

The public trajectory data and the operative implementation in
`src/dswp/energetics.py` reproduce the reported across-individual means:

- Type A: 1.275 MJ, reported as 1.28 MJ;
- Type B: 9.069 MJ, reported as 9.07 MJ.

Those values are obtained from:

1. pitch-adaptive reconstructed positions sampled at 25 Hz;
2. the full first-click--last-click buzz interval, with both boundaries mapped
   to the preceding trajectory sample;
3. parasite-drag work plus positive tangential-acceleration work;
4. body mass 40,000 kg, body length 12 m, skull width 1.5 m, and added-mass
   coefficient 0.06; and
5. within-individual A/B means, followed by the mean across 20 individuals.

The current Methods and Supplementary Information now describe this operative
trajectory-driven model directly. They identify Goldbogen et al. (2019) as a
source for the hydrodynamic framework without presenting the calculation as a
fitted analytical prey-interception model. The equations, event interval,
parameters, within-individual aggregation, component values, and reported
1.28/9.07 MJ means are aligned with `src/dswp/energetics.py` and the registered
outputs.

The Aoki et al. (2012) steady-drag calculation is retained as additional
evidence in the same direction. Applied to the same reconstructed speed series
and buzz intervals, it gives 0.013 MJ for Type A and 0.111 MJ for Type B
(B/A = 8.51), with Type B higher in all 20 whales. It is not used as a
quantitative calibration of the primary energetic estimates.

This item is resolved. Future edits should preserve the current distinction
between the manuscript's trajectory-driven model and the cited source
frameworks.

## Classifier speed variable

The reported GMM counts (A = 1,346; B = 1,142; ambiguous = 1,198) are reproduced
using the original constant-speed reconstruction summary
`avg_speed_3d_m_s`. The selected pitch-adaptive speed is released separately as
`pitch_adaptive_speed_3d_m_s`. Switching the classifier to the latter leaves
the classified A/B contrast unchanged for shared confident cases but changes
which observations fall near the posterior-probability boundary.

The Methods should state which speed is used for classification, or the
classifier should be rerun on pitch-adaptive speed and its counts and downstream
figures updated. The repository keeps the published-count implementation as the
default and names both variables explicitly.

## “Total duration” diagnostic feature

The source model-selection notebook defines its third diagnostic feature as
`duration_start + duration_plateau` but labels it “total duration.” The
released event table separately contains the full first-click--last-click buzz
duration and the terminal-segment duration. The public model-selection
function follows the operative notebook definition exactly and names the
derived feature `ramp_plus_plateau_duration_s`.

This does not affect the main A/B classifier, which uses ramp-up duration and
3-D speed. Nevertheless, any Methods or SI caption discussing the five-feature
pair plot should either call this quantity ramp-plus-plateau duration or change
the code deliberately to use the full buzz duration and regenerate that
diagnostic.

## Available reconstructed trajectories

The internal dive table contains 245 dive records, but 17 have no available
pitch-adaptive reconstructed path. The release therefore contains 228
trajectories. After the stated depth, segment-length, and turning-point filters,
209 dives from 20 individuals enter the trajectory-scale analysis, matching the
manuscript.

## Reconstruction-error wording

The safe reconstruction-error table reproduces the four method comparisons
from 20 anonymous deployments. For the selected pitch-adaptive method, the
reported 219 m value is the **mean of the 20 deployment-level median errors**
(219.398 m). It is not the pooled median distance between all GPS references
and the reconstructed path. The latter cannot be recovered from the released
deployment summaries.

The pitch-adaptive method has the smallest mean of deployment-level mean
errors (339.0 m versus 351.3 m for constant speed). It is tied with the
constant-speed method for most deployment-level wins (eight each), rather than
being uniquely most frequently best. The Results and figure caption should
name the aggregation explicitly and avoid the current pooled-median and unique
winner wording. Vessel positions remain a broad, conservatively interpreted
reference rather than pointwise whale ground truth.

## Roll-rate units

The legacy per-buzz summary stored mean absolute roll increment per 25-Hz
sample while some figures labelled the value as degrees per second. The release
converts that summary by the 25-Hz sampling rate and exposes
`avg_roll_speed_deg_s`. The 2-s time-course table was recomputed directly as a
time derivative and is also expressed in degrees per second.

## Spatial-recurrence definition and classifier version

The current manuscript reports the comeback association as 18 deployments,
1,691 classified buzzes, pooled OR 1.11 (95% CI 0.78--1.59), P = 0.56, with
heterogeneous odds ratios (P = 0.041). The public pipeline reproduces those
numbers exactly, but the audit shows that they combine choices not stated
consistently in the SI:

- the result-producing recurrence notebook uses the 20-s subsampled
  constant-speed deployment reconstruction, three-dimensional distances,
  `close = 50 m`, and `far = 150 m`;
- the SI describes horizontal distances, `close = 10 m`, and `far = 50 m`;
- the forest plot uses an older saved GMM-label table (A = 1,281, B = 1,046,
  uncertain = 1,359), not the registered classifier used elsewhere in the
  current paper (A = 1,346, B = 1,142, uncertain = 1,198); and
- the approximately 1--30% comeback-ratio range in the SI comes from an older
  recurrence configuration, whereas the result-producing forest-plot
  configuration yields 0--11.1% across available deployment reconstructions.

Applying the registered current labels to the exact same recurrence context
gives 18 deployments and 1,660 buzzes, pooled OR 1.151 (95% CI 0.807--1.642),
P = 0.433, with homogeneity P = 0.096. The biological conclusion remains null,
but the numerical provenance is not interchangeable.

Before submission, choose and document one coherent analysis:

1. register the current classifier and a single recurrence definition, rerun
   all comeback numbers and figures, and update the SI; or
2. explicitly freeze the legacy label/recurrence calculation as exploratory,
   describe its actual parameters, and explain why it differs from the main
   classifier.

The repository retains both association outputs. The legacy labels are kept in
a separate, clearly named table solely for forensic reproduction of the
current manuscript figure.

## Markov graph: gaps and resampling unit

The published graph is exactly recovered only when ambiguous buzzes remain in
the ordered sequence as gaps. Transitions touching an ambiguous event are
discarded after counting, so an `A--?--B` run does not become an `A→B`
transition. This gives the reported point probabilities, including
Start→A/B of approximately 0.46/0.54 and A/B→End of approximately 0.06/0.13.

The result-producing notebook computes 200 leave-subset-out resamples after
removing ten `tag_id` values (deployments) per iteration. The current Methods
instead state that 5--10 individuals are excluded. These are not equivalent.
The repository implements the notebook procedure as the figure-reproduction
default and exposes the grouping and exclusion range as arguments. Before
release, either:

1. revise the Methods to say ten deployments and retain the current figure; or
2. select and preregister an individual-level procedure, regenerate the graph,
   and update every reported standard deviation.

## Terminal-buzz count

With the registered current classifier, missing post-buzz-pause values identify
32 terminal events in the released table: 29 Type B and 3 Type A. The current
Results instead state 36 terminal events (32 Type B and 4 Type A). The
result-producing pause notebook does not contain a separate terminal-event
derivation that explains this difference.

Before release, recover the precise vocal-phase termination rule used for the
36-event statement or align the prose and binomial calculation to the released
event table. This should not be justified from the Markov end-transition
counts: those are a different sequence-level quantity and are affected by
ambiguous labels.

## Azores validation: reproduced, with manuscript corrections required

The four authoritative CC0 MATLAB files are pinned by Dryad version-1 file
IDs, byte sizes, SHA-256 digests, and expected variables. The publication-safe
implementation in `validation.azores` validates those local inputs and
reproduces the numerical path of the supplied production scripts. It exports
only derived event summaries and aggregate results; the MATLAB files remain
outside this repository.

The reproduced inputs and outputs are:

- 27 dives, 108 buzzes, and the stated 11-dive/58-buzz daytime subset;
- the operative nearest-corner labels: 29 Type A, 28 Type B, and one
  unclassified buzz; the independent 29-nearest A and 29-nearest B selections
  overlap once, and the scripts give that event A precedence;
- prey echo count: P = 0.0366 and Cohen's d = 0.345; mean prey depth:
  P = 0.00282 and d = 1.387; nearest range: P = 1.000;
- the reported robustness values, including continuous rank correlations of
  rho = -0.221 (P = 0.0948) for echo count and rho = -0.456 (P = 0.00516)
  for prey depth;
- pre-buzz signed vertical speed of +0.253 m/s for A and -0.290 m/s for B
  (P = 0.0143), pause chi-square = 1.07 (P = 0.784), and 48%/61%
  A/B oscillatory/persistent geometry; and
- the current point Markov probabilities. The public bootstrap now resamples
  an ordered list of dives so duplicate draws are retained, correcting a bug
  in `azores_extended.py`, which converted each resample to a dictionary and
  discarded duplicates before calculating confidence intervals.

The following manuscript discrepancies remain and should not be glossed over:

1. The text and captions call the primary analysis a balanced 29/29 partition
   of all 58 buzzes. The operative code and its reported P values use
   29 A/28 B/1 unclassified. A genuinely disjoint, globally balanced 29/29
   assignment is exported as a sensitivity: prey-count P = 0.0313, depth
   P = 0.0130 and d = 1.160, and nearest-range P = 0.833. It is not the
   manuscript's result-producing analysis.
2. The code defines the echo window as `buzz start - 10 s` through `buzz end +
   10 s`, whereas the manuscript says a window around buzz onset. Likewise,
   nearest range is the minimum over that full window, not necessarily the
   range at buzz start. Either revise the prose to match the operative
   calculation or deliberately change and rerun it.
3. The supplementary Markov point estimates are reproduced, but the published
   bootstrap intervals came from the duplicate-dropping implementation. The
   figure and caption should be regenerated from the corrected resampling
   procedure before treating its confidence intervals as reported values.
4. `azores_analysis.py` is a legacy whole-record analysis with hard-coded
   35/35 labels spanning the 108-buzz, 27-dive record. It is not the
   manuscript's 11-dive analysis and should not be used as its production
   entry point.
5. The robustness comment in `azores_extended.py` says that 20, 30, and 35
   events per corner are tested, whereas the executable loop uses 20, 25, and
   29. The public result table records the values actually run by the code.

## Lévy fitter named in Methods

The reported step-length exponents are reproduced by the result-producing
custom implementation: a continuous maximum-likelihood exponent is evaluated
at 30 candidate lower cutoffs spanning the 5th--80th percentiles, and the
cutoff minimizing the Kolmogorov--Smirnov distance is selected. The current
Methods instead say that fitting used the Python `powerlaw` package. That
package's unrestricted cutoff search is not the operative implementation and
need not return identical values.

Retain the cautious term “Lévy-like,” as intended, but either describe the
actual 30-candidate implementation in Methods or rerun the analysis with a
pinned `powerlaw` version and update the numerical results. No additional
lognormal-versus-power-law claim is required.

## Buzz-centred MSD time origin and labels

The manuscript-producing Lévy notebook subtracts `dive_start` from each buzz
click time before indexing a dive-local trajectory. The buzz times are already
dive-local. This second subtraction makes most later dives negative and drops
them at the `+-30 s` boundary check. Combined with the archived A/B labels, the
buggy path leaves eight whales and reproduces the saved all-nonsignificant
Wilcoxon table used by the current SI.

Using the released dive-local buzz time directly while retaining the archived
labels keeps 19 whales and gives P values below 0.001 at every tested positive
lag. Reapplying the registered current GMM keeps 20 whales and gives the same
qualitative result. This isolates the time-origin error, rather than the label
version, as the cause of the archived null result and is incompatible with the
current statement that buzz-centred MSD does not distinguish tactics.

`trajectory.manuscript.buzz_centred_results` therefore exposes two named paths:
`dive_local` is the corrected default, while `legacy_subtract_dive_start` is a
forensic reproduction mode. Before submission, the buzz-centred analysis and
claim should be rerun with the corrected time origin and one explicitly chosen
classifier version; the legacy null result should not be presented as a
robustness check of the registered analysis.
