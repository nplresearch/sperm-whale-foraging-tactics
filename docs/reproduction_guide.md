# Reproduction guide

## Levels of reproduction

The repository distinguishes three levels:

1. **Unit reproduction** runs analytical functions on synthetic fixtures.
2. **Result reproduction** reruns a reported model or figure from the
   publication-safe derived inputs.
3. **Upstream reconstruction** rebuilds trajectories and buzz measurements
   from raw tags. This level is intentionally not part of the public release.

This separation is important: the repository reproduces paper results from
derived or authoritative open inputs without implying that restricted raw
records are public. Consult `docs/result_map.md` for the analysis crosswalk and
`docs/release_readiness.md` for the short public-release checklist.

## Set up the environment

From the repository root:

```bash
conda env create -f environment/environment.yml
conda activate ceti-foraging-reproducibility
```

or use the virtual-environment commands in the top-level README.

## Validate the release boundary

Run this before analysis and again before release:

```bash
python scripts/check_release_safety.py
```

The check rejects raw-data extensions, private filesystem or download paths,
embedded notebook outputs, files above GitHub's normal file-size limit, and
unsafe columns in distributed tables.

## Run the analyses

The complete public pipeline is:

```bash
python scripts/run_pipeline.py
```

The runner executes dataset validation first, then DSWP, trajectory-scale, and
CETI 2024 analyses and component-figure generation. Azores source validation
and analysis are a separate explicit step because the checksummed CC0 MATLAB
files are retrieved locally rather than committed. Use
`notebooks/validation/03_azores_derivation.ipynb` for the numerical derivation
and `04_azores_manuscript_figures.ipynb` for the paper components. Stages do not
overwrite input files.

The DSWP stage runs the manuscript's trajectory-driven energetic model and the
Aoki et al. (2012) steady-drag comparison over the same observed buzz
intervals. `dswp.energetics` reproduces the reported 1.28/9.07 MJ values;
`dswp.aoki` provides additional evidence that the directional A/B contrast is
preserved under a drag-only formulation.

To understand or modify an analysis, use the corresponding documented notebook
under `notebooks/`. Notebooks call the tested functions in `src/`; they are not
the sole implementation of the analysis.

## Verify the results

```bash
pytest
```

Tests cover:

- input schemas and identifier rules;
- deterministic classification and summary statistics;
- trajectory and sequence calculations on known examples;
- agreement between regenerated and archived numerical summaries, with
  explicitly documented tolerances; and
- the public-release data boundary.

## Interpreting differences

Minor graphical differences can arise across operating systems and plotting
backends. Numerical tests, rather than pixel identity, are the authoritative
check. Any expected tolerance should be tied to a specific floating-point or
stochastic operation; broad tolerances should not be used to conceal changes
in the reported results.
