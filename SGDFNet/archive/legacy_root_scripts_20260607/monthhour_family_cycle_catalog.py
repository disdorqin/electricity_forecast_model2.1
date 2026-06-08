from __future__ import annotations

from copy import deepcopy


MONTHHOUR_FAMILY_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "mhfam_001",
        "experiment_name": "SGDFNet_MonthHour_TFPressure_V1",
        "instance_slug": "mhfam_001_month_hour_bias",
        "stage": "J5_or_month_hour_calibration_family",
        "branch": "tf_pressure_month_hour_calibration",
        "hypothesis": "month-hour bias calibration on top of TF+pressure may capture seasonally concentrated risk-hour residuals better than plain hour bias",
        "changed_factor": "month_hour_bias_risk_extended_on_tf_pressure",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
            "calibration_mode": "month_hour_bias",
            "calibration_hour_scope": "risk_extended",
            "calibration_month_bucket_mode": "season",
            "calibration_segments": ["9_16"],
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "mhfam_002",
        "experiment_name": "SGDFNet_MonthHour_TFPressureRecent14_V1",
        "instance_slug": "mhfam_002_month_hour_bias_recent14",
        "stage": "J5_or_month_hour_calibration_family",
        "branch": "tf_pressure_month_hour_calibration",
        "hypothesis": "if season-hour calibration is too stale, a recent-14-day month-hour calibration on top of TF+pressure may respond better to evolving month-hour drift",
        "changed_factor": "month_hour_bias_risk_extended_on_tf_pressure_recent14",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
            "calibration_mode": "month_hour_bias",
            "calibration_hour_scope": "risk_extended",
            "calibration_month_bucket_mode": "season",
            "calibration_recent_days": 14,
            "calibration_segments": ["9_16"],
        },
    },
]


def list_monthhour_family_candidates() -> list[dict]:
    return deepcopy(MONTHHOUR_FAMILY_CANDIDATES)
