"""Aoki et al. (2012) steady-drag locomotor-cost model.

The model is implemented from the equation in the article's Supplementary
Material (doi:10.3354/meps09371):

    P_loc = lambda / (eta_a * eta_p) * 0.5 * rho * S * C_D * U**3

It estimates the metabolic equivalent of work against active swimming drag.
It does not include acceleration, resting metabolism, prey speed, or capture
geometry.  Here it is applied to the same reconstructed 3-D speed samples and
first-click--last-click intervals as the operative DSWP energetic model so
that the two formulations differ in mechanics rather than event selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from trajectory.analysis import load_trajectory


def _integrate_trapezoid(values, coordinates):
    """NumPy 1.x/2.x compatible trapezoidal integration."""
    if hasattr(np, "trapezoid"):
        return np.trapezoid(values, coordinates)
    return np.trapz(values, coordinates)


@dataclass(frozen=True)
class AokiParameters:
    """Parameters for the Aoki steady-drag comparison.

    Aoki et al. used an 8-m whale with a total surface area of 23.7 m2.  The
    comparison reported for DSWP instead uses the same 40,000-kg allometric
    surface area as the operative model, isolating the model-form difference.
    """

    body_mass_kg: float = 40_000.0
    rho_water_kg_m3: float = 1027.0
    drag_coefficient: float = 0.00306
    active_to_passive_drag_ratio: float = 3.0
    aerobic_efficiency: float = 0.25
    propulsive_efficiency: float = 0.75

    @property
    def surface_area_m2(self) -> float:
        return 0.08 * self.body_mass_kg**0.65


def aoki_energy_from_speed_series(
    time_s,
    speed_m_s,
    *,
    parameters: AokiParameters = AokiParameters(),
) -> dict:
    """Return Aoki drag-related locomotor energy for one observed interval."""
    t = np.asarray(time_s, dtype=float)
    v = np.asarray(speed_m_s, dtype=float)
    if len(t) != len(v) or len(t) < 2 or not np.isfinite(t).all() or not np.isfinite(v).all():
        raise ValueError("time and speed must be equal-length finite arrays with >=2 samples")
    if np.any(np.diff(t) <= 0) or np.any(v < 0):
        raise ValueError("time must increase strictly and speed be non-negative")

    p = parameters
    metabolic_power_w = (
        p.active_to_passive_drag_ratio
        / (p.aerobic_efficiency * p.propulsive_efficiency)
        * 0.5
        * p.rho_water_kg_m3
        * p.surface_area_m2
        * p.drag_coefficient
        * v**3
    )
    energy_j = float(_integrate_trapezoid(metabolic_power_w, t))
    duration_s = float(t[-1] - t[0])
    return {
        "capture_duration_s": duration_s,
        "mean_speed_m_s": float(v.mean()),
        "aoki_drag_locomotor_energy_J": energy_j,
        "aoki_mean_locomotor_power_W": energy_j / duration_s,
    }


def event_aoki_energy_from_trajectories(
    events: pd.DataFrame,
    trajectory_index_csv: str | Path,
    *,
    parameters: AokiParameters = AokiParameters(),
) -> pd.DataFrame:
    """Apply the Aoki comparison to released trajectories event by event."""
    required = {"event_id", "trajectory_id", "buzz_start_s", "buzz_end_s"}
    if missing := required - set(events):
        raise ValueError("Missing event columns: " + ", ".join(sorted(missing)))

    index_path = Path(trajectory_index_csv)
    index = pd.read_csv(index_path).set_index("trajectory_id")
    rows = []
    for trajectory_id, group in events.groupby("trajectory_id", sort=False):
        if trajectory_id not in index.index:
            continue
        metadata = index.loc[trajectory_id]
        fs_hz = float(metadata["sampling_rate_hz"])
        xyz = load_trajectory(index_path.parent / metadata["file"])
        for event in group.itertuples(index=False):
            start = max(0, int(np.floor(float(event.buzz_start_s) * fs_hz)))
            end = min(
                len(xyz) - 1,
                int(np.floor(float(event.buzz_end_s) * fs_hz)),
            )
            if end - start + 1 < 3:
                continue
            segment = xyz[start : end + 1]
            speed = np.linalg.norm(np.diff(segment, axis=0), axis=1) * fs_hz
            if not np.isfinite(speed).all() or np.any(speed < 0):
                continue
            time_s = (np.arange(len(speed), dtype=float) + 0.5) / fs_hz
            result = aoki_energy_from_speed_series(time_s, speed, parameters=parameters)
            result.update({"event_id": event.event_id, "trajectory_id": trajectory_id})
            for column in (
                "deployment_id",
                "individual_id",
                "dive_id",
                "buzz_order_in_dive",
                "buzz_type",
            ):
                if hasattr(event, column):
                    result[column] = getattr(event, column)
            rows.append(result)
    return pd.DataFrame(rows)


def paired_individual_aoki(
    events: pd.DataFrame,
    *,
    individual_col: str = "individual_id",
) -> pd.DataFrame:
    """Return paired within-individual Type A and Type B Aoki estimates."""
    required = {
        individual_col,
        "buzz_type",
        "aoki_drag_locomotor_energy_J",
    }
    if missing := required - set(events):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    return (
        events[events["buzz_type"].isin(["A", "B"])]
        .pivot_table(
            index=individual_col,
            columns="buzz_type",
            values="aoki_drag_locomotor_energy_J",
            aggfunc="mean",
        )
        .dropna(subset=["A", "B"])
        .reset_index()
        .rename_axis(None, axis=1)
    )
