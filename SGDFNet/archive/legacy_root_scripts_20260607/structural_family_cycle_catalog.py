from __future__ import annotations

from copy import deepcopy


STRUCTURAL_FAMILY_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "sfam_001",
        "experiment_name": "SGDFNet_Structural_TFPressureGraph_V1",
        "instance_slug": "sfam_001_tf_pressure_static_graph",
        "stage": "J7_or_structural_feature_family",
        "branch": "tf_pressure_structural_features",
        "hypothesis": "static group graph features on top of TF+pressure may improve raw 9_16 by strengthening cross-group structure in the point-signal core",
        "changed_factor": "tf_pressure_static_group_graph",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_static_group_graph_features": True,
            },
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "sfam_002",
        "experiment_name": "SGDFNet_Structural_TFPressureGraphSegLocal_V1",
        "instance_slug": "sfam_002_tf_pressure_static_graph_seg_local",
        "stage": "J7_or_structural_feature_family",
        "branch": "tf_pressure_structural_features",
        "hypothesis": "if static graph alone is too coarse, combining it with segment-local statistics may better localize 9_16 point-signal structure",
        "changed_factor": "tf_pressure_static_group_graph_plus_segment_local",
        "config_updates": {
            "feature_config": {
                "include_tf_moving_average_features": True,
                "include_forecast_pressure_interactions": True,
                "include_static_group_graph_features": True,
                "include_segment_local_stats": True,
            },
        },
    },
]


def list_structural_family_candidates() -> list[dict]:
    return deepcopy(STRUCTURAL_FAMILY_CANDIDATES)
