"""Paper-compatible A/B buzz classification from derived feature summaries."""
import numpy as np
import pandas as pd
from scipy.stats import rankdata

FEATURES = ("ramp_up_duration_s", "avg_speed_3d_m_s")
MODEL_SELECTION_FEATURES = {
    "ramp_up_vs_3d_speed": (
        "ramp_up_duration_s",
        "avg_speed_3d_m_s",
    ),
    "max_click_rate_vs_roll": (
        "max_click_rate_hz",
        "avg_roll_speed_deg_s",
    ),
    "total_duration_vs_median_click_rate": (
        "ramp_plus_plateau_duration_s",
        "median_click_rate_hz",
    ),
}

def _valid(frame, features=FEATURES):
    return frame.loc[frame.loc[:, list(features)].notna().all(axis=1), list(features)]

def classify_gmm(frame: pd.DataFrame, *, features=FEATURES, probability_threshold=0.75,
                 random_state=1234) -> pd.Series:
    """Two-component quantile-normal GMM used for the main DSWP classifier.

    The high-speed component is B, low-speed component A.  Rows lacking either
    feature or with posterior below ``probability_threshold`` receive ``?``.
    Requires scikit-learn only when called.
    """
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import QuantileTransformer
    valid = _valid(frame, features)
    labels = pd.Series("?", index=frame.index, dtype=object)
    if len(valid) < 4:
        return labels
    # The paper code used every complete observation as a quantile. Keep this
    # explicit because sklearn's estimator default would otherwise cap at 1000.
    transformed = QuantileTransformer(n_quantiles=len(valid), output_distribution="normal",
                                      random_state=0).fit_transform(valid.to_numpy())
    model = GaussianMixture(n_components=2, covariance_type="full", n_init=10,
                            init_params="kmeans", random_state=random_state).fit(transformed)
    posterior = model.predict_proba(transformed); hard = posterior.argmax(axis=1)
    high_speed_component = np.argmax([valid.iloc[hard == k, 1].mean() for k in range(2)])
    named = np.where(hard == high_speed_component, "B", "A")
    labels.loc[valid.index] = np.where(posterior.max(axis=1) < probability_threshold, "?", named)
    return labels


def classify_gmm_hard(
    frame: pd.DataFrame,
    *,
    features=FEATURES,
    random_state=1234,
) -> pd.Series:
    """GMM hard labels without the posterior threshold, for SI robustness."""
    return classify_gmm(
        frame,
        features=features,
        probability_threshold=0.0,
        random_state=random_state,
    )


def classify_extreme_corners(frame: pd.DataFrame, *, features=FEATURES, n_per_class=None) -> pd.Series:
    """Azores robustness classification in rank space.

    A is nearest the short-ramp/slow-speed corner and B nearest the
    long-ramp/fast-speed corner.  Overlap is deliberately labelled ``?`` rather
    than arbitrarily assigned, making the two reference sets disjoint.
    """
    valid = _valid(frame, features); labels = pd.Series("?", index=frame.index, dtype=object)
    if len(valid) < 2:
        return labels
    n = len(valid); n_per_class = n // 2 if n_per_class is None else int(n_per_class)
    if not 1 <= n_per_class <= n:
        raise ValueError("n_per_class must lie between 1 and number of complete rows")
    ranks = np.column_stack([(rankdata(valid[c]) - 1) / (n - 1) for c in features])
    a = set(valid.index[np.argsort(np.hypot(ranks[:, 0], ranks[:, 1]))[:n_per_class]])
    b = set(valid.index[np.argsort(np.hypot(1-ranks[:, 0], 1-ranks[:, 1]))[:n_per_class]])
    labels.loc[list(a - b)] = "A"; labels.loc[list(b - a)] = "B"
    return labels


def classify_corner_argmin(
    frame: pd.DataFrame,
    *,
    features=FEATURES,
) -> pd.Series:
    """Assign each complete row to its nearer diagonal corner in rank space."""
    valid = _valid(frame, features)
    labels = pd.Series("?", index=frame.index, dtype=object)
    if len(valid) < 2:
        return labels
    n = len(valid)
    ranks = np.column_stack(
        [(rankdata(valid[column]) - 1) / (n - 1) for column in features]
    )
    distance_a = np.hypot(ranks[:, 0], ranks[:, 1])
    distance_b = np.hypot(1 - ranks[:, 0], 1 - ranks[:, 1])
    labels.loc[valid.index] = np.where(distance_a <= distance_b, "A", "B")
    return labels


def classifier_robustness(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reproduce the three threshold-free classifier comparisons in the SI."""
    from sklearn.metrics import cohen_kappa_score, confusion_matrix

    gmm_3d = classify_gmm_hard(frame)
    alternatives = {
        "gmm_vertical_speed": classify_gmm_hard(
            frame,
            features=("ramp_up_duration_s", "avg_vertical_speed_m_s"),
        ),
        "corner_3d_speed": classify_corner_argmin(frame),
        "corner_vertical_speed": classify_corner_argmin(
            frame,
            features=("ramp_up_duration_s", "avg_vertical_speed_m_s"),
        ),
    }
    summaries = []
    matrix_rows = []
    for name, alternative in alternatives.items():
        compared = gmm_3d.isin(["A", "B"]) & alternative.isin(["A", "B"])
        reference = gmm_3d.loc[compared].to_numpy()
        candidate = alternative.loc[compared].to_numpy()
        direct = np.mean(reference == candidate)
        flipped = np.mean(reference != candidate)
        was_flipped = bool(flipped > direct)
        aligned = (
            np.where(candidate == "A", "B", "A")
            if was_flipped
            else candidate
        )
        matrix = confusion_matrix(reference, aligned, labels=["A", "B"])
        summaries.append(
            {
                "comparison": name,
                "n": int(len(reference)),
                "agreement": float(np.mean(reference == aligned)),
                "cohen_kappa": float(cohen_kappa_score(reference, aligned)),
                "labels_flipped": was_flipped,
            }
        )
        for i, reference_label in enumerate(("A", "B")):
            for j, alternative_label in enumerate(("A", "B")):
                matrix_rows.append(
                    {
                        "comparison": name,
                        "reference_gmm_3d": reference_label,
                        "aligned_alternative": alternative_label,
                        "count": int(matrix[i, j]),
                    }
                )
    return pd.DataFrame(summaries), pd.DataFrame(matrix_rows)


def gmm_model_selection(
    frame: pd.DataFrame,
    *,
    feature_pairs=MODEL_SELECTION_FEATURES,
    k_values=range(1, 9),
    random_state=1234,
) -> pd.DataFrame:
    """Reproduce the SI BIC/AIC scan for the three registered feature pairs."""
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import QuantileTransformer

    rows = []
    working = frame.copy()
    working["ramp_plus_plateau_duration_s"] = (
        working["ramp_up_duration_s"] + working["plateau_duration_s"]
    )
    for pair_name, features in feature_pairs.items():
        valid = _valid(working, features)
        if len(valid) < 10:
            raise ValueError(
                f"Too few complete rows for model selection: {pair_name}"
            )
        transformed = QuantileTransformer(
            n_quantiles=len(valid),
            output_distribution="normal",
            random_state=0,
        ).fit_transform(valid.to_numpy())
        pair_rows = []
        for n_components in k_values:
            model = GaussianMixture(
                n_components=n_components,
                covariance_type="full",
                n_init=10,
                init_params="kmeans",
                random_state=random_state,
            ).fit(transformed)
            pair_rows.append(
                {
                    "feature_pair": pair_name,
                    "feature_1": features[0],
                    "feature_2": features[1],
                    "n": int(len(valid)),
                    "n_components": int(n_components),
                    "bic": float(model.bic(transformed)),
                    "aic": float(model.aic(transformed)),
                }
            )
        reference_bic = pair_rows[0]["bic"]
        reference_aic = pair_rows[0]["aic"]
        for row in pair_rows:
            row["delta_bic_from_k1"] = row["bic"] - reference_bic
            row["delta_aic_from_k1"] = row["aic"] - reference_aic
        rows.extend(pair_rows)
    return pd.DataFrame(rows)

def attach_labels(frame: pd.DataFrame, *, method="gmm") -> pd.DataFrame:
    """Return a copy with ``buzz_type`` and retain only derived columns."""
    out = frame.copy()
    out["buzz_type"] = classify_gmm(out) if method == "gmm" else classify_extreme_corners(out)
    return out
