from __future__ import annotations

from copy import deepcopy


KICKOFF_FOLLOWUP_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "kfollow_001",
        "experiment_name": "SGDFNet_KickoffFollowup_TFSegLocal_V1",
        "instance_slug": "kfollow_001_tf_seg_local",
        "stage": "J3_or_new_point_signal_family",
        "branch": "kickoff_time_frequency_point_signal",
        "hypothesis": "time-frequency moving-average features may work better when paired with same-hour local context after the first kickoff rejection.",
        "changed_factor": "tf_moving_average_plus_segment_local_enabled",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_segment_local_stats": True,
            }
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "kfollow_002",
        "experiment_name": "SGDFNet_KickoffFollowup_TFPressureSegLocal_V1",
        "instance_slug": "kfollow_002_tf_pressure_seg_local",
        "stage": "J3_or_new_point_signal_family",
        "branch": "kickoff_time_frequency_point_signal",
        "hypothesis": "time-frequency residuals may need both forecast-pressure interactions and same-hour local context to improve 9_16 raw error after kickoff failure.",
        "changed_factor": "tf_moving_average_plus_pressure_plus_segment_local_enabled",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            }
        },
    },
]


def list_kickoff_followup_candidates() -> list[dict]:
    return deepcopy(KICKOFF_FOLLOWUP_CANDIDATES)
