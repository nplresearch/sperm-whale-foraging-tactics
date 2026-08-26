"""Trajectory-based DSWP buzz-energy calculation used in the manuscript.

This module implements the model described in the current Methods and
Supplementary Information. It reproduces the reported whale-level means
(1.28 MJ for Type A and 9.07 MJ for Type B) from reconstructed trajectory
speeds over the full buzz, parasite-drag work, positive tangential-acceleration
work, and resting metabolism. The model is inspired by the hydrodynamic
framework of Goldbogen et al. (2019), but it is not a fitted implementation of
their analytical prey-interception model.
"""

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
class EnergyParameters:
    """Fixed parameters in the code path that produced the reported values."""

    body_mass_kg: float = 40_000.0
    body_length_m: float = 12.0
    skull_width_m: float = 1.5
    rho_water_kg_m3: float = 1027.0
    nu_water_m2_s: float = 1.15e-6
    eta_metabolic: float = 0.25
    eta_propulsive: float = 0.75
    tail_heaving_factor: float = 2.5
    depth_factor: float = 1.0
    added_mass_coefficient: float = 0.06
    # Coefficient units are W kg^-b when body mass is supplied in kg.
    resting_a_w: float = 6.72
    resting_mass_exponent: float = 0.68

    @property
    def wetted_area_m2(self):
        return 0.08 * self.body_mass_kg**0.65


def energy_from_speed_series(time_s, speed_m_s, *, parameters=EnergyParameters()) -> dict:
    """Compute one capture-window energy estimate from a derived speed series.

    ``time_s`` is relative to buzz start and ``speed_m_s`` is the released 3-D
    speed magnitude. At least three strictly increasing samples are required.
    Returned work is in J; ``E_total_J`` is metabolic energy.
    """
    t, v = np.asarray(time_s, float), np.asarray(speed_m_s, float)
    if len(t) != len(v) or len(t) < 3 or not np.isfinite(t).all() or not np.isfinite(v).all():
        raise ValueError("time and speed must be equal-length finite arrays with >=3 samples")
    if np.any(np.diff(t) <= 0) or np.any(v < 0):
        raise ValueError("time must increase strictly and speed must be non-negative")
    p = parameters
    acceleration = np.gradient(v, t)
    re = np.maximum(v * p.body_length_m / p.nu_water_m2_s, 1.0)
    ratio = p.skull_width_m / p.body_length_m
    cd = 0.072 * re ** (-0.2) * (1 + 1.5 * ratio**1.5 + 7 * ratio**3)
    parasite = (
        p.tail_heaving_factor
        * p.depth_factor
        * 0.5
        * p.rho_water_kg_m3
        * p.wetted_area_m2
        * cd
        * v**2
    )
    drag_work = float(_integrate_trapezoid(parasite * v, t))
    effective_mass = p.body_mass_kg * (1.0 + p.added_mass_coefficient)
    acceleration_work = float(
        _integrate_trapezoid(np.maximum(0.0, effective_mass * acceleration * v), t)
    )
    mechanical_work = drag_work + acceleration_work
    fluke_metabolic = mechanical_work / (p.eta_metabolic * p.eta_propulsive)
    duration = float(t[-1] - t[0])
    resting = p.resting_a_w * p.body_mass_kg**p.resting_mass_exponent * duration
    total = fluke_metabolic + resting
    return {
        "capture_duration_s": duration,
        "mean_speed_m_s": float(v.mean()),
        "drag_work_J": drag_work,
        "positive_acceleration_work_J": acceleration_work,
        "mechanical_translation_work_J": mechanical_work,
        "E_metabolic_fluking_J": fluke_metabolic,
        "E_metabolic_rest_J": resting,
        "E_total_J": total,
        "mean_metabolic_power_W": total / duration,
        "fluking_to_rest_ratio": fluke_metabolic / resting if resting else np.nan,
    }


def event_energy_from_speed_table(
    samples: pd.DataFrame, *, parameters=EnergyParameters()
) -> pd.DataFrame:
    """Calculate energy per opaque buzz from a safe long-form speed table.

    Required columns: ``deployment_id``, ``dive_id``, ``buzz_order_in_dive``,
    ``capture_time_s`` and ``speed_3d_m_s``.  The capture window must already
    be restricted to the full first-click--last-click interval upstream; no raw
    reconstruction is read or inferred here.
    """
    required = {"deployment_id", "dive_id", "buzz_order_in_dive", "capture_time_s", "speed_3d_m_s"}
    if missing := required - set(samples):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    blocked = [
        c
        for c in samples
        if any(
            x in c.lower()
            for x in ("raw", "audio", "gps", "latitude", "longitude", "whale", "name")
        )
    ]
    if blocked:
        raise ValueError("Unsafe columns in speed summary: " + ", ".join(blocked))
    keys = ["deployment_id", "dive_id", "buzz_order_in_dive"]
    rows = []
    for key, group in samples.groupby(keys, sort=False):
        group = group.sort_values("capture_time_s")
        row = dict(zip(keys, key))
        row.update(
            energy_from_speed_series(
                group.capture_time_s, group.speed_3d_m_s, parameters=parameters
            )
        )
        rows.append(row)
    return pd.DataFrame(rows)


def event_energy_from_trajectories(
    events: pd.DataFrame,
    trajectory_index_csv: str | Path,
    *,
    parameters=EnergyParameters(),
) -> pd.DataFrame:
    """Calculate per-buzz energy directly from released reconstructions.

    The operative interval begins at the first click and ends at the last click.
    Speed is the magnitude of the first difference of the
    pitch-adaptive reconstructed position at the index table's sampling rate,
    matching the trajectory-derived speed used in the manuscript.

    Events without an available reconstruction, valid buzz boundary, or at
    least three retained trajectory samples are omitted and can be audited by
    comparing event IDs against the returned table.
    """
    required = {
        "event_id",
        "trajectory_id",
        "buzz_start_s",
        "buzz_end_s",
    }
    missing = required - set(events)
    if missing:
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
            # Production segmentation used the preceding 25-Hz sample for both
            # acoustic boundaries.
            start = int(np.floor(float(event.buzz_start_s) * fs_hz))
            end = int(np.floor(float(event.buzz_end_s) * fs_hz))
            start = max(0, start)
            end = min(len(xyz) - 1, end)
            if end - start + 1 < 3:
                continue
            segment = xyz[start : end + 1]
            event_speed = np.linalg.norm(np.diff(segment, axis=0), axis=1) * fs_hz
            if not np.isfinite(event_speed).all() or np.any(event_speed < 0):
                continue
            # Speeds live at displacement midpoints. The half-sample offset is
            # immaterial for integration but records the actual support.
            time_s = (np.arange(len(event_speed), dtype=float) + 0.5) / fs_hz
            result = energy_from_speed_series(time_s, event_speed, parameters=parameters)
            result.update(
                {
                    "event_id": event.event_id,
                    "trajectory_id": trajectory_id,
                }
            )
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


def paired_individual_energy(
    events: pd.DataFrame, *, individual_col="individual_id"
) -> pd.DataFrame:
    """Within-individual mean A/B energy used for the manuscript panel.

    ``individual_col`` must identify the biological individual. The default
    uses the publication-safe ``individual_id`` token so repeated deployments
    are pooled as specified in the manuscript.
    """
    need = {individual_col, "buzz_type", "E_total_J"}
    if missing := need - set(events):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    out = events[events.buzz_type.isin(["A", "B"])].pivot_table(
        index=individual_col, columns="buzz_type", values="E_total_J", aggfunc="mean"
    )
    return out.reset_index().rename_axis(None, axis=1)
