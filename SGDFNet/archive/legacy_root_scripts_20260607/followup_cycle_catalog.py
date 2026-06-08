from __future__ import annotations

from copy import deepcopy


FOLLOWUP_CYCLE_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "followup_001",
        "experiment_name": "SGDFNet_Followup_TFMovingAverage_V1",
        "instance_slug": "followup_001_tf_moving_average",
        "stage": "J3_or_new_point_signal_family",
        "branch": "time_frequency_point_signal",
        "hypothesis": "moving-average low/high-frequency delta residual features may repair unresolved 9_16 raw-error concentration without changing the backbone",
        "changed_factor": "tf_moving_average_features_enabled",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
            }
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "followup_002",
        "experiment_name": "SGDFNet_Followup_TFMovingAveragePlusPressure_V1",
        "instance_slug": "followup_002_tf_moving_average_plus_pressure",
        "stage": "J3_or_new_point_signal_family",
        "branch": "time_frequency_point_signal",
        "hypothesis": "time-frequency moving-average residual features may need forecast-pressure interactions to translate tail signal into 9_16 point improvement",
        "changed_factor": "tf_moving_average_plus_forecast_pressure_enabled",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            }
        },
    },
]


def list_followup_cycle_candidates() -> list[dict]:
    return deepcopy(FOLLOWUP_CYCLE_CANDIDATES)
