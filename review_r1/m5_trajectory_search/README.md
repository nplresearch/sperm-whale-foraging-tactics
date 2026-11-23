# M5 — Trajectory-scale search (not raised by R1; pre-emptive)

**Owner:** _unassigned_ **Status:** verified; post hoc.

## Claim
The published step-length μ≈2.35 is a sampling artefact: turns are defined between consecutive
25-Hz vectors, every sampled turn is a flip in *vertical* angle (median heading change 0.14°),
and μ depends on sample rate (2.34 @25 Hz, 1.45 @1 Hz, 1.72 @0.2 Hz). With heading-based turns
(5-s blocks, 30°), a two-mode (composite) mixture beats a power law in 13/15 fitted whales;
turning concentrates within 10 s of buzzes (OR 0.57 per log-s). Lévy foraging and MVT predictions
are not supported.

## Inputs / outputs
`data/dswp/trajectories/*.npz` + labelled events → `trajectory_*.csv`, `trajectory_tests.json`.
Code: `src/trajectory/heading_steps.py`; legacy script `scripts/run_review_r1_trajectory_tests.py`.

## Run
```bash
pytest review_r1/m5_trajectory_search
python review_r1/m5_trajectory_search/run.py
```

## Known failure modes / open issues
- At the primary setting only 15 of 20 whales have enough steps (median 7 turns per bottom
  phase) — report the sensitivity grid, not one setting.
- GEE/block p-values (10⁻³¹) ignore autocorrelation of 5-s blocks: say "very small".
- Heading is poorly defined at steep pitch and Type B buzzes are steep; only *roll* was
  checked (M6). **Add a pitch control before claiming the turning response.**
- `L_mu_vs_buzz_rate` (15 dives, p 0.009) is significant and unreported in the plan.
- MVT result is not robust to including each dive's last bout (p 0.097).
- Absolute MSD scale rests on the assumed 0.9 m/s.

## What would falsify it
Power law winning at most settings after a pitch-stratified re-fit.
