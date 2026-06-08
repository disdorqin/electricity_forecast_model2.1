from __future__ import annotations

from copy import deepcopy


KICKOFF_TAILCAL_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "ktcal_001",
        "experiment_name": "SGDFNet_KickoffTailCal_TFPressureSegLocal_V1",
        "instance_slug": "ktcal_001_signed_tail_calibration_kickoff_tfpressure_seg_local",
        "stage": "kickoff_followup_tail_calibration_family",
        "branch": "kickoff_signed_tail_calibration_family",
        "hypothesis": "The kickoff TF+pressure+segment-local near-miss may convert its capped and tail signal into a real point gain through signed-tail triggered val-learned bias correction.",
        "changed_factor": "kickoff_signed_tail_probability_triggered_bias_global",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "probability_scope": "global",
            "calibration_scope": "all",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "ktcal_002",
        "experiment_name": "SGDFNet_KickoffTailCal_TFPressureSegLocal916_V1",
        "instance_slug": "ktcal_002_signed_tail_calibration_kickoff_tfpressure_916_seg_local",
        "stage": "kickoff_followup_tail_calibration_family",
        "branch": "kickoff_signed_tail_calibration_family",
        "hypothesis": "A 9_16-focused signed-tail calibration may preserve the kickoff near-miss raw behavior while pushing more of the capped/tail benefit into the hard midday cells.",
        "changed_factor": "kickoff_signed_tail_probability_triggered_bias_9_16_seg_local",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
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


def list_kickoff_tailcal_candidates() -> list[dict]:
    return deepcopy(KICKOFF_TAILCAL_CANDIDATES)
