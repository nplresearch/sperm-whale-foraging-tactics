"""Paper-defined post-buzz pause classes and association test."""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

PAUSE_BINS_S = (1.3, 3.4, 6.0)
PAUSE_LABELS = ("short", "medium", "long", "very_long")


def categorize_pauses(values) -> pd.Categorical:
    """Apply manuscript bins: <1.3, 1.3–<3.4, 3.4–6.0, and >6.0 seconds.

    Exact threshold values are assigned to the higher class except 6.0, which
    is long; this follows the written inclusive 3.4--6.0 convention.
    """
    x = pd.to_numeric(pd.Series(values), errors="coerce")
    labels = np.select(
        [x < 1.3, (x >= 1.3) & (x < 3.4), (x >= 3.4) & (x <= 6.0), x > 6.0],
        PAUSE_LABELS,
        default=None,
    )
    return pd.Categorical(labels, categories=PAUSE_LABELS, ordered=True)


def pause_category_table(
    events: pd.DataFrame, *, label="buzz_type", pause="post_buzz_pause_s"
) -> pd.DataFrame:
    """Counts, proportions, and binomial SE for A/B non-terminal pauses."""
    x = events.loc[events[label].isin(["A", "B"]) & events[pause].notna(), [label, pause]].copy()
    x["pause_category"] = categorize_pauses(x[pause])
    counts = pd.crosstab(x[label], x.pause_category).reindex(
        index=["A", "B"], columns=PAUSE_LABELS, fill_value=0
    )
    out = counts.stack().rename("count").reset_index()
    out.columns = ["buzz_type", "pause_category", "count"]
    out["total"] = out.groupby("buzz_type")["count"].transform("sum")
    out["proportion"] = out["count"] / out["total"]
    out["binomial_se"] = np.sqrt(out.proportion * (1 - out.proportion) / out.total)
    return out


def pause_association(events: pd.DataFrame, *, n_permutations=10_000, seed=42) -> dict:
    """Chi-square and label-permutation p-value for A/B pause categories."""
    tab = (
        pause_category_table(events)
        .pivot(index="buzz_type", columns="pause_category", values="count")
        .fillna(0)
    )
    tab = tab.loc[:, tab.sum(axis=0) > 0]
    chi2, _, _, _ = chi2_contingency(tab.to_numpy())
    labels = np.repeat(tab.index.to_numpy(), tab.sum(axis=1).astype(int))
    cats = np.concatenate([np.repeat(c, int(tab[c].sum())) for c in tab.columns])
    rng = np.random.default_rng(seed)
    simulated = []
    for _ in range(n_permutations):
        shuffled = rng.permutation(labels)
        sim = pd.crosstab(shuffled, cats).reindex(
            index=tab.index, columns=tab.columns, fill_value=0
        )
        simulated.append(chi2_contingency(sim.to_numpy())[0])
    return {
        "chi2": float(chi2),
        "permutation_p": float((np.sum(np.asarray(simulated) >= chi2) + 1) / (n_permutations + 1)),
        "n": int(tab.to_numpy().sum()),
    }
