# Manuscript-to-code result map

This table maps paper results to the public analysis. “Reproduced” means that
the numerical result is regenerated from a distributed or authoritative open
input; it does not require the final multi-panel artwork to be pixel-identical.

| Paper result or panel | Public input | Implementation and output | Status |
| --- | --- | --- | --- |
| DSWP deployment summary | `data/dswp/deployment_summary.csv` | checksummed source table | Reproduced from an approved pseudonymized summary |
| Reconstruction-method comparison | `data/dswp/reconstruction_error_summary.csv` | `results/dswp/reconstruction_method_summary.csv`; `figures/dswp/reconstruction_error_summary.*` | Reproduced from coordinate-free summaries; manuscript reports the mean of deployment-specific medians and the eight--eight win tie |
| Regional trajectory map | final manuscript artwork | none | Presentation-only asset; location-bearing inputs are outside the public data boundary |
| Representative 3-D path | `trajectory_index.csv`; `trajectories/T###.npz` | path loader in `trajectory.analysis` | Numerical path released; final manuscript composition is not automated |
| Buzz phase construction and threshold sensitivity | `buzz_clicks.csv`; `buzz_events.csv` | `dswp.buzz_thresholds`; `notebooks/dswp/00_dataset_and_buzz_construction.ipynb` | Production 0.3-s/0.05-s/five-point segmentation and all three alpha diagnostics reproduced from derived clicks; raw click detection is out of scope |
| Step-length exponents and Lévy-like robustness | DSWP trajectory release | `trajectory.analysis.analyze_release`; `results/trajectory/*`; `figures/trajectory/*` | Reproduced; Methods must name the operative fitter |
| MSD and temporal crossover | DSWP trajectory release | same as above | Reproduced |
| Buzz-centred squared displacement | DSWP trajectories and registered classifier features | `trajectory.manuscript.buzz_centred_results`; `results/trajectory/buzz_centred_displacement_*`; `figures/trajectory/buzz_centred_displacement.*`; `notebooks/trajectory/02_manuscript_trajectory_figures.ipynb` | Dive-local analysis retains 20 whales and 1,346/1,141 complete Type A/B windows; Type B exceeds Type A at all eight tested positive lags after Bonferroni correction |
| Main A/B GMM and counts | `data/dswp/buzz_events.csv` | `dswp.classification`; `results/dswp/buzz_events_labelled.csv`; `results/dswp/classifier_speed_sensitivity.json`; `figures/dswp/classifier.*` | Reproduced; constant-speed-derived primary input disclosed, with pitch-adaptive refit showing zero direct A/B switches among shared confident events |
| GMM BIC scan | derived buzz features | `gmm_model_selection.csv`; `gmm_model_selection.*` | Main ramp-up/3-D-speed optimum reproduced at `k=2`; diagnostic duration terminology documented |
| Threshold-free classifier robustness | derived buzz features | `classifier_robustness*.csv` | Reproduced |
| Buzz feature contrasts | derived buzz features | `buzz_group_contrasts.csv` | Reproduced |
| Depth mixed model | derived buzz features and anonymous hierarchy | `depth_mixed_model.json` | Reproduced |
| Vertical direction geometry | derived buzz features | `vertical_geometry*` | Reproduced |
| Roll time course | `roll_speed_bins.csv` | `roll_speed_bin_tests.csv`; `roll_speed_timecourse.*` | Reproduced with corrected degrees-per-second units |
| Within-dive Markov graph | ordered derived buzz events | `buzz_markov_transitions.csv`; `markov_transitions.*` | Reproduced using 200 resamples that each exclude ten deployments and preserve ambiguous gaps, matching the Methods |
| Post-buzz pause distributions | derived buzz features | `pause_*`; `pause_distribution.*`; `pause_categories.*` | Reproduced; the frozen terminal-event denominator is 36 total, comprising 29 Type B, 3 Type A, and 4 unassigned events |
| Buzz-centred straightness | derived buzz events and DSWP trajectories | `buzz_straightness.csv`; `straightness_group_contrasts.csv` | Reproduced, including post-buzz 20 m `P≈0.40` |
| Trajectory-driven energetic comparison | derived buzz events and pitch-adaptive trajectories | `dswp.energetics`; `buzz_energy.csv`; `individual_energy.csv`; `individual_energy.*` | Reported 1.28/9.07 MJ means reproduced with the model described in the current Methods and SI |
| Aoki steady-drag comparison | same observed buzz intervals and reconstructed speed series | `dswp.aoki`; `aoki_event_energy.csv`; `aoki_individual_energy.csv` | Additional directional evidence: Type B remains higher in all 20 whales, with B/A = 8.51 |
| Spatial recurrence/comebacks | coarse local deployment paths and derived buzz times | `comeback_*` tables and figures | Manuscript association and current-classifier sensitivity reproduced |
| Azores prey-field validation | pinned Dryad version-1 files | `validation.azores`; `results/azores/*`; `notebooks/validation/03_azores_derivation.ipynb` | Final 28/28/two-tie main and supplementary analyses reproduced from local checksummed CC0 inputs; full buzz-plus-margin window and duplicate-preserving Markov bootstrap frozen |
| CETI 2024 buzz-level validation | `data/ceti2024/buzz_features.csv` | `validation.ceti2024`; `results/ceti2024/*` | Supported kinematic and sequence summaries reproduced |
| CETI 2024 reconstructed-path and high-frequency roll-trace panels | none | none | Outside the scope of this release version; the released validation is buzz-level |

The authoritative one-command run for implemented rows is
`python scripts/run_pipeline.py`. The tests in `tests/` protect the numerical
targets; `scripts/check_release_safety.py` protects the public-data boundary.
