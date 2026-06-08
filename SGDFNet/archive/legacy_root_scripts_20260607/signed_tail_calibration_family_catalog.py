from __future__ import annotations

from copy import deepcopy


SIGNED_TAIL_CALIBRATION_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "stcfam_001",
        "experiment_name": "SGDFNet_SignedTailCalibration_TFPressure_V1",
        "instance_slug": "stcfam_001_signed_tail_calibration_tfpressure",
        "stage": "J5_or_signed_tail_calibration_family",
        "branch": "signed_tail_calibration_family",
        "hypothesis": "If signed-tail probabilities carry useful ranking signal, a val-learned sign-specific hard-case bias should improve point errors more directly than probability heads alone.",
        "changed_factor": "signed_tail_probability_triggered_bias",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Followup_TFMovingAveragePlusPressure_V1_20260605_183728",
            "probability_scope": "global",
            "calibration_scope": "all",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": False,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "stcfam_002",
        "experiment_name": "SGDFNet_SignedTailCalibration_TFPressure916SegLocal_V1",
        "instance_slug": "stcfam_002_signed_tail_calibration_tfpressure_916_seg_local",
        "stage": "J5_or_signed_tail_calibration_family",
        "branch": "signed_tail_calibration_family",
        "hypothesis": "A 9_16-only signed-tail calibration with segment-local features may convert the near-miss ranking signal into targeted midday point repair.",
        "changed_factor": "signed_tail_probability_triggered_bias_9_16_seg_local",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Followup_TFMovingAveragePlusPressure_V1_20260605_183728",
            "probability_scope": "segment_9_16",
            "calibration_scope": "segment_9_16",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
]


def list_signed_tail_calibration_candidates() -> list[dict]:
    return deepcopy(SIGNED_TAIL_CALIBRATION_CANDIDATES)
