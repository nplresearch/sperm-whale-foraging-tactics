"""Deterministic, release-safe buzz boundary and threshold diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dswp.io import validate_buzz_events

WINDOW_S = 0.3
WINDOW_STEP_S = 0.05
SMOOTH_WINDOW = 5
PRODUCTION_THRESHOLD = 0.7
THRESHOLDS = np.round(np.arange(0.05, 1.0, 0.05), 2)


def load_clicks(path: str | Path) -> pd.DataFrame:
    """Load derived click times and require one event-local time axis."""
    frame = pd.read_csv(path)
    required = {"event_id", "click_index", "click_time_from_buzz_start_s"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"click table is missing {sorted(missing)}")
    out = frame.copy()
    out["click_time_from_buzz_start_s"] = pd.to_numeric(
        out["click_time_from_buzz_start_s"], errors="raise"
    )
    out["click_index"] = pd.to_numeric(out["click_index"], errors="raise").astype(int)
    if (out["click_time_from_buzz_start_s"] < 0).any():
        raise ValueError("click times must be non-negative")
    return out.sort_values(["event_id", "click_index"], kind="stable").reset_index(drop=True)


def click_rate_series(
    click_times: np.ndarray,
    window_s: float = WINDOW_S,
    step_s: float = WINDOW_STEP_S,
    smooth_window: int = SMOOTH_WINDOW,
) -> pd.DataFrame:
    """Reproduce the production symmetric-window, smoothed click-rate series."""
    clicks = np.sort(np.asarray(click_times, dtype=float))
    if clicks.size < 2 or window_s <= 0 or step_s <= 0 or smooth_window < 1:
        raise ValueError("need at least two clicks and positive window parameters")
    if not np.isfinite(clicks).all():
        raise ValueError("click times must be finite")
    time_s = np.arange(clicks[0], clicks[-1], step_s)
    if not len(time_s):
        time_s = np.array([clicks[0]])
    half_window = window_s / 2.0
    left = np.searchsorted(clicks, time_s - half_window, side="left")
    right = np.searchsorted(clicks, time_s + half_window, side="left")
    raw_rate = (right - left) / window_s
    kernel = np.ones(int(smooth_window), dtype=float) / smooth_window
    smoothed_rate = np.convolve(raw_rate, kernel, mode="same")
    # NumPy's ``same`` mode follows the longer input; real buzzes are longer
    # than the kernel, but keep small synthetic/review examples well-defined.
    if len(smoothed_rate) != len(raw_rate):
        offset = (len(smoothed_rate) - len(raw_rate)) // 2
        smoothed_rate = smoothed_rate[offset : offset + len(raw_rate)]
    return pd.DataFrame({"time_s": time_s, "raw_rate_hz": raw_rate, "rate_hz": smoothed_rate})


def _ici_cv(values: np.ndarray) -> float:
    ici = np.diff(np.sort(np.asarray(values, dtype=float)))
    return (
        float(np.std(ici, ddof=1) / np.mean(ici)) if len(ici) >= 2 and np.mean(ici) > 0 else np.nan
    )


def _segment_from_rate(
    clicks: np.ndarray, rates: pd.DataFrame, threshold: float
) -> dict[str, float | int]:
    # This intentionally preserves the result-producing formula in the SI:
    # alpha * (maximum - minimum), without adding the minimum back.
    cutoff = threshold * (rates["rate_hz"].max() - rates["rate_hz"].min())
    mask = rates["rate_hz"].to_numpy() >= cutoff
    regions = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(int))).reshape(-1, 2)
    if not len(regions):
        plateau_start = plateau_end = np.nan
        plateau_clicks = np.array([], dtype=float)
    else:
        start_index, stop_index = regions[np.argmax(regions[:, 1] - regions[:, 0])]
        plateau_start = float(rates["time_s"].iloc[start_index])
        # The source implementation uses the first grid point after the region.
        plateau_end = float(rates["time_s"].iloc[min(stop_index, len(rates) - 1)])
        plateau_clicks = clicks[(clicks >= plateau_start) & (clicks <= plateau_end)]
    start_s, end_s = float(clicks[0]), float(clicks[-1])
    return {
        "start_s": start_s,
        "plateau_start_s": plateau_start,
        "plateau_end_s": plateau_end,
        "end_s": end_s,
        "ramp_s": plateau_start - start_s,
        "plateau_s": plateau_end - plateau_start,
        "terminal_s": end_s - plateau_end,
        "threshold": float(threshold),
        "cutoff_hz": float(cutoff),
        "n_plateau_clicks": int(len(plateau_clicks)),
        "plateau_ici_cv": _ici_cv(plateau_clicks),
    }


def segment_clicks(
    click_times: np.ndarray,
    threshold: float = PRODUCTION_THRESHOLD,
    window_s: float = WINDOW_S,
    step_s: float = WINDOW_STEP_S,
    smooth_window: int = SMOOTH_WINDOW,
) -> dict[str, float | int]:
    """Segment ramp, plateau, and terminal phases using production settings.

    This reproduces the derived-click implementation; it does not replace the
    reviewed boundaries distributed in ``buzz_events.csv``.
    """
    clicks = np.sort(np.asarray(click_times, dtype=float))
    if clicks.size < 2 or not 0 < threshold < 1:
        raise ValueError("need two clicks and threshold in (0, 1)")
    rates = click_rate_series(clicks, window_s, step_s, smooth_window)
    return _segment_from_rate(clicks, rates, threshold)


def threshold_sweep(
    clicks: pd.DataFrame,
    thresholds=None,
    window_s: float = WINDOW_S,
    step_s: float = WINDOW_STEP_S,
    smooth_window: int = SMOOTH_WINDOW,
) -> pd.DataFrame:
    """Return plateau duration and ICI regularity for every buzz and alpha."""
    thresholds = THRESHOLDS if thresholds is None else np.asarray(thresholds, float)
    rows = []
    for event_id, group in clicks.groupby("event_id", sort=True):
        values = group["click_time_from_buzz_start_s"].to_numpy()
        rates = click_rate_series(values, window_s, step_s, smooth_window)
        for threshold in thresholds:
            rows.append({"event_id": event_id, **_segment_from_rate(values, rates, threshold)})
    return pd.DataFrame(rows)


def null_window_diagnostic(
    clicks: pd.DataFrame,
    *,
    thresholds=None,
    n_windows: int = 20,
    seed: int = 42,
    window_s: float = WINDOW_S,
    step_s: float = WINDOW_STEP_S,
    smooth_window: int = SMOOTH_WINDOW,
) -> pd.DataFrame:
    """Compare each plateau with uniformly drawn same-duration buzz windows.

    One row is returned per buzz and threshold. ``excess_regularity`` is the
    median null-window ICI CV minus the observed plateau ICI CV, exactly as
    defined in the SI caption.
    """
    if n_windows < 1:
        raise ValueError("n_windows must be positive")
    thresholds = THRESHOLDS if thresholds is None else np.asarray(thresholds, float)
    rng = np.random.default_rng(seed)
    rows = []
    for event_id, group in clicks.groupby("event_id", sort=True):
        values = group["click_time_from_buzz_start_s"].to_numpy()
        rates = click_rate_series(values, window_s, step_s, smooth_window)
        buzz_start, buzz_end = float(values[0]), float(values[-1])
        for threshold in thresholds:
            segment = _segment_from_rate(values, rates, threshold)
            duration = float(segment["plateau_s"])
            null_cvs = []
            if np.isfinite(duration) and 0 < duration <= buzz_end - buzz_start:
                latest_start = buzz_end - duration
                starts = rng.uniform(buzz_start, latest_start, size=n_windows)
                for start in starts:
                    window_clicks = values[(values >= start) & (values <= start + duration)]
                    null_cvs.append(_ici_cv(window_clicks))
            valid_null = np.asarray(null_cvs, dtype=float)
            median_null = (
                float(np.nanmedian(valid_null)) if np.isfinite(valid_null).any() else np.nan
            )
            plateau_cv = float(segment["plateau_ici_cv"])
            rows.append(
                {
                    "event_id": event_id,
                    "threshold": float(threshold),
                    "plateau_duration_s": duration,
                    "plateau_ici_cv": plateau_cv,
                    "median_null_ici_cv": median_null,
                    "excess_regularity": median_null - plateau_cv,
                    "n_valid_null_windows": int(np.isfinite(valid_null).sum()),
                    "n_windows": int(n_windows),
                    "seed": int(seed),
                }
            )
    return pd.DataFrame(rows)


def threshold_summary(sweep: pd.DataFrame, nulls: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the three SI threshold diagnostics across buzzes."""
    grouped = sweep.groupby("threshold")["plateau_ici_cv"]
    summary = grouped.agg(
        median_plateau_ici_cv="median",
        q25_plateau_ici_cv=lambda x: x.quantile(0.25),
        q75_plateau_ici_cv=lambda x: x.quantile(0.75),
        n_buzzes="count",
    ).reset_index()
    summary["d_median_cv_d_threshold"] = (
        np.gradient(summary["median_plateau_ici_cv"], summary["threshold"])
        if len(summary) > 1
        else np.nan
    )
    excess = (
        nulls.groupby("threshold")["excess_regularity"]
        .median()
        .rename("median_excess_regularity")
        .reset_index()
    )
    return summary.merge(excess, on="threshold", validate="one_to_one")


def cohort_summary(deployments: pd.DataFrame, buzzes: pd.DataFrame) -> dict:
    """Return the release cohort counts used by the dataset notebook."""
    events = validate_buzz_events(buzzes, require_classifier=False)
    return {
        "deployments": int(len(deployments)),
        "individuals": int(deployments.individual_id.nunique()),
        "dives": int(pd.to_numeric(deployments["n_dives"], errors="raise").sum()),
        "buzzes": int(len(events)),
    }
