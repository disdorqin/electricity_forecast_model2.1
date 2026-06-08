from __future__ import annotations

from copy import deepcopy


KICKOFF_CONSERVATIVE_TAILCAL_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "kctcal_001",
        "experiment_name": "SGDFNet_KickoffConservativeTailCal_Global_V1",
        "instance_slug": "kctcal_001_conservative_signed_tail_global",
        "stage": "kickoff_conservative_tail_calibration_family",
        "branch": "kickoff_conservative_signed_tail_calibration_family",
        "hypothesis": "A higher trigger and shrunk global signed-tail bias may preserve the kickoff tail signal while reducing raw-metric damage.",
        "changed_factor": "kickoff_conservative_signed_tail_global_shrinked",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "probability_scope": "global",
            "calibration_scope": "all",
            "probability_trigger_quantile": 0.92,
            "bias_shrinkage": 0.35,
            "bias_cap_abs": 25.0,
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "kctcal_002",
        "experiment_name": "SGDFNet_KickoffConservativeTailCal_916_V1",
        "instance_slug": "kctcal_002_conservative_signed_tail_916",
        "stage": "kickoff_conservative_tail_calibration_family",
        "branch": "kickoff_conservative_signed_tail_calibration_family",
        "hypothesis": "A very conservative 9_16-only signed-tail bias should test whether the kickoff near-miss can convert top-tail gains without broad raw regression.",
        "changed_factor": "kickoff_conservative_signed_tail_916_shrinked",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "probability_scope": "segment_9_16",
            "calibration_scope": "segment_9_16",
            "probability_trigger_quantile": 0.94,
            "bias_shrinkage": 0.25,
            "bias_cap_abs": 18.0,
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
]


def list_kickoff_conservative_tailcal_candidates() -> list[dict]:
    return deepcopy(KICKOFF_CONSERVATIVE_TAILCAL_CANDIDATES)
