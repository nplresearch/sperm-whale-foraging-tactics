# M1 — How much of the speed series is measured? (R1 point 2)

**Owner:** _unassigned_ **Status:** verified.

## Claim
R1 is right that speed is largely assumed. In foraging-phase steps 91 % use the 0.9 m/s
fallback; 71 % of Type A buzzes contain **no** measured-speed step at all (2.5 % of Type B).
The 5 m/s cap barely matters (Type B median 1.53 → 1.55). R1 misread one detail:
the depth gate is 0.05 m *per 25-Hz sample* (a 1.25 m/s vertical-speed gate).

## Method
`src/dswp/speed_regimes.py` inverts the released hybrid reconstruction exactly from
positions: |Δz| < 0.05 m → fallback, otherwise depth-derived, >5 m/s → clipped.

## Inputs / outputs
- In: `data/dswp/trajectories/T*.npz`, `results/dswp/buzz_energy.csv`.
- Out: `results/review_r1/summary.json`, `speed_regime_by_type.csv`, `speed_regime_events.csv`,
  `energy_variants_*.csv` (shared with M4).
- Legacy script: `scripts/run_review_r1_diagnostics.py`.

## Run
```bash
pytest review_r1/m1_speed_regimes review_r1/test_claims.py -k "M1 or m1"
python review_r1/m1_speed_regimes/run.py      # recompute (backs up results first)
```

## Known failure modes
- 4,812 steps (0.03 %) with pitch < 0.05 rad and |Δz| ≥ 0.05 m cannot be classified from
  positions; they are labelled depth-derived.
- The inversion is only valid for the *released* reconstruction. If the tracks are
  regenerated with other settings (smoothing, thresholds) the classification is wrong.

## What would falsify it
A fallback step with horizontal speed > 0.9 m/s (currently 0; asserted by test and claim).
