from __future__ import annotations

from copy import deepcopy


SIGNED_TAIL_PROBABILITY_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "stpfam_001",
        "experiment_name": "SGDFNet_SignedTailProb_TFPressure_V1",
        "instance_slug": "stpfam_001_signed_tail_tfpressure",
        "stage": "J6_or_signed_tail_probability_family",
        "branch": "signed_tail_probability_family",
        "hypothesis": "Separate positive and negative tail probabilities can turn the error-gate tail-specialist clue into a cleaner ranking signal than unsigned spike probability.",
        "changed_factor": "signed_tail_dual_probability",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Followup_TFMovingAveragePlusPressure_V1_20260605_183728",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": False,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "stpfam_002",
        "experiment_name": "SGDFNet_SignedTailProb_TFPressureSegLocal_V1",
        "instance_slug": "stpfam_002_signed_tail_tfpressure_seg_local",
        "stage": "J6_or_signed_tail_probability_family",
        "branch": "signed_tail_probability_family",
        "hypothesis": "If signed-tail ranking needs more localization, same-hour segment-local statistics may help distinguish positive and negative hard cases inside 9_16.",
        "changed_factor": "signed_tail_dual_probability_plus_segment_local",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Followup_TFMovingAveragePlusPressure_V1_20260605_183728",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
]


def list_signed_tail_probability_candidates() -> list[dict]:
    return deepcopy(SIGNED_TAIL_PROBABILITY_CANDIDATES)
