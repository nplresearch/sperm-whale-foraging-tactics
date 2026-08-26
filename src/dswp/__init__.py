"""Publication-safe event-level analyses for the DSWP foraging study.

This package deliberately reads *derived* event tables only.  It contains no
loader for audio, GPS, tag sensor streams, MATLAB files, or identifiable study
metadata.
"""

from .aoki import AokiParameters, aoki_energy_from_speed_series
from .classification import (
    classifier_speed_sensitivity,
    classify_extreme_corners,
    classify_gmm,
)
from .energetics import EnergyParameters, energy_from_speed_series, event_energy_from_speed_table
from .io import load_buzz_events, validate_buzz_events
from .pauses import categorize_pauses, pause_association, pause_category_table
from .statistics import compare_groups, markov_with_ci

__all__ = [
    "load_buzz_events",
    "validate_buzz_events",
    "classify_extreme_corners",
    "classify_gmm",
    "classifier_speed_sensitivity",
    "compare_groups",
    "markov_with_ci",
    "EnergyParameters",
    "energy_from_speed_series",
    "event_energy_from_speed_table",
    "categorize_pauses",
    "pause_category_table",
    "pause_association",
    "AokiParameters",
    "aoki_energy_from_speed_series",
]
