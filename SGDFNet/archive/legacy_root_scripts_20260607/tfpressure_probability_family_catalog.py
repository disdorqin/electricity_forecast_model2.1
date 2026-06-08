from __future__ import annotations

from copy import deepcopy


TFPRESSURE_PROBABILITY_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "ppfam_001",
        "experiment_name": "SGDFNet_TFPressure_P1_QuantileInterval_V1",
        "instance_slug": "ppfam_001_tfpressure_quantile_interval",
        "stage": "J6_or_probability_family",
        "branch": "tfpressure_probability_family",
        "hypothesis": "The strongest TF+pressure near-miss point base may produce better interval coverage and hard-sample ranking than the frozen baseline interval head.",
        "changed_factor": "tfpressure_quantile_interval",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Followup_TFMovingAveragePlusPressure_V1_20260605_183728",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "ppfam_002",
        "experiment_name": "SGDFNet_TFPressure_P2_SpikeProbability_V1",
        "instance_slug": "ppfam_002_tfpressure_spike_probability",
        "stage": "J6_or_probability_family",
        "branch": "tfpressure_probability_family",
        "hypothesis": "A spike-probability head on top of the TF+pressure near-miss base may recover better hard-case ranking than the frozen-baseline probability branch.",
        "changed_factor": "tfpressure_spike_probability",
        "config_updates": {
            "baseline_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Followup_TFMovingAveragePlusPressure_V1_20260605_183728",
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
            },
        },
    },
]


def list_tfpressure_probability_candidates() -> list[dict]:
    return deepcopy(TFPRESSURE_PROBABILITY_CANDIDATES)
