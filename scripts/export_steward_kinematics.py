#!/usr/bin/env python3
"""Export per-buzz and per-dive kinematic summaries from the DSWP tag structs.

This is a data-steward export, not part of the public analysis run. It reads
the restricted per-deployment tag structs (25-Hz depth, pitch, heading, dive
and buzz timing) and the internal buzz table, verifies row-for-row that the
internal table is the source of the public buzz events, and writes only:

* ``buzz_kinematics.csv``: one row per public ``event_id``;
* ``dive_kinematics.csv``: one row per public ``dive_id``;
* ``deployment_kinematics.csv``: one row per public ``deployment_id``;
* ``buzz_kinematic_profiles.csv``: 2-s bins from -20 to +20 s around each
  public buzz onset.

No source identifiers, crosswalk, sensor time series, locations or private
paths are written. Measures are defined in ``src/dswp/kinematics.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio
from scipy.signal import butter, find_peaks, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dswp.kinematics import centered_mean, ocdr_speed, stroke_oscillation  # noqa: E402

PRE_S = 10.0


def load_tag(path: Path):
    whale = sio.loadmat(path, squeeze_me=True, struct_as_record=False)["whale"]
    mv = whale.Movement
    fs = float(mv.SamplingRate)
    channels = [
        np.atleast_1d(np.asarray(getattr(mv, f), float)) for f in ("Depth", "Pitch", "Heading")
    ]
    n = max(len(c) for c in channels)
    # Channels share t=0 at recording start; shorter ones end earlier (NaN-padded).
    # Two deployments lack orientation (one also lacks depth): those stay NaN.
    depth, pitch, heading = (
        np.concatenate([c, np.full(n - len(c), np.nan)]) if len(c) > 1 else np.full(n, np.nan)
        for c in channels
    )
    return whale, fs, depth, pitch, heading


def _scalar(value):
    a = np.asarray(value, float).ravel()
    return float(a[0]) if a.size == 1 else np.nan  # empty on incomplete last dives


def dive_table(whale) -> pd.DataFrame:
    fields = ("DiveStart", "DiveEnd", "BottomStart", "BottomEnd", "DepthMax")
    return pd.DataFrame(
        [{f: _scalar(getattr(d, f)) for f in fields} for d in np.atleast_1d(whale.Dives)]
    )


def _segment_index(src, origin, fs):
    return origin + np.round(np.asarray(src.time_segment, float) * fs).astype(int)


def depth_matches(src, origin, fs, depth):
    idx = _segment_index(src, origin, fs)
    stored = np.asarray(src.depth_segment, float)
    if idx.min() < 0 or idx.max() >= len(depth) or stored.size != idx.size:
        return False
    both = np.isfinite(stored) & np.isfinite(depth[idx])
    return bool(both.any() and np.max(np.abs(depth[idx][both] - stored[both])) < 1e-6)


def dive_origin(src, dive_start_s, fs, depth, search=250):
    """Raw index of dive-relative t=0: exact match of the stored depth segment."""
    base = int(round(dive_start_s * fs))
    for off in sorted(range(-search, search + 1), key=abs):
        if depth_matches(src, base + off, fs, depth):
            return base + off
    return None


def pitch_status(src, origin, fs, pitch):
    """'exact', 'offset180' (internal table shifted by 180 deg), 'absent' or 'differs'."""
    idx = _segment_index(src, origin, fs)
    stored = np.asarray(src.pitch_segment, float)
    if stored.size != idx.size or idx.max() >= len(pitch):
        return "absent" if stored.size == 0 else "differs"
    both = np.isfinite(stored) & np.isfinite(pitch[idx])
    if not both.any():
        return "absent"
    diff = stored[both] - pitch[idx][both]
    if np.max(np.abs(diff)) < 1e-6:
        return "exact"
    if np.max(np.abs(np.abs(diff) - 180.0)) < 1e-6:
        return "offset180"
    return "differs"


def rms(x):
    x = x[np.isfinite(x)]
    return float(np.sqrt(np.mean(x**2))) if len(x) else np.nan


def summarize(prefix, sl, series):
    out = {}
    pitch = series["pitch"][sl]
    out[f"{prefix}_pitch_deg"] = float(np.nanmean(pitch)) if len(pitch) else np.nan
    out[f"{prefix}_abs_pitch_deg"] = float(np.nanmean(np.abs(pitch))) if len(pitch) else np.nan
    out[f"{prefix}_vertical_speed_m_s"] = float(np.nanmean(np.abs(series["rate"][sl])))
    for thr in (45, 30):
        v = series[f"ocdr{thr}"][sl]
        cover = np.isfinite(v)
        out[f"{prefix}_ocdr{thr}_coverage"] = float(cover.mean()) if len(v) else np.nan
        out[f"{prefix}_ocdr{thr}_speed_m_s"] = float(v[cover].mean()) if cover.any() else np.nan
    out[f"{prefix}_stroke_rms_deg"] = rms(series["stroke"][sl])
    return out


PROFILE_BINS_S = np.arange(-20.0, 20.0 + 1e-9, 2.0)  # 2-s bins, as the roll-speed panel


def profile_rows(event_id, onset_index, fs, series):
    """Buzz-centred 2-s bin means of measured kinematics (NaN where invalid)."""
    rows = []
    for left in PROFILE_BINS_S[:-1]:
        a = onset_index + int(round(left * fs))
        b = a + int(round(2.0 * fs))
        if a < 0 or b > len(series["pitch"]):
            continue
        row = {"event_id": event_id, "bin_start_s": left}
        for name in ("ocdr45", "ocdr30"):
            v = series[name][a:b]
            row[f"{name}_speed_m_s"] = float(np.nanmean(v)) if np.isfinite(v).any() else np.nan
        row["vertical_velocity_m_s"] = float(np.nanmean(series["rate"][a:b]))
        p = series["pitch"][a:b]
        row["pitch_deg"] = float(np.nanmean(p)) if np.isfinite(p).any() else np.nan
        row["stroke_rms_deg"] = rms(series["stroke"][a:b])
        rows.append(row)
    return rows


def descent_stroke_period(whale, fs, pitch):
    """Stroke period (s) from the autocorrelation of high-passed descent pitch.

    This checks that the 0.1-0.4 Hz stroke band used for the effort index
    contains each deployment's stroke rhythm. NaN if no rhythm is found.
    """
    sos = butter(2, 0.03, btype="highpass", fs=fs, output="sos")
    curves = []
    for dive in dive_table(whale).dropna(subset=["DiveStart", "BottomStart"]).itertuples():
        seg = pitch[int((dive.DiveStart + 30) * fs) : int((dive.BottomStart - 10) * fs)]
        if len(seg) < 120 * fs or not np.isfinite(seg).all():
            continue
        x = sosfiltfilt(sos, seg)
        x = x - x.mean()
        ac = np.correlate(x, x, "full")[len(x) - 1 :][: int(30 * fs)]
        curves.append(ac / ac[0])
    if not curves:
        return np.nan
    peaks, _ = find_peaks(np.mean(curves, axis=0), prominence=0.05)
    peaks = peaks[peaks > 2 * fs]
    return float(peaks[0] / fs) if len(peaks) else np.nan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_buzz_pickle", type=Path)
    parser.add_argument("source_tag_dir", type=Path)
    parser.add_argument("public_buzz_events_csv", type=Path)
    parser.add_argument("output_data_dir", type=Path)
    args = parser.parse_args()

    source = pd.read_pickle(args.source_buzz_pickle)[
        [
            "tag_id", "dive_number", "buzzes_times", "duration_start",
            "avg_speed_3d_during_buzz", "time_segment", "pitch_segment", "depth_segment",
        ]
    ].reset_index(drop=True)
    public = pd.read_csv(args.public_buzz_events_csv).sort_values("event_id")
    public = public.reset_index(drop=True)

    # The public events were exported from this table in row order. Verify it.
    if len(source) != len(public):
        raise SystemExit("row counts differ; refusing to build a crosswalk")
    checks = {
        "ramp-up": (source.duration_start, public.ramp_up_duration_s),
        "3-D speed": (source.avg_speed_3d_during_buzz, public.avg_speed_3d_m_s),
        "duration": (
            source.buzzes_times.map(lambda t: t[-1] - t[0]),
            public.buzz_end_s - public.buzz_start_s,
        ),
    }
    for name, (a, b) in checks.items():
        if not np.allclose(a.astype(float), b.astype(float), atol=1e-6, equal_nan=True):
            raise SystemExit(f"crosswalk check failed on {name}")

    buzz_rows, dive_rows, dep_rows, prof_rows = [], [], [], []
    pitch_log: dict[str, int] = {}
    for tag, rows in source.groupby("tag_id", sort=True):
        whale, fs, depth, pitch, heading = load_tag(args.source_tag_dir / f"{tag}.mat")
        series = {
            "pitch": pitch,
            "rate": centered_mean(np.gradient(depth) * fs, int(fs)),
            "ocdr45": ocdr_speed(depth, pitch, fs, min_pitch_deg=45.0),
            "ocdr30": ocdr_speed(depth, pitch, fs, min_pitch_deg=30.0),
            "stroke": stroke_oscillation(pitch, heading, fs),
        }
        pub = public.loc[rows.index]
        dep_rows.append({
            "deployment_id": pub.deployment_id.iloc[0],
            "sampling_rate_hz": fs,
            "descent_stroke_period_s": descent_stroke_period(whale, fs, pitch),
        })

        dives = dive_table(whale)
        if not np.isfinite(depth).any():
            for i in rows.index:
                buzz_rows.append({"event_id": public.event_id[i]})
            continue
        origins = {}
        for dive_number, group in rows.groupby("dive_number"):
            origin = dive_origin(group.iloc[0], dives.DiveStart[int(dive_number)], fs, depth)
            if origin is None or not all(
                depth_matches(src, origin, fs, depth) for _, src in group.iterrows()
            ):
                raise SystemExit("could not align a dive to the tag record exactly")
            origins[dive_number] = origin
            for _, src in group.iterrows():
                status = pitch_status(src, origin, fs, pitch)
                pitch_log[status] = pitch_log.get(status, 0) + 1
        for i, src in rows.iterrows():
            # Buzz times are seconds since the dive start used by the buzz table.
            t0, t1 = float(src.buzzes_times[0]), float(src.buzzes_times[-1])
            origin = origins[src.dive_number]
            i0, i1 = origin + int(np.floor(t0 * fs)), origin + int(np.floor(t1 * fs)) + 1
            row = {"event_id": public.event_id[i]}
            row.update(summarize("buzz", slice(i0, i1), series))
            row.update(summarize("pre", slice(max(0, i0 - int(PRE_S * fs)), i0), series))
            buzz_rows.append(row)
            prof_rows.extend(profile_rows(public.event_id[i], i0, fs, series))

        for (dive_number, dive_id), _ in pub.assign(dive_number=rows.dive_number).groupby(
            ["dive_number", "dive_id"]
        ):
            dive = dives.iloc[int(dive_number)]
            nxt = dives.iloc[int(dive_number) + 1] if int(dive_number) + 1 < len(dives) else None
            if np.isfinite(dive.BottomStart) and np.isfinite(dive.BottomEnd):
                bottom = slice(int(dive.BottomStart * fs), int(dive.BottomEnd * fs))
            else:
                bottom = slice(0, 0)
            dive_rows.append({
                "dive_id": dive_id,
                "deployment_id": pub.deployment_id.iloc[0],
                "dive_duration_s": float(dive.DiveEnd - dive.DiveStart),
                "bottom_duration_s": float(dive.BottomEnd - dive.BottomStart),
                # Phase boundaries relative to dive start (the public buzz time base).
                "bottom_start_s": float(dive.BottomStart - dive.DiveStart),
                "bottom_end_s": float(dive.BottomEnd - dive.DiveStart),
                "max_depth_m": float(dive.DepthMax),
                "interdive_interval_s": (
                    float(nxt.DiveStart - dive.DiveEnd) if nxt is not None else np.nan
                ),
                "bottom_stroke_rms_deg": rms(series["stroke"][bottom]),
                "bottom_ocdr45_coverage": (
                    float(np.isfinite(series["ocdr45"][bottom]).mean())
                    if bottom.stop > bottom.start else np.nan
                ),
            })

    out = args.output_data_dir
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(buzz_rows).sort_values("event_id").to_csv(out / "buzz_kinematics.csv", index=False)
    pd.DataFrame(dive_rows).sort_values("dive_id").to_csv(out / "dive_kinematics.csv", index=False)
    pd.DataFrame(prof_rows).sort_values(["event_id", "bin_start_s"]).to_csv(
        out / "buzz_kinematic_profiles.csv", index=False, float_format="%.5g"
    )
    pd.DataFrame(dep_rows).sort_values("deployment_id").to_csv(
        out / "deployment_kinematics.csv", index=False
    )
    print(f"wrote {len(buzz_rows)} buzzes, {len(dive_rows)} dives, {len(dep_rows)} deployments")
    print("internal-table pitch vs tag record, per buzz:", pitch_log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
