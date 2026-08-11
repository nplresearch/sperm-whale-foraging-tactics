"""Small command-line runner for the derived DSWP event-level analysis."""
from pathlib import Path
import argparse
import pandas as pd
from .io import load_buzz_events
from .classification import attach_labels
from .statistics import compare_groups, markov_leave_subset_out, markov_with_ci

DEFAULT_METRICS = ("avg_vertical_speed_m_s", "avg_roll_speed_deg_s", "avg_depth_m",
                   "median_click_rate_hz", "pre_buzz_vertical_velocity_m_s",
                   "post_buzz_pause_s", "straightness_before_20m", "interbuzz_dt_s")

def run(input_path, output_dir, *, classifier="gmm", n_boot=2000):
    """Write reproducible labels, contrasts, and Markov table from safe input."""
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    events = attach_labels(load_buzz_events(input_path), method=classifier)
    events.to_csv(output / "buzz_events_labelled.csv", index=False)
    rows = [compare_groups(events, metric) for metric in DEFAULT_METRICS if metric in events]
    pd.DataFrame(rows).to_csv(output / "buzz_group_contrasts.csv", index=False)
    markov_leave_subset_out(events).to_csv(
        output / "buzz_markov_transitions.csv", index=False
    )
    markov_with_ci(events, n_boot=n_boot).to_csv(
        output / "buzz_markov_dive_bootstrap.csv", index=False
    )
    return events

def main():
    parser = argparse.ArgumentParser(description="Run DSWP buzz analyses on a derived event table only.")
    parser.add_argument("input", help="CSV/Parquet of sanitized derived buzz events")
    parser.add_argument("output", help="directory for derived analytical results")
    parser.add_argument("--classifier", choices=("gmm", "corner"), default="gmm")
    parser.add_argument("--n-boot", type=int, default=2000)
    args = parser.parse_args(); run(args.input, args.output, classifier=args.classifier, n_boot=args.n_boot)

if __name__ == "__main__": main()
