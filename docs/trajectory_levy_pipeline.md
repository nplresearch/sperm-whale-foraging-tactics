# Reconstructed trajectories and Lévy-like movement

## Public input

The trajectory workflow reads `data/dswp/trajectory_index.csv` and numeric-only
`data/dswp/trajectories/T###.npz` files. Each path is a pitch-adaptive
dead-reckoning reconstruction in local metres. The horizontal origin is reset
per dive; positive `z` is depth. No raw sensor, GPS, absolute position, date,
name, or source identifier is present.

The upstream reconstructions were built internally from the restricted tag
data, beginning with `notebooks/00_save_3d_reconstructions.ipynb`. That
raw-to-derived stage and its private storage are provenance, not part of the
public executable workflow.

## Registered production choices

`trajectory.analysis.analyze_release` preserves the exact choices used to
generate the manuscript values:

- selected reconstruction: pitch-adaptive/hybrid;
- sampling rate: 25 Hz;
- dive maximum-depth threshold: 600 m;
- foraging segment: released start/end indices;
- minimum segment length: 50 samples;
- turning threshold: 30 degrees;
- endpoints: not added as artificial turning points;
- minimum steps/tail observations: 30;
- `xmin` scan: 30 candidates from the 5th to 80th step-length percentiles;
- exponent: continuous MLE with the cutoff minimizing the KS distance;
- global MSD: 50 logarithmically spaced lags up to 40% of the segment; and
- multiscale MSD: longest whole-dive non-surface run, lags up to 50% of that
  run, in <=1, 1--5, 5--15, and >=15 minute windows.

## Regenerated values

The release regenerates:

| quantity | value |
| --- | ---: |
| eligible dives | 209 |
| pseudonymous individuals | 20 |
| median per-dive step exponent, `mu` | 2.354 |
| median of individual-level `mu` medians | 2.364 |
| pooled step exponent, `mu` | 2.155 |
| median global MSD exponent, `alpha` | 1.909 |
| median `alpha`, <=1 min | 1.979 |
| median `alpha`, 1--5 min | 1.745 |
| median `alpha`, 5--15 min | 1.522 |

All 209 global per-dive MSD exponents exceed one.

## Interpretation

These statistics justify the deliberately qualified term **Lévy-like**:
heavy-tailed step lengths coexist with superdiffusive, directionally
persistent movement. They do not prove that a unique power-law mechanism
generates the paths, that the whales implement an optimal Lévy rule, or that
environmental heterogeneity and state mixtures can be excluded.

The public implementation therefore reports the fit, cutoff, KS distance, tail
count, MSD slope, lag range, and reconstruction provenance. It does not add a
new omnibus lognormal-vs-power-law claim that was not used for the paper.

## Precision

The trajectory arrays remain float64. Casting them to float32 changed a small
number of 30-degree threshold decisions and caused material changes in a few
per-dive exponents, even though aggregate medians changed little. Exact
reproduction takes precedence over reducing the derived bundle by roughly
half.

## Outputs

The full pipeline writes:

- `results/trajectory/per_dive_levy_msd.csv`;
- `results/trajectory/timescale_msd.csv`; and
- `results/trajectory/population_summary.json`.

Tests compare the regenerated aggregates to the registered values above with
tight numerical tolerances.
