# M7 — Azores validation (one juvenile whale)

**Owner:** _unassigned_ **Status:** echo results verified; phase/seafloor results are **printed-only**.

## Claim
"Type A targets deeper prey" survives restriction to the bottom phase (50–56 of 58 daytime buzzes,
p 0.002–0.010; within dives 65 m deeper, p < 0.001) and is not just built into vertical speed
(ramp-up predicts it too). Type A drops ~45 m below the search layer before buzzing; Type B is
taken within it. Prey size (echo level) does **not** differ (p 0.14, n 19 vs 11) and the echo
level is a weak size proxy (24 vs 40 dB per decade of range).

## Honest limits
One animal, 11 dives, 58 buzzes; every p-value is nominal and post hoc. DSWP shows the same
direction at 7–8 m (n.s.). Do **not** present as "stronger"; present as "consistent, single-whale".

## Inputs / outputs
Four Dryad files (`repo/Clean_notebooks_figures/Azores_code/`, pinned checksums:
`scripts/validate_azores_sources.py <dir>`). `foraging_models.json` stores echo tests only;
`scripts/run_review_r1_azores_phase.py` **prints** the phase/seafloor numbers. Capture them:
```bash
python scripts/run_review_r1_azores_phase.py > review_r1/m7_azores/azores_phase_output.txt
```
**Task for the owner:** make that script write JSON so the printed-only claims in
`claims.yaml` (M7-*) can become checked.

## Run
```bash
pytest review_r1/m7_azores
```
