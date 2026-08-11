"""Exact trajectory-scale analysis used for the manuscript.

The public inputs are reconstructed positions, not raw tag channels.  The
functions below preserve the production choices that generated the reported
numbers: hybrid trajectories sampled at 25 Hz, 30-degree turning points,
foraging segments from the reviewed phase boundaries, a 30-candidate
Clauset-style cutoff scan, and 50 logarithmically spaced MSD lags.

The fitted distributions are described as *Lévy-like*.  A heavy tail and a
superdiffusive MSD do not establish a unique generative or optimal search rule.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


FS_HZ = 25.0
MIN_MAX_DEPTH_M = 600.0
SURFACE_THRESHOLD_M = 50.0
MIN_SAMPLES = 50
MIN_STEPS = 30
TURN_THRESHOLD_RAD = np.pi / 6


def turning_points(
    xyz: np.ndarray, threshold_rad: float = TURN_THRESHOLD_RAD
) -> np.ndarray:
    """Return production turning-point indices.

    A point is retained when the angle between consecutive non-zero
    displacement vectors exceeds ``threshold_rad``. Endpoints are intentionally
    *not* added: the published step lengths are distances between detected
    turning points only.
    """
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("xyz must have shape (n_samples, 3)")
    displacement = np.diff(xyz, axis=0)
    norms = np.linalg.norm(displacement, axis=1)
    valid = norms > 1e-9
    if valid.sum() < 3:
        return np.array([], dtype=int)
    unit = displacement[valid] / norms[valid, None]
    angles = np.arccos(
        np.clip(np.einsum("ij,ij->i", unit[:-1], unit[1:]), -1.0, 1.0)
    )
    valid_indices = np.where(valid)[0]
    return valid_indices[np.where(angles > threshold_rad)[0] + 1] + 1


def step_lengths(
    xyz: np.ndarray, threshold_rad: float = TURN_THRESHOLD_RAD
) -> np.ndarray:
    """Euclidean distances between successive detected turning points."""
    xyz = np.asarray(xyz, dtype=float)
    points = turning_points(xyz, threshold_rad)
    if len(points) < 2:
        return np.array([], dtype=float)
    return np.linalg.norm(np.diff(xyz[points], axis=0), axis=1)


def fit_powerlaw(steps: np.ndarray, min_tail: int = MIN_STEPS) -> dict:
    """Continuous power-law MLE with the manuscript's KS cutoff scan.

    Thirty candidate ``xmin`` values are drawn from the 5th--80th percentiles.
    The exponent is denoted ``mu`` in the paper.  This is a descriptive fit,
    and the repository deliberately avoids re-labelling it as proof of a
    power-law search mechanism.
    """
    values = np.asarray(steps, dtype=float)
    values = np.sort(values[np.isfinite(values) & (values > 0)])
    if len(values) < min_tail:
        return {"mu": np.nan, "xmin_m": np.nan, "ks": np.nan, "n_tail": 0}

    best = (np.nan, np.nan, np.inf, 0)
    candidates = np.unique(np.percentile(values, np.linspace(5, 80, 30)))
    for xmin in candidates:
        tail = values[values >= xmin]
        if len(tail) < min_tail:
            continue
        log_sum = np.sum(np.log(tail / xmin))
        if log_sum <= 0:
            continue
        mu = 1.0 + len(tail) / log_sum
        empirical = np.arange(1, len(tail) + 1) / len(tail)
        fitted = 1.0 - (tail / xmin) ** (-(mu - 1.0))
        ks = float(np.max(np.abs(empirical - fitted)))
        if ks < best[2]:
            best = (float(mu), float(xmin), ks, int(len(tail)))
    return {
        "mu": best[0],
        "xmin_m": best[1],
        "ks": best[2],
        "n_tail": best[3],
    }


def msd_curve(
    xyz: np.ndarray,
    *,
    fs_hz: float = FS_HZ,
    n_lags: int = 50,
    max_fraction: float = 0.4,
) -> pd.DataFrame:
    """Time-averaged 3-D MSD at the production logarithmic lag grid."""
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("xyz must have shape (n_samples, 3)")
    if len(xyz) < 4:
        return pd.DataFrame(columns=["lag_samples", "lag_s", "msd_m2"])
    maximum = max(2, int(max_fraction * len(xyz)))
    lags = np.unique(
        np.round(np.logspace(0, np.log10(maximum), n_lags)).astype(int)
    )
    lags = lags[(lags >= 1) & (lags < len(xyz))]
    msd = [
        np.mean(np.sum((xyz[lag:] - xyz[:-lag]) ** 2, axis=1))
        for lag in lags
    ]
    return pd.DataFrame(
        {
            "lag_samples": lags,
            "lag_s": lags / float(fs_hz),
            "msd_m2": msd,
        }
    )


def loglog_slope(
    curve: pd.DataFrame,
    min_lag_s: float | None = None,
    max_lag_s: float | None = None,
) -> dict:
    """OLS slope of log(MSD) against log(time lag)."""
    selected = curve.copy()
    if min_lag_s is not None:
        selected = selected[selected["lag_s"] >= min_lag_s]
    if max_lag_s is not None:
        selected = selected[selected["lag_s"] <= max_lag_s]
    selected = selected[
        (selected["lag_s"] > 0)
        & (selected["msd_m2"] > 0)
        & np.isfinite(selected["msd_m2"])
    ]
    if len(selected) < 4:
        return {"alpha_msd": np.nan, "msd_r2": np.nan, "n_lags": len(selected)}
    fit = stats.linregress(
        np.log(selected["lag_s"]), np.log(selected["msd_m2"])
    )
    return {
        "alpha_msd": float(fit.slope),
        "msd_r2": float(fit.rvalue**2),
        "n_lags": int(len(selected)),
    }


def _longest_true_run(mask: np.ndarray) -> np.ndarray:
    indices = np.where(mask)[0]
    if len(indices) < 2:
        return indices
    return max(
        np.split(indices, np.where(np.diff(indices) > 1)[0] + 1),
        key=len,
    )


def load_trajectory(path: str | Path) -> np.ndarray:
    """Load one numeric-only release archive."""
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != {"xyz_m"}:
            raise ValueError(f"{path}: expected only numeric member 'xyz_m'")
        xyz = archive["xyz_m"]
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError(f"{path}: invalid reconstructed trajectory")
    return xyz.astype(float, copy=False)


def analyze_release(
    index_csv: str | Path,
    *,
    threshold_rad: float = TURN_THRESHOLD_RAD,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Run the reported foraging and multiscale analyses from release files.

    Returns ``(per_dive, population_summary, timescale_results)``. The index
    contains release pseudonyms and phase bounds; no source identifiers,
    absolute positions, or raw depth series are required.
    """
    index_path = Path(index_csv)
    index = pd.read_csv(index_path)
    required = {
        "trajectory_id",
        "individual_id",
        "file",
        "sampling_rate_hz",
        "foraging_start_index",
        "foraging_end_index",
        "max_depth_m",
    }
    missing = required - set(index)
    if missing:
        raise ValueError(f"trajectory index is missing {sorted(missing)}")

    per_dive_rows: list[dict] = []
    timescale_rows: list[dict] = []
    pooled_steps: list[np.ndarray] = []

    windows = {
        "alpha_short_le_1min": (1.0 / FS_HZ, 60.0),
        "alpha_mid_1_5min": (60.0, 300.0),
        "alpha_long_5_15min": (300.0, 900.0),
        "alpha_very_long_ge_15min": (900.0, None),
    }

    for row in index.itertuples(index=False):
        if not np.isfinite(row.max_depth_m) or row.max_depth_m < MIN_MAX_DEPTH_M:
            continue
        xyz = load_trajectory(index_path.parent / row.file)
        start = max(0, int(row.foraging_start_index))
        end = min(len(xyz), int(row.foraging_end_index))
        foraging = xyz[start:end]
        foraging = foraging[np.isfinite(foraging).all(axis=1)]
        if len(foraging) < MIN_SAMPLES:
            continue

        steps = step_lengths(foraging, threshold_rad)
        if len(steps) < MIN_STEPS:
            continue
        powerlaw = fit_powerlaw(steps)
        msd = loglog_slope(
            msd_curve(foraging, fs_hz=row.sampling_rate_hz)
        )
        per_dive_rows.append(
            {
                "trajectory_id": row.trajectory_id,
                "individual_id": row.individual_id,
                "n_foraging_samples": len(foraging),
                "n_turning_points": len(turning_points(foraging, threshold_rad)),
                "n_steps": len(steps),
                "median_step_m": float(np.median(steps)),
                **powerlaw,
                **msd,
            }
        )
        pooled_steps.append(steps)

        # The manuscript crossover analysis used the longest non-surface run
        # of the whole dive and max_fraction=0.5.
        nonsurface_indices = _longest_true_run(xyz[:, 2] >= SURFACE_THRESHOLD_M)
        if len(nonsurface_indices) >= MIN_SAMPLES:
            nonsurface = xyz[nonsurface_indices]
            curve = msd_curve(
                nonsurface,
                fs_hz=row.sampling_rate_hz,
                max_fraction=0.5,
            )
            result = {
                "trajectory_id": row.trajectory_id,
                "individual_id": row.individual_id,
            }
            for name, (lower, upper) in windows.items():
                upper_effective = (
                    upper
                    if upper is not None
                    else 0.5 * len(nonsurface) / row.sampling_rate_hz
                )
                result[name] = loglog_slope(
                    curve, min_lag_s=lower, max_lag_s=upper_effective
                )["alpha_msd"]
            timescale_rows.append(result)

    per_dive = pd.DataFrame(per_dive_rows)
    timescale = pd.DataFrame(timescale_rows)
    if per_dive.empty:
        return per_dive, {}, timescale

    all_steps = np.concatenate(pooled_steps)
    pooled_fit = fit_powerlaw(all_steps)
    per_individual = per_dive.groupby("individual_id")["mu"].median()
    summary = {
        "n_dives": int(len(per_dive)),
        "n_individuals": int(per_dive["individual_id"].nunique()),
        "mu_dive_median": float(per_dive["mu"].median()),
        "mu_individual_median": float(per_individual.median()),
        "mu_pooled": float(pooled_fit["mu"]),
        "alpha_dive_median": float(per_dive["alpha_msd"].median()),
        "fraction_superdiffusive": float((per_dive["alpha_msd"] > 1).mean()),
    }
    for column in windows:
        summary[f"{column}_median"] = float(timescale[column].median())
    return per_dive, summary, timescale


def analyze_trajectories(
    trajectories: pd.DataFrame,
    phase: str | None = "foraging",
    threshold_rad: float = TURN_THRESHOLD_RAD,
) -> pd.DataFrame:
    """Convenience analysis for safe long-form trajectory tables.

    The release itself uses compact NPZ archives through :func:`analyze_release`;
    this helper is useful for tests and user-supplied derived tables.
    """
    data = (
        trajectories
        if phase is None or "phase" not in trajectories
        else trajectories[trajectories["phase"] == phase]
    )
    rows = []
    for trajectory_id, group in data.groupby("trajectory_id", sort=False):
        group = group.sort_values("time_s")
        xyz = group[["x_m", "y_m", "z_m"]].to_numpy()
        steps = step_lengths(xyz, threshold_rad)
        rows.append(
            {
                "trajectory_id": trajectory_id,
                "n_samples": len(group),
                "n_turning_points": len(turning_points(xyz, threshold_rad)),
                "n_steps": len(steps),
                "median_step_m": (
                    float(np.median(steps)) if len(steps) else np.nan
                ),
                **fit_powerlaw(steps),
                **loglog_slope(msd_curve(xyz)),
            }
        )
    return pd.DataFrame(rows)


def summarize_reconstruction_error(errors: pd.DataFrame) -> pd.DataFrame:
    """Summarize an already-derived, pseudonymized GPS-error table."""
    required = {"trajectory_id", "error_m"}
    missing = required - set(errors.columns)
    if missing:
        raise ValueError(f"error summary is missing: {sorted(missing)}")
    values = errors.copy()
    values["error_m"] = pd.to_numeric(values["error_m"], errors="raise")
    if (
        (values["error_m"] < 0).any()
        or values["error_m"].isna().any()
        or not np.isfinite(values["error_m"]).all()
    ):
        raise ValueError("error_m must be finite and non-negative")
    grouping = (
        ["reconstruction_method"]
        if "reconstruction_method" in values
        else []
    )
    return (
        values.groupby(grouping, dropna=False)["error_m"]
        .agg(
            n="count",
            median_error_m="median",
            mean_error_m="mean",
            q25_error_m=lambda x: x.quantile(0.25),
            q75_error_m=lambda x: x.quantile(0.75),
        )
        .reset_index()
    )
