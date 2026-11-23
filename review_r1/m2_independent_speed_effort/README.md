# M2 — Independent speed and effort (R1 point 2, "could Type A be fast?")

**Owner:** _unassigned_ **Status:** ⚠ speed contrast is **circular**; effort contrast is the real evidence.

## Claim (as drafted overnight)
"Type B swims 1.72× faster at matched body angle, direction and depth (AUC 0.84)."

## Why it does not stand (new analysis, `circularity.py`)
The A/B labels are built on ramp-up and *vertical speed* (alone: AUC 0.93 for the labels).
OCDR speed is `|vertical speed| / sin(pitch)`. Matching on pitch leaves a gap that the labels
imply. Controlling for log |vertical speed| as well:

| model (>=30°) | B/A | 95 % CI |
|---|---|---|
| pitch only (what was quoted) | 1.77 | 1.47–2.12 |
| pitch **and vertical speed** | **1.00** | 0.98–1.02 |

Inside quartiles of |vertical speed| the A and B medians coincide (e.g. 1.77 vs 1.71,
2.13 vs 1.94 m/s). Synthetic test: labels built on vertical speed alone reproduce the
draft's "finding" with zero true difference, and the control does not hide a real 1.5× one.

## What *is* independent
Stroke effort (0.1–0.4 Hz body-axis oscillation, from pitch+heading, no speed model):
Type A strokes at 0.83× its dive's bottom-phase level, B at 1.12× (20/20 whales);
near-horizontal B strokes 1.59× harder than A. A GMM on ramp-up + stroke effort
reproduces 91 % of labels (κ 0.82). Caveat: the band also picks up fast turns; stroke
vs OCDR speed ρ is only 0.12.

## Inputs / outputs
- In: `data/dswp/buzz_kinematics.csv` (steward-pending), `results/dswp/buzz_events_labelled.csv`.
- Out: `results/review_r1/speed_*.csv|json`, `stroke_*.csv`, `m2_circularity_*.csv`,
  `figures/speed_effort_profiles.png`.

## Run
```bash
pytest review_r1/m2_independent_speed_effort
python review_r1/m2_independent_speed_effort/circularity.py 30   # or 45
python review_r1/m2_independent_speed_effort/run.py              # legacy scripts
```

## Letter guidance
Do **not** quote the 1.72×, AUC 0.84 or "Type B accelerates into the buzz" (also vertical-speed
built). Lead with: valid OCDR exists for 4.5 % of Type A buzzes; stroke effort shows A is
low-effort. Real independent speed needs flow-noise or accelerometer-jiggle from raw DTAG data.

## What would falsify the circularity finding
A B/A ratio clearly ≠ 1 at matched vertical speed *in a dataset where labels are not built
from vertical speed* (e.g. a re-labelling using ramp-up and stroke only, then OCDR contrast).
