from __future__ import annotations

from copy import deepcopy


FRESH_CYCLE_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "fresh_cycle_001",
        "experiment_name": "SGDFNet_FirstExperiment_FeatureRedesign_V1",
        "instance_slug": "fresh_cycle_001_segment_local_stats",
        "stage": "J1_or_new_model_line",
        "branch": "point_signal_redesign",
        "hypothesis": "same-hour local delta and residual context may repair 9_16 raw error concentration",
        "changed_factor": "segment_local_stats_enabled",
        "config_updates": {
            "feature_config": {
                "include_segment_local_stats": True,
            }
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "fresh_cycle_002",
        "experiment_name": "SGDFNet_FreshCycle_ForecastPressure_V1",
        "instance_slug": "fresh_cycle_002_forecast_pressure",
        "stage": "J1_or_new_model_line",
        "branch": "point_signal_redesign",
        "hypothesis": "forecast-side pressure interactions may improve risk-hour and 9_16 mismatch without changing the backbone",
        "changed_factor": "forecast_pressure_interactions_enabled",
        "config_updates": {
            "feature_config": {
                "include_forecast_pressure_interactions": True,
            }
        },
    },
    {
        "sequence_id": 3,
        "experiment_id": "fresh_cycle_003",
        "experiment_name": "SGDFNet_FreshCycle_WeeklyHistory_V1",
        "instance_slug": "fresh_cycle_003_weekly_history",
        "stage": "J1_or_new_model_line",
        "branch": "point_signal_redesign",
        "hypothesis": "weekly recurrence features may stabilize repeated hour-of-week deviations in 9_16 without introducing routing",
        "changed_factor": "weekly_history_enabled",
        "config_updates": {
            "feature_config": {
                "include_weekly_history_features": True,
            }
        },
    },
]


def list_fresh_cycle_candidates() -> list[dict]:
    return deepcopy(FRESH_CYCLE_CANDIDATES)
