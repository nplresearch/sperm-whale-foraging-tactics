import numpy as np
import pandas as pd
from trajectory.analysis import analyze_trajectories, msd_curve, step_lengths, summarize_reconstruction_error, turning_points


def test_turning_points_match_production_without_added_endpoints():
    path = np.array([[0,0,0],[1,0,0],[2,0,0],[2,1,0],[2,2,0]], float)
    points = turning_points(path, threshold_rad=.2)
    assert points.tolist() == [3]
    # One turn is not enough to define a between-turn step.
    assert step_lengths(path, .2).size == 0


def test_multiple_turns_produce_positive_steps():
    path = np.array(
        [[0,0,0],[1,0,0],[2,0,0],[2,1,0],[2,2,0],[1,2,0],[0,2,0]],
        float,
    )
    assert np.all(step_lengths(path, .2) > 0)


def test_msd_curve_and_per_trajectory_analysis():
    n=100; t=np.arange(n, dtype=float)
    data=pd.DataFrame({"trajectory_id":"D01", "individual_id":"W01", "dive_id":"D01", "time_s":t, "x_m":t, "y_m":0., "z_m":0., "phase":"foraging"})
    curve=msd_curve(data[["x_m","y_m","z_m"]].to_numpy(), fs_hz=1.0)
    assert (curve.msd_m2 > 0).all()
    result=analyze_trajectories(data, threshold_rad=.2)
    assert len(result)==1 and result.loc[0,"n_samples"] == n


def test_reconstruction_error_summary_is_aggregate_ready():
    errors = pd.DataFrame({"trajectory_id":["D01", "D02"], "error_m":[2., 4.], "reconstruction_method":["method_a"]*2})
    summary = summarize_reconstruction_error(errors)
    assert summary.loc[0, "median_error_m"] == 3. and summary.loc[0, "n"] == 2
