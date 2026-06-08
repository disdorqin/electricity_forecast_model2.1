from __future__ import annotations

from copy import deepcopy


KICKOFF_MONTHHOUR_SELECTIVE_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "kmhsel_001",
        "experiment_name": "SGDFNet_KickoffMonthHourSelective_SeasonRisk_V1",
        "instance_slug": "kmhsel_001_monthhour_selective_season_risk",
        "stage": "kickoff_monthhour_selective_family",
        "branch": "kickoff_monthhour_selective_family",
        "hypothesis": "Season-hour selective bias on risk hours should be a cleaner teacher than signed-tail residuals because the diagnostics show stable month-hour concentration in 9_16.",
        "changed_factor": "kickoff_monthhour_selective_season_risk_hours",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "calibration_hours": [9, 10, 11, 14, 15, 16],
            "calibration_segments": ["9_16"],
            "month_bucket_mode": "season",
            "min_group_size": 6,
            "bias_shrinkage": 0.45,
            "bias_cap_abs": 18.0,
            "val_min_delta_mae_gain": 0.20,
            "val_min_rt_capped_smape_gain": 0.05,
            "require_predicted_sign_match": False,
            "predicted_abs_gate_quantile": 0.75,
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "kmhsel_002",
        "experiment_name": "SGDFNet_KickoffMonthHourSelective_SignRisk_V1",
        "instance_slug": "kmhsel_002_monthhour_selective_sign_risk",
        "stage": "kickoff_monthhour_selective_family",
        "branch": "kickoff_monthhour_selective_family",
        "hypothesis": "Adding predicted-sign consistency to the stable month-hour teacher may reduce raw harm while preserving the capped gain on the worst 9_16 hours.",
        "changed_factor": "kickoff_monthhour_selective_sign_consistent_risk_hours",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "calibration_hours": [9, 10, 11, 14, 15, 16],
            "calibration_segments": ["9_16"],
            "month_bucket_mode": "season",
            "min_group_size": 5,
            "bias_shrinkage": 0.40,
            "bias_cap_abs": 14.0,
            "val_min_delta_mae_gain": 0.20,
            "val_min_rt_capped_smape_gain": 0.05,
            "require_predicted_sign_match": True,
            "predicted_abs_gate_quantile": 0.80,
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
]


def list_kickoff_monthhour_selective_candidates() -> list[dict]:
    return deepcopy(KICKOFF_MONTHHOUR_SELECTIVE_CANDIDATES)
