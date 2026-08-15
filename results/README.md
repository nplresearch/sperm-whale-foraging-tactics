# Generated numerical results

Pipeline-generated tables and model summaries are written here. The immutable
input checksums are recorded in `data/manifest.csv`; parameters and fixed
random seeds are defined in the tested modules and described in `docs/`.
`pipeline_summary.json` provides a compact check of the headline values.

Small reference summaries used by regression tests may be version-controlled.
Large or transient outputs should be regenerated.

The DSWP outputs include the classifier counts and contrasts, the explicit
constant-speed versus pitch-adaptive classifier sensitivity, model-selection
scan, classifier robustness matrices, mixed depth model, roll and pause tests,
Markov transitions, straightness, energetics, recurrence alternatives, and
safe reconstruction-error summaries. The energetic outputs include the
trajectory-based result-producing proxy, the Aoki steady-drag comparison
(`aoki_event_energy.csv` and `aoki_individual_energy.csv`). Trajectory outputs
contain the per-dive Lévy-like and MSD estimates plus corrected buzz-centred
squared-displacement curves, paired tests, and provenance. CETI outputs contain the supported preliminary
buzz-level validation. Azores outputs contain the operative and balanced prey
contrasts, robustness checks, vertical geometry, corrected Markov bootstrap,
derived event metrics, and a compact summary. They are regenerated only after
the checksummed CC0 source files have been retrieved locally.
