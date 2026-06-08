from __future__ import annotations

from copy import deepcopy


KICKOFF_SELECTIVE_GATE_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "ksgate_001",
        "experiment_name": "SGDFNet_KickoffSelectiveGate_Global_V1",
        "instance_slug": "ksgate_001_selective_signed_tail_global",
        "stage": "kickoff_selective_gate_family",
        "branch": "kickoff_selective_signed_tail_gate_family",
        "hypothesis": "Selective signed-tail correction should only fire when validation proves subgroup-level improvement, reducing the raw penalty seen in unconditional tail calibration.",
        "changed_factor": "kickoff_selective_signed_tail_global_valgated",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "probability_scope": "global",
            "calibration_scope": "all",
            "probability_trigger_quantile": 0.90,
            "predicted_abs_gate_quantile": 0.80,
            "require_predicted_sign_match": True,
            "bias_shrinkage": 0.45,
            "bias_cap_abs": 20.0,
            "val_min_delta_mae_gain": 0.20,
            "val_min_rt_capped_smape_gain": 0.05,
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "ksgate_002",
        "experiment_name": "SGDFNet_KickoffSelectiveGate_916_V1",
        "instance_slug": "ksgate_002_selective_signed_tail_916",
        "stage": "kickoff_selective_gate_family",
        "branch": "kickoff_selective_signed_tail_gate_family",
        "hypothesis": "A 9_16-only selective gate with predicted-sign consistency should focus correction onto the highest-confidence midday hard cells without spreading raw damage elsewhere.",
        "changed_factor": "kickoff_selective_signed_tail_916_valgated",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_KickoffFollowup_TFPressureSegLocal_V1_20260605_204630",
            "probability_scope": "segment_9_16",
            "calibration_scope": "segment_9_16",
            "probability_trigger_quantile": 0.92,
            "predicted_abs_gate_quantile": 0.85,
            "require_predicted_sign_match": True,
            "bias_shrinkage": 0.40,
            "bias_cap_abs": 16.0,
            "val_min_delta_mae_gain": 0.25,
            "val_min_rt_capped_smape_gain": 0.08,
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_segment_local_stats": True,
            },
        },
    },
]


def list_kickoff_selective_gate_candidates() -> list[dict]:
    return deepcopy(KICKOFF_SELECTIVE_GATE_CANDIDATES)
