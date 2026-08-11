"""Non-parametric contrasts and buzz-sequence summaries."""
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, ks_2samp, mannwhitneyu, ttest_ind

def cliffs_delta(a, b) -> float:
    """P(A > B) - P(A < B); positive values mean A tends to be larger."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not len(a) or not len(b): return np.nan
    return float(((a[:, None] > b).sum() - (a[:, None] < b).sum()) / (len(a) * len(b)))

def compare_groups(frame, metric, *, label="buzz_type") -> dict:
    """Two-sided Mann--Whitney and Cliff's delta for A versus B."""
    a = frame.loc[frame[label].eq("A"), metric].dropna().to_numpy()
    b = frame.loc[frame[label].eq("B"), metric].dropna().to_numpy()
    out = {"metric": metric, "n_A": len(a), "n_B": len(b),
           "median_A": np.median(a) if len(a) else np.nan, "median_B": np.median(b) if len(b) else np.nan,
           "cliffs_delta": cliffs_delta(a, b)}
    out["U"], out["p_value"] = mannwhitneyu(a, b, alternative="two-sided") if len(a) and len(b) else (np.nan, np.nan)
    return out


def cohen_d(a, b) -> float:
    """Standardized mean difference using the mean of group variances."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    denominator = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return float((a.mean() - b.mean()) / denominator)


def depth_mixed_model(
    frame: pd.DataFrame,
    *,
    label: str = "buzz_type",
    depth_col: str = "avg_depth_m",
) -> dict:
    """A-vs-B depth model with whale and nested-dive random intercepts."""
    import statsmodels.formula.api as smf

    required = {
        label,
        depth_col,
        "individual_id",
        "dive_id",
        "deployment_id",
    }
    if missing := required - set(frame):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    values = frame.loc[
        frame[label].isin(["A", "B"]),
        [label, depth_col, "individual_id", "dive_id", "deployment_id"],
    ].dropna()
    values = values.rename(columns={depth_col: "depth_m"}).copy()
    values["is_A"] = values[label].eq("A").astype(int)
    model = smf.mixedlm(
        "depth_m ~ is_A",
        values,
        groups=values["individual_id"],
        re_formula="1",
        vc_formula={"dive": "0+C(dive_id)"},
    )
    fitted = model.fit(method="lbfgs", reml=True, disp=False)
    ci_low, ci_high = fitted.conf_int().loc["is_A"]
    a = values.loc[values["is_A"].eq(1), "depth_m"].to_numpy()
    b = values.loc[values["is_A"].eq(0), "depth_m"].to_numpy()
    return {
        "n": int(len(values)),
        "n_A": int(len(a)),
        "n_B": int(len(b)),
        "n_individuals": int(values["individual_id"].nunique()),
        "n_deployments": int(values["deployment_id"].nunique()),
        "n_dives": int(values["dive_id"].nunique()),
        "estimate_A_minus_B_m": float(fitted.params["is_A"]),
        "standard_error_m": float(fitted.bse["is_A"]),
        "ci_low_m": float(ci_low),
        "ci_high_m": float(ci_high),
        "z_value": float(fitted.tvalues["is_A"]),
        "p_value": float(fitted.pvalues["is_A"]),
        "whale_sd_m": float(np.sqrt(fitted.cov_re.iloc[0, 0])),
        "dive_sd_m": float(np.sqrt(fitted.vcomp[0])),
        "residual_sd_m": float(np.sqrt(fitted.scale)),
        "median_A_m": float(np.median(a)),
        "median_B_m": float(np.median(b)),
        "cohen_d": cohen_d(a, b),
        "cliffs_delta": cliffs_delta(a, b),
        "converged": bool(fitted.converged),
    }


def roll_speed_bin_tests(
    events: pd.DataFrame,
    roll_bins: pd.DataFrame,
    *,
    label: str = "buzz_type",
) -> pd.DataFrame:
    """Independent t-tests per 2-s bin with Bonferroni correction."""
    required_events = {"event_id", label}
    required_bins = {"event_id", "time_bin_s", "roll_speed_deg_s"}
    if missing := required_events - set(events):
        raise ValueError("Missing event columns: " + ", ".join(sorted(missing)))
    if missing := required_bins - set(roll_bins):
        raise ValueError("Missing roll-bin columns: " + ", ".join(sorted(missing)))
    merged = roll_bins.merge(
        events[["event_id", label]],
        on="event_id",
        validate="many_to_one",
    )
    rows = []
    for time_bin, group in merged.groupby("time_bin_s", sort=True):
        a = group.loc[group[label].eq("A"), "roll_speed_deg_s"].dropna()
        b = group.loc[group[label].eq("B"), "roll_speed_deg_s"].dropna()
        if len(a) <= 5 or len(b) <= 5:
            continue
        statistic, p_value = ttest_ind(a, b)
        rows.append(
            {
                "time_bin_s": float(time_bin),
                "n_A": int(len(a)),
                "n_B": int(len(b)),
                "mean_A_deg_s": float(a.mean()),
                "mean_B_deg_s": float(b.mean()),
                "t_statistic": float(statistic),
                "p_value": float(p_value),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["p_value_bonferroni"] = np.minimum(
        1.0, out["p_value"] * len(out)
    )
    out["significant_0_05"] = out["p_value_bonferroni"] < 0.05
    return out


def pause_distribution_tests(
    frame: pd.DataFrame,
    *,
    label: str = "buzz_type",
    pause_col: str = "post_buzz_pause_s",
) -> dict:
    """Mann--Whitney and KS tests for non-terminal A/B pause durations."""
    a = frame.loc[frame[label].eq("A"), pause_col].dropna().to_numpy()
    b = frame.loc[frame[label].eq("B"), pause_col].dropna().to_numpy()
    mann_whitney = mannwhitneyu(a, b, alternative="two-sided")
    ks = ks_2samp(a, b, alternative="two-sided")
    return {
        "n_A": int(len(a)),
        "n_B": int(len(b)),
        "median_A_s": float(np.median(a)),
        "median_B_s": float(np.median(b)),
        "mann_whitney_U": float(mann_whitney.statistic),
        "mann_whitney_p": float(mann_whitney.pvalue),
        "ks_D": float(ks.statistic),
        "ks_p": float(ks.pvalue),
    }

def _counts(sequences):
    counts = {"S": {"A": 0, "B": 0}, "A": {"A": 0, "B": 0, "E": 0}, "B": {"A": 0, "B": 0, "E": 0}}
    for sequence in sequences:
        if not sequence: continue
        counts["S"][sequence[0]] += 1
        for left, right in zip(sequence, sequence[1:]): counts[left][right] += 1
        counts[sequence[-1]]["E"] += 1
    return counts


def _markov_probabilities_with_gaps(
    frame: pd.DataFrame,
    *,
    label: str = "buzz_type",
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], int]]:
    """Reproduce the paper graph while preserving ambiguous buzzes as gaps.

    The figure-generating notebook first counted every adjacent transition,
    including transitions to and from ``?``, and only then removed the
    ambiguous row and column before normalizing the remaining counts. Thus an
    A--?--B run contributes neither A→B nor a transition involving ``?`` to
    the displayed matrix. This is intentionally different from filtering out
    ``?`` before constructing sequences, which would bridge across the gap.
    """
    states = ("S", "A", "B", "?", "E")
    counts = {(left, right): 0 for left in states for right in states}
    for _, group in frame.groupby(["deployment_id", "dive_id"], sort=False):
        labels = [
            value if value in ("A", "B") else "?"
            for value in group.sort_values("buzz_start_s")[label]
        ]
        if not labels:
            continue
        sequence = ["S", *labels, "E"]
        for left, right in zip(sequence, sequence[1:]):
            counts[(left, right)] += 1

    displayed_edges = {
        "S": ("A", "B"),
        "A": ("A", "B", "E"),
        "B": ("A", "B", "E"),
    }
    probabilities = {}
    displayed_counts = {}
    for left, destinations in displayed_edges.items():
        denominator = sum(counts[(left, right)] for right in destinations)
        for right in destinations:
            displayed_counts[(left, right)] = counts[(left, right)]
            probabilities[(left, right)] = (
                counts[(left, right)] / denominator
                if denominator
                else np.nan
            )
    return probabilities, displayed_counts


def markov_leave_subset_out(
    frame: pd.DataFrame,
    *,
    label: str = "buzz_type",
    group_col: str = "deployment_id",
    n_resamples: int = 200,
    n_exclude_min: int = 10,
    n_exclude_max: int | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Reproduce the transition graph and its leave-subset-out uncertainty.

    Defaults match the result-producing notebook: 200 resamples, each
    excluding ten deployments. ``n_exclude_min=5``, ``n_exclude_max=10`` and
    ``group_col="individual_id"`` can be used to evaluate the procedure
    currently described in the manuscript Methods.
    """
    required = {
        "deployment_id",
        "dive_id",
        "buzz_start_s",
        label,
        group_col,
    }
    if missing := required - set(frame):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    n_exclude_max = (
        n_exclude_min if n_exclude_max is None else n_exclude_max
    )
    if not 0 <= n_exclude_min <= n_exclude_max:
        raise ValueError("Require 0 <= n_exclude_min <= n_exclude_max")

    point, counts = _markov_probabilities_with_gaps(frame, label=label)
    groups = pd.unique(frame[group_col].dropna())
    if not len(groups):
        raise ValueError(f"No non-missing values in {group_col}")
    rng = np.random.default_rng(seed)
    draws = {edge: [] for edge in point}
    for _ in range(n_resamples):
        n_exclude = int(rng.integers(n_exclude_min, n_exclude_max + 1))
        excluded = rng.choice(
            groups, size=min(n_exclude, len(groups)), replace=False
        )
        probabilities, _ = _markov_probabilities_with_gaps(
            frame.loc[~frame[group_col].isin(excluded)],
            label=label,
        )
        for edge, value in probabilities.items():
            draws[edge].append(value)

    return pd.DataFrame(
        [
            {
                "from_state": left,
                "to_state": right,
                "probability": point[(left, right)],
                "mean_probability": (
                    float(np.mean(finite_draws))
                    if len(finite_draws := np.asarray(
                        draws[(left, right)]
                    )[np.isfinite(draws[(left, right)])])
                    else np.nan
                ),
                "std_probability": (
                    float(np.std(finite_draws)) if len(finite_draws) else np.nan
                ),
                "count": counts[(left, right)],
                "resampling_unit": group_col,
                "n_resamples": n_resamples,
                "n_exclude_min": n_exclude_min,
                "n_exclude_max": n_exclude_max,
                "seed": seed,
            }
            for left, right in point
        ]
    )


def markov_with_ci(frame, *, label="buzz_type", n_boot=2000, seed=42) -> pd.DataFrame:
    """Start→A/B→End transitions with 95% CIs resampled at the dive level."""
    seqs = []
    for _, g in frame.groupby(["deployment_id", "dive_id"], sort=False):
        seq = [x for x in g.sort_values("buzz_start_s")[label] if x in ("A", "B")]
        if seq: seqs.append(seq)
    if not seqs: return pd.DataFrame(columns=["from_state", "to_state", "probability", "ci_low", "ci_high", "count"])
    def probabilities(seqs):
        counts = _counts(seqs)
        return {(f, t): c / sum(dest.values()) if sum(dest.values()) else np.nan
                for f, dest in counts.items() for t, c in dest.items()}, counts
    point, counts = probabilities(seqs); rng = np.random.default_rng(seed)
    draws = {key: [] for key in point}
    for _ in range(n_boot):
        sampled = [seqs[i] for i in rng.integers(0, len(seqs), len(seqs))]
        p, _ = probabilities(sampled)
        for key, value in p.items(): draws[key].append(value)
    return pd.DataFrame([{"from_state": f, "to_state": t, "probability": point[(f,t)],
                          "ci_low": np.nanpercentile(draws[(f,t)], 2.5), "ci_high": np.nanpercentile(draws[(f,t)], 97.5),
                          "count": counts[f][t]} for f, t in point])


def geometry_association(frame, *, label="buzz_type") -> tuple[pd.DataFrame, dict]:
    """Four-category vertical direction table and Pearson residuals."""
    required = {
        label,
        "vertical_direction_before",
        "vertical_direction_after",
    }
    if missing := required - set(frame):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    values = frame[frame[label].isin(["A", "B"])].dropna(
        subset=["vertical_direction_before", "vertical_direction_after"]
    ).copy()
    before = np.where(values["vertical_direction_before"] >= 0, "down", "up")
    after = np.where(values["vertical_direction_after"] >= 0, "down", "up")
    values["geometry"] = np.char.add(np.char.add(before, "_to_"), after)
    order = ["down_to_down", "up_to_up", "down_to_up", "up_to_down"]
    counts = (
        pd.crosstab(values[label], values["geometry"])
        .reindex(index=["A", "B"], columns=order, fill_value=0)
    )
    chi2, p_value, dof, expected = chi2_contingency(counts)
    residuals = (counts.to_numpy() - expected) / np.sqrt(expected)
    rows = []
    for i, buzz_type in enumerate(counts.index):
        for j, geometry in enumerate(counts.columns):
            rows.append(
                {
                    "buzz_type": buzz_type,
                    "geometry": geometry,
                    "count": int(counts.iloc[i, j]),
                    "expected": float(expected[i, j]),
                    "pearson_residual": float(residuals[i, j]),
                }
            )
    return pd.DataFrame(rows), {
        "chi2": float(chi2),
        "p_value": float(p_value),
        "degrees_of_freedom": int(dof),
        "n": int(counts.to_numpy().sum()),
    }
