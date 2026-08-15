# Manuscript-to-code result map

This table is the release checklist for the paper. “Reproduced” means that the
numerical result is regenerated from a distributed or authoritative open input,
not that the final multi-panel artwork is pixel-identical. “Decision required”
means that the available implementation and the manuscript are not currently
the same analysis; details and alternatives are in `known_issues.md`.

| Paper result or panel | Public input | Implementation and output | Status |
| --- | --- | --- | --- |
| DSWP deployment summary | `data/dswp/deployment_summary.csv` | checksummed source table | Releasable after steward review |
| Reconstruction-method comparison | `data/dswp/reconstruction_error_summary.csv` | `results/dswp/reconstruction_method_summary.csv`; `figures/dswp/reconstruction_error_summary.*` | Reproduced from coordinate-free summaries; manuscript aggregation wording requires correction |
| Regional trajectory map | local-coordinate DSWP paths | none | Intentionally not reproducible without location-bearing data |
| Representative 3-D path | `trajectory_index.csv`; `trajectories/T###.npz` | path loader in `trajectory.analysis` | Numerical path released; final manuscript composition is not automated |
| Buzz phase construction and threshold sensitivity | `buzz_clicks.csv`; `buzz_events.csv` | `dswp.buzz_thresholds`; `notebooks/dswp/00_dataset_and_buzz_construction.ipynb` | Production 0.3-s/0.05-s/five-point segmentation and all three alpha diagnostics reproduced from derived clicks; raw click detection is out of scope |
| Step-length exponents and Lévy-like robustness | DSWP trajectory release | `trajectory.analysis.analyze_release`; `results/trajectory/*`; `figures/trajectory/*` | Reproduced; Methods must name the operative fitter |
| MSD and temporal crossover | DSWP trajectory release | same as above | Reproduced |
| Buzz-centred squared displacement | DSWP trajectories and registered classifier features | `trajectory.manuscript.buzz_centred_results`; `results/trajectory/buzz_centred_displacement_*`; `figures/trajectory/buzz_centred_displacement.*`; `notebooks/trajectory/02_manuscript_trajectory_figures.ipynb` | Corrected dive-local analysis retains 20 whales and 1,346/1,141 complete Type A/B windows; Type B exceeds Type A at all eight tested positive lags after Bonferroni correction. Legacy eight-whale null retained only as forensic provenance |
| Main A/B GMM and counts | `data/dswp/buzz_events.csv` | `dswp.classification`; `results/dswp/buzz_events_labelled.csv`; `results/dswp/classifier_speed_sensitivity.json`; `figures/dswp/classifier.*` | Reproduced; constant-speed-derived primary input disclosed, with pitch-adaptive refit showing zero direct A/B switches among shared confident events |
| GMM BIC scan | derived buzz features | `gmm_model_selection.csv`; `gmm_model_selection.*` | Main ramp-up/3-D-speed optimum reproduced at `k=2`; diagnostic duration terminology documented |
| Threshold-free classifier robustness | derived buzz features | `classifier_robustness*.csv` | Reproduced |
| Buzz feature contrasts | derived buzz features | `buzz_group_contrasts.csv` | Reproduced |
| Depth mixed model | derived buzz features and anonymous hierarchy | `depth_mixed_model.json` | Reproduced |
| Vertical direction geometry | derived buzz features | `vertical_geometry*` | Reproduced |
| Roll time course | `roll_speed_bins.csv` | `roll_speed_bin_tests.csv`; `roll_speed_timecourse.*` | Reproduced with corrected degrees-per-second units |
| Within-dive Markov graph | ordered derived buzz events | `buzz_markov_transitions.csv`; `markov_transitions.*` | Figure values reproduced; manuscript resampling unit requires correction |
| Post-buzz pause distributions | derived buzz features | `pause_*`; `pause_distribution.*`; `pause_categories.*` | Distributions reproduced; terminal-event count requires resolution |
| Buzz-centred straightness | derived buzz events and DSWP trajectories | `buzz_straightness.csv`; `straightness_group_contrasts.csv` | Reproduced, including post-buzz 20 m `P≈0.40` |
| Trajectory-driven energetic comparison | derived buzz events and pitch-adaptive trajectories | `dswp.energetics`; `buzz_energy.csv`; `individual_energy.csv`; `individual_energy.*` | Reported 1.28/9.07 MJ means reproduced with the model described in the current Methods and SI |
| Aoki steady-drag comparison | same observed buzz intervals and reconstructed speed series | `dswp.aoki`; `aoki_event_energy.csv`; `aoki_individual_energy.csv` | Additional directional evidence: Type B remains higher in all 20 whales, with B/A = 8.51 |
| Spatial recurrence/comebacks | coarse local deployment paths and derived buzz times | `comeback_*` tables and figures | Legacy manuscript and current-classifier versions both reproduced; one definition must be selected |
| Azores prey-field validation | pinned Dryad version-1 files | `validation.azores`; `results/azores/*`; `notebooks/validation/03_azores_derivation.ipynb` | Numerical main and supplementary analyses reproduced from local checksummed CC0 inputs; manuscript sample-count, echo-window, nearest-range, and Markov-CI wording require correction |
| CETI 2024 buzz-level validation | `data/ceti2024/buzz_features.csv` | `validation.ceti2024`; `results/ceti2024/*` | Supported kinematic and sequence summaries reproduced |
| CETI 2024 path/heading panels | steward-approved local-coordinate paths | none yet | Blocked on reviewed reconstructed trajectory bundle |

The authoritative one-command run for implemented rows is
`python scripts/run_pipeline.py`. The tests in `tests/` protect the numerical
targets; `scripts/check_release_safety.py` protects the public-data boundary.
