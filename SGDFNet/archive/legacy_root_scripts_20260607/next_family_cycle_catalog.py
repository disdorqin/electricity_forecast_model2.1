from __future__ import annotations

from copy import deepcopy


NEXT_FAMILY_CYCLE_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "nextfam_001",
        "experiment_name": "SGDFNet_NextFamily_TFPressureHourBias_V1",
        "instance_slug": "nextfam_001_tf_pressure_hour_bias",
        "stage": "J4_or_localized_calibration_family",
        "branch": "tf_pressure_risk_hour_localized_calibration",
        "hypothesis": "TF+pressure features may need risk-hour localized hour-bias calibration to translate capped/tail gains into raw 9_16 improvement",
        "changed_factor": "hour_bias_risk_extended_on_tf_pressure",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
            "calibration_mode": "hour_bias",
            "calibration_hour_scope": "risk_extended",
            "calibration_segments": ["9_16"],
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "nextfam_002",
        "experiment_name": "SGDFNet_NextFamily_TFPressureSegmentHourBias_V1",
        "instance_slug": "nextfam_002_tf_pressure_segment_hour_bias",
        "stage": "J4_or_localized_calibration_family",
        "branch": "tf_pressure_risk_hour_localized_calibration",
        "hypothesis": "If plain risk-hour bias is too coarse, segment-hour bias on top of TF+pressure may better focus 9_16 repair",
        "changed_factor": "segment_hour_bias_risk_extended_on_tf_pressure",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
            "calibration_mode": "segment_hour_bias",
            "calibration_hour_scope": "risk_extended",
            "calibration_segments": ["9_16"],
        },
    },
]


def list_next_family_cycle_candidates() -> list[dict]:
    return deepcopy(NEXT_FAMILY_CYCLE_CANDIDATES)
