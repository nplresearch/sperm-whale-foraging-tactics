# M6 — Tactic ↔ search coupling and the phase check

**Owner:** _unassigned_ **Status:** coupling verified; oxygen/termination claims **withdrawn**.

## Claim that stands (bottom phase only)
First buzz after a travel gap is Type B 39 % of the time vs 50 % within a bout (OR 0.65,
p 6e-7); Type B more likely after a short gap (OR 0.73 per log-min). Heading changes across
buzzes last (41° vs 18°, 20/20 whales) and turning doubles near low-roll buzzes (5.3 % vs 2.2 %).

## Claims withdrawn by the phase check
"Type B ends dives" (OR 2.17 → 0.93 in bottom phase), "Type-B-rich dives are shorter"
(−4.4 → −2.1 min, p 0.20; −2.9 min, p 0.11 with acoustic labels), U-shaped use, Markov
Start→B 0.54 / End asymmetry (`main.tex:259–270`). They come from transit buzzes: 84 % of
dive-final Type B buzzes are in the ascent; the share effect is a denominator artefact.
These numbers still reproduce, so their claims are flagged `withdrawn` — never quote as support.

## Inputs / outputs
`foraging_models.json`, `trajectory_tests.json`, `transit_buzz_profile.csv`;
printed-only: `scripts/run_review_r1_share_decomposition.py`.

## Run
```bash
pytest review_r1/m6_tactic_search_coupling
python review_r1/m6_tactic_search_coupling/run.py
```

## Known failure modes
- ~25 post hoc tests: only D4/C1/X survive multiplicity; none pre-registered. Put all in one SI table.
- Type B ≈ vertical speed, so "climbing" controls are imperfect — bottom-only is the clean test.
- Bout threshold (76 s) is fitted; no capture-success data, so "follow-up after a miss" cannot be
  separated from "more prey nearby".
- Roll check does not cover pitch (see M5).

## What would falsify it
Bottom-phase first-in-bout OR crossing 1, or the effect vanishing with whale-clustered permutation.
