# Known release issues and manuscript checks

This file records discrepancies found while making the result-producing code
independent of the private analysis environment. Resolved items and explicit
production exceptions are retained here as provenance.

## Numbered active-issue index

No result-affecting manuscript issue remains active for the current production
freeze. The spatial-recurrence/comeback discrepancy is accepted as a documented
production exception: the manuscript-producing legacy calculation is retained
without being conflated with the registered-current sensitivity analysis.

Release-only tasks, including the CETI roll panel, steward approval, artifact
crosswalk and archival freeze, are numbered separately in
`submission_reconciliation.md`.

## Notebook touchpoint index

Decision-sensitive and historically discrepant choices are surfaced in the
notebooks that they can change:

- `dswp/00_dataset_and_buzz_construction.ipynb`: the boundary between derived
  click-time reproduction and unavailable raw-audio/full-record processing;
- `trajectory/02_manuscript_trajectory_figures.ipynb`: reconstruction-error
  provenance and location-bearing maps; the resolved L\'evy-fitting and legacy
  buzz-centred paths remain visible there as provenance and regression checks;
- `dswp/03_manuscript_figure_components.ipynb`: resolved classifier-speed,
  diagnostic-duration, DSWP Markov-resampling, and terminal-buzz provenance;
- `dswp/04_comeback_reproduction_audit.ipynb`: recurrence thresholds and
  legacy versus registered classifier labels;
- `validation/04_azores_manuscript_figures.ipynb`: final 28/28/two-tie labels,
  balanced sensitivity, full buzz-plus-margin echo window, nearest-range
  definition, and duplicate-preserving bootstrap intervals;
- `validation/05_ceti2024_manuscript_figures.ipynb`: unavailable per-bin roll
  time course and the reviewed trajectory-data gate; and
- `paper/00_manuscript_reproduction_status.ipynb`: paper-wide inventory of all
  these choices without selecting among unresolved alternatives.

Decision-sensitive notebooks retain the searchable phrase
`Known issue touchpoint`, with the text itself stating whether each decision is
active or resolved.

## Plateau-threshold null diagnostic (resolved)

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

The manuscript Methods and Supplementary Fig. S10 caption now report 0.7 as a
robust operating point rather than a unique numerical optimum. They state the
deterministic diagnostic values explicitly: excess regularity is 0.3027 at
alpha 0.70, or 99.2% of the maximum value of 0.3052 at alpha 0.55, while the
median plateau ICI CV at alpha 0.70 remains 0.12. The
dataset/buzz-construction notebook retains the full sensitivity diagnostic and
does not change the production boundaries.

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

## Classifier speed variable (resolved)

The reported GMM counts (A = 1,346; B = 1,142; unassigned = 1,198) are reproduced
using the original constant-speed reconstruction summary `avg_speed_3d_m_s`.
The manuscript Methods, main Fig. 2 caption and Supplementary Information now
identify this variable explicitly and distinguish it from the selected
pitch-adaptive speed, `pitch_adaptive_speed_3d_m_s`, used for the trajectory-
scale and energetic analyses.

The SI reports an otherwise identical GMM refit using pitch-adaptive speed. It
yields A = 1,350, B = 1,176 and unassigned = 1,160. Among the 2,417 events
confidently classified by both versions, 1,306 remain A and 1,111 remain B;
none switches directly between A and B. The differences are confined to the
posterior boundary: 71 primary confident events become unassigned and 109
primary unassigned events become confident under the pitch-adaptive refit.

The repository retains the original result-producing classifier as the default,
exports `results/dswp/classifier_speed_sensitivity.json`, and regression-tests
both counts and boundary movements. Downstream manuscript values continue to
use the original classifier. This item is resolved as a transparent provenance
choice supported by an explicit reconstruction-sensitivity analysis.

## “Total duration” diagnostic feature (resolved for the manuscript)

The source model-selection notebook defines its third diagnostic feature as
`duration_start + duration_plateau` but labels it “total duration.” The
released event table separately contains the full first-click--last-click buzz
duration and the terminal-segment duration. The public model-selection
function follows the operative notebook definition exactly and names the
derived feature `ramp_plus_plateau_duration_s`.

This does not affect the main A/B classifier, which uses ramp-up duration and
3-D speed. It also does not affect the manuscript's five-feature analysis in
Supplementary Fig. S11. That figure uses the genuine full `buzz_duration_s`,
despite the similarly named repository-side diagnostic. We verified this by
recomputing every duration-related Spearman coefficient printed in S11 using
the released confidently classified A/B events. Full `buzz_duration_s`
reproduces all 12 displayed pooled, Type A and Type B coefficients after
rounding to the reported two decimal places; ramp-up plus plateau duration
reproduces only one of the 12.

For example, the displayed ramp-up/duration correlations are 0.90 pooled,
0.75 for Type A and 0.87 for Type B. Full buzz duration reproduces
0.90/0.75/0.87, whereas ramp-up plus plateau gives 0.91/0.77/0.90. The
displayed Type B roll/duration correlation is 0.12, reproduced by full buzz
duration rather than the 0.09 obtained from ramp-up plus plateau.

Therefore the S11 axes, caption, Results, Methods and Discussion correctly use
“total buzz duration” and require no change. The naming discrepancy is confined
to the separate repository-side BIC diagnostic, which is not reported or
plotted in the active manuscript. This manuscript-facing item is resolved;
the explicit `ramp_plus_plateau_duration_s` name should be retained in the
public diagnostic code and outputs to prevent the two quantities from being
conflated again.

## Available reconstructed trajectories

The internal dive table contains 245 dive records, but 17 have no available
pitch-adaptive reconstructed path. The release therefore contains 228
trajectories. After the stated depth, segment-length, and turning-point filters,
209 dives from 20 individuals enter the trajectory-scale analysis, matching the
manuscript.

## Reconstruction-error wording (resolved)

The safe reconstruction-error table reproduces the four method comparisons
from 20 anonymous deployments. For the selected pitch-adaptive method, the
reported 219 m value is the **mean of the 20 deployment-level median errors**
(219.398 m). It is not the pooled median distance between all GPS references
and the reconstructed path. The latter cannot be recovered from the released
deployment summaries.

The pitch-adaptive method has the smallest mean of deployment-level mean
errors (339.0 m versus 351.3 m for constant speed). It is tied with the
constant-speed method for most deployment-level wins (eight each), rather than
being uniquely most frequently best. The Results and figure caption now name
the aggregation explicitly and record the eight--eight tie rather than claiming
a unique winner. Vessel positions remain a broad, conservatively interpreted
reference rather than pointwise whale ground truth.

## Roll-rate units

The legacy per-buzz summary stored mean absolute roll increment per 25-Hz
sample while some figures labelled the value as degrees per second. The release
converts that summary by the 25-Hz sampling rate and exposes
`avg_roll_speed_deg_s`. The 2-s time-course table was recomputed directly as a
time derivative and is also expressed in degrees per second.

## Spatial-recurrence definition and classifier version (accepted production exception)

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

The coherent alternatives are:

1. register the current classifier and a single recurrence definition, rerun
   all comeback numbers and figures, and update the SI; or
2. explicitly freeze the legacy label/recurrence calculation as exploratory,
   describe its actual parameters, and explain why it differs from the main
   classifier.

For the 2026-08-25 production freeze, the author elected not to rerun or rewrite
this exploratory null result. The manuscript-producing legacy calculation is
therefore retained as the frozen paper value, while the registered-current
calculation remains a labelled sensitivity analysis. This is an explicit
provenance exception, not evidence that the two definitions are equivalent.
The repository retains both association outputs, and the legacy labels remain
in a separate, clearly named table solely to reproduce the current manuscript
figure.

## Markov graph: gaps and resampling unit (resolved in the manuscript)

The published graph is exactly recovered only when ambiguous buzzes remain in
the ordered sequence as gaps. Transitions touching an ambiguous event are
discarded after counting, so an `A--?--B` run does not become an `A→B`
transition. This gives the reported point probabilities, including
Start→A/B of approximately 0.46/0.54 and A/B→End of approximately 0.06/0.13.

The result-producing notebook computes 200 leave-subset-out resamples after
removing ten `tag_id` values (deployments) per iteration. An earlier Methods
draft instead stated that 5--10 individuals were excluded; these procedures are
not equivalent because deployments and individuals have different sampling
weights. The current manuscript now follows the figure-producing procedure: it
states that ten deployments are excluded in each of 200 iterations and that
ambiguous events are preserved as gaps. The repository uses this deployment-
level procedure as the figure-reproduction default and retains the grouping and
exclusion range as explicit arguments for sensitivity analyses. Before public
release, commit this implementation and its frozen Markov outputs together.

## Terminal-buzz count (resolved in the manuscript)

The apparent 36-versus-32 discrepancy was caused by applying the classifier
confidence filter to the terminal events, not by a difference in terminal-event
identification. The released table contains 36 buzzes with missing
`post_buzz_pause_s`: under the registered current classifier, 29 are Type B, 3
are Type A, and 4 are unassigned. Thus, 36 is the total number of terminal
events and 32 is the confidently classified subset. This is shown explicitly
in `notebooks/dswp/01_event_level_analysis.ipynb`, under “Terminal-buzz count
and classifier status.”

The Results were updated to read:

> Final buzzes (those not followed by any further echolocation before
> surfacing) were first identified and excluded from pause analysis; of the 36
> terminal events, 29 were confidently identified as Type B and only 3 as Type
> A, which is itself strongly consistent with the Markov termination asymmetry
> (expected ratio under the null hypothesis of equal termination probabilities:
> $\sim$0.5; observed: $0.91$; binomial $P < 0.001$).

The archived source analysis in
`unversioned-old-repo/notebooks/buzz_pauses_CLEAN.ipynb` independently derives
36 missing “next-echolocation time” values from 3,686 buzzes. It is therefore
consistent with the updated notebook on terminal-event identification and the
total of 36. Its markdown annotation of 32 Type B and 4 Type A reflects an
older, unpreserved classifier assignment; the registered current classifier
provides the reproducible 29 Type B, 3 Type A, and 4 unassigned breakdown used
for the manuscript correction. The pause-distribution analyses and figure
panels are unchanged because all terminal events were already excluded.

## Azores validation (resolved)

The four authoritative CC0 MATLAB files are pinned by Dryad version-1 file
IDs, byte sizes, SHA-256 digests, and expected variables. The publication-safe
implementation in `validation.azores` validates those local inputs and ports
the final analysis in Andrea Santoro's `CETI_Foraging` commit `a74bab4`. It
exports only derived event summaries and aggregate results; the MATLAB files
remain outside this repository.

The reproduced inputs and outputs are:

- 27 dives, 108 buzzes, and the stated 11-dive/58-buzz daytime subset;
- the final nearest-corner labels: 28 Type A, 28 Type B, and two unclassified
  buzzes exactly equidistant from the lower-left and upper-right corners;
- prey echo count: P = 0.0368 and Cohen's d = 0.363; mean prey depth:
  P = 0.00410 and d = 1.343; nearest range: P = 0.972;
- the reported robustness values, including continuous rank correlations of
  rho = -0.221 (P = 0.0948) for echo count and rho = -0.456 (P = 0.00516)
  for prey depth;
- pre-buzz signed vertical speed of +0.224 m/s for A and -0.290 m/s for B
  (P = 0.0204), pause chi-square = 1.02 (P = 0.796), and 50%/61%
  A/B oscillatory/persistent geometry; and
- the point Markov probabilities and 95% intervals from 2,000 bootstrap
  replicates that resample an ordered list of dives, retaining duplicate draws.

The manuscript now describes the echo window exactly as implemented: from
10 s before buzz onset through 10 s after buzz end. Nearest range is the
minimum detected prey range over this same full interval. The main-text and SI
statistics use the final 28/28 labels and corrected bootstrap figure.

The original folder also contains `azores_analysis.py`, a legacy whole-record
analysis with hard-coded 35/35 labels, and a stale tracked
`figure_extended.pdf`. Neither is a manuscript-producing source. Executing the
updated `azores_extended.py` from commit `a74bab4` regenerates a figure that is
pixel-identical to the current Overleaf SI asset. The production implementation
and registered results in this repository are the release-facing source of
truth.

## L\'evy fitter named in Methods (resolved)

The reported step-length exponents are reproduced by the result-producing
custom implementation: a continuous maximum-likelihood exponent is evaluated
at 30 candidate lower cutoffs spanning the 5th--80th percentiles, and the
cutoff minimizing the Kolmogorov--Smirnov distance is selected.

The current Methods now describe this custom 30-candidate sweep directly and
retain the cautious term “L\'evy-like,” without claiming a unique or optimal
search rule or adding a lognormal-versus-power-law claim. The Python `powerlaw`
package is no longer presented as the operative fitter. This item is resolved;
the clean output-and-figure freeze remains a release task in
`submission_reconciliation.md`.

## Buzz-centred displacement time origin and labels (resolved)

The former manuscript-producing Lévy notebook subtracted `dive_start` from each
buzz click time before indexing a dive-local trajectory. The buzz times were
already dive-local. This second subtraction made most later dives negative and
dropped them at the `+-30 s` boundary check. Combined with the archived A/B
labels, the buggy path left eight whales and reproduced the saved
all-nonsignificant Wilcoxon table used by the previous SI.

Using the released dive-local buzz time directly while retaining the archived
labels keeps 19 whales and gives P values below 0.001 at every tested positive
lag. Reapplying the registered current GMM keeps 20 whales and gives the same
qualitative result. This isolates the time-origin error, rather than the label
version, as the cause of the archived null result. It was incompatible with the
previous statement that buzz-centred MSD did not distinguish tactics.

The manuscript-facing analysis now uses `dive_local` with the registered GMM.
It retains 20 whales and 1,346 Type A plus 1,141 Type B complete `+-30 s`
windows. Type B onset-referenced squared displacement exceeds Type A at all
eight tested positive lags from 0.04 to 30 s; all paired Wilcoxon tests remain
below 0.001 after Bonferroni correction. The result is interpreted as a
trajectory-scale expression of the established speed contrast, not as an
independent validation because buzz-period speed contributes to classification.

`legacy_subtract_dive_start` remains an explicitly named forensic mode, and the
regression test preserves the archived eight-whale P values to document the
error. It must not be used to generate manuscript figures or scientific claims.
This item is resolved.
