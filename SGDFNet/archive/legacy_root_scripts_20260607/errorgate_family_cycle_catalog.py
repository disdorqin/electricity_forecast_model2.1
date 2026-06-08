from __future__ import annotations

from copy import deepcopy


ERRORGATE_FAMILY_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "egfam_001",
        "experiment_name": "SGDFNet_ErrorGate_TFPressure_V1",
        "instance_slug": "egfam_001_error_gate_bias",
        "stage": "J6_or_error_gate_family",
        "branch": "tf_pressure_error_gate_calibration",
        "hypothesis": "validation residual error-gate bias on top of TF+pressure may focus correction on genuinely hard windows better than time buckets",
        "changed_factor": "error_gate_bias_on_tf_pressure",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
            "calibration_mode": "error_gate_bias",
            "calibration_error_quantile": 0.8,
            "calibration_segments": ["9_16"],
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "egfam_002",
        "experiment_name": "SGDFNet_ErrorGateSign_TFPressure_V1",
        "instance_slug": "egfam_002_combo_error_sign_gate_bias",
        "stage": "J6_or_error_gate_family",
        "branch": "tf_pressure_error_gate_calibration",
        "hypothesis": "if pure error-gate bias is too coarse, adding predicted-sign splits may better separate hard positive and negative residual regimes",
        "changed_factor": "combo_error_sign_gate_bias_on_tf_pressure",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
            "calibration_mode": "combo_error_sign_gate_bias",
            "calibration_error_quantile": 0.8,
            "calibration_segments": ["9_16"],
        },
    },
]


def list_errorgate_family_candidates() -> list[dict]:
    return deepcopy(ERRORGATE_FAMILY_CANDIDATES)
