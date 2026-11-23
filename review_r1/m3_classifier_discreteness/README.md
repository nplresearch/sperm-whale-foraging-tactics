# M3 — Classifier, continuum and discreteness (R1 point 3)

**Owner:** _unassigned_ **Status:** verified; one inherited SI error to fix.

## Claim
Two overlapping modes, not discrete classes: converged ΔBIC (k=2 vs 1) = −43; parametric
bootstrap p = 0.005 (floor 1/201); 28.7 % of buzzes have posterior < 0.75. k=3 ties k=2
(ΔBIC −2.0). The split survives without speed: κ 0.997 with measured vertical speed,
κ 0.82 (91 % agreement) with stroke effort — but **k=2 is not supported on ramp-up×stroke**
(ΔBIC +16, p 0.085).

## Inherited SI problem
`results/dswp/gmm_model_selection.csv` uses scikit-learn's default EM tolerance, which stops
before the two-component fits converge (reported ΔBIC −5.3). Converged fits give −43, and
"minimum at k=2" should read "k=2 and k=3 indistinguishable". Test: `test_converged_em_…`.

## Inputs / outputs
`results/dswp/buzz_events_labelled.csv`, `data/dswp/buzz_kinematics.csv` →
`classifier_kinematic_retest.csv`, `kinematics_summary.json` (`discreteness.*`).
Legacy script: `scripts/run_review_r1_kinematics.py` (sections B and discreteness).

## Run
```bash
pytest review_r1/m3_classifier_discreteness
python review_r1/m3_classifier_discreteness/run.py   # recompute: ~10 min (bootstraps)
```

## Known failure modes
- Features are quantile→Gaussian transformed, so each marginal is Gaussian by construction;
  the GMM only sees dependence. State this when reporting BIC.
- The "measured vertical speed" variant is nearly the registered axis (ρ 0.94): it is a
  consistency check, not an independent test. Only stroke effort is speed-free.
- Fig. 3d ("independent" vertical signature) restates the classifier axis: drop the wording.

## What would falsify it
Converged BIC preferring k=1 on registered features, or bootstrap p ≥ 0.05.
