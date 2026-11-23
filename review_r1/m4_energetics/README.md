# M4 — Energetics at the right scale (R1 point 4)

**Owner:** _unassigned_ **Status:** mixed — see per-claim status in `claims.yaml`.

## Claim
Drop "sevenfold (1.28 vs 9.07 MJ)". The ratio is not identified: 3× to 35× across defensible
settings; only B > A (20/20 whales) is stable. 99 % of modelled work is the positive-acceleration
term; median Type B power is 114× the model's resting rate (implausible; model uses 40 t, a
16 m adult male, not a Dominica social-unit whale).

## Why the model misbehaves (known-answer tests)
`max(0, m·a·v)` keeps only positive acceleration, so zero-mean 25-Hz speed jitter is rectified
into positive work (`test_zero_mean_speed_noise_is_rectified…`). 1-s smoothing removes 90 % of
Type A energy. Drag follows v^2.8.

## Replacement numbers and their status
| quantity | value | status |
|---|---|---|
| drag + resting only, production speed | B/A 3.1 | verified |
| stroke intensity (RMS) B/A | 1.27 | verified |
| cumulative stroke effort B/A | 2.39 | verified, but ≈ 1.9× duration × 1.27 |
| drag at OCDR speed B/A | 2.65 (energy/buzz 2.70) | **circular** (see M2) |
| dive-level: genuine Type B vs dive length | −0.4 min, p 0.82 | verified null |
| bottom stroke effort vs dive length | +1.3 min/SD, p 0.018 | verified, wrong sign for oxygen |

So the defensible per-buzz statement is "Type B is longer and strokes ~1.3× harder"; the
2.5× figure is mostly duration.

## Run
```bash
pytest review_r1/m4_energetics
python review_r1/m4_energetics/run.py
```
Do not read CLAUDE.md-listed bug catalogue lightly: `code/comparison-energy-models/CLAUDE.md`.

## What would falsify it
Independent speed (flow noise / jiggle) giving B/A energy outside 2–3× with a plausible
(<5× resting) median power.
