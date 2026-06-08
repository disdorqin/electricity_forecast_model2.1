from __future__ import annotations

from copy import deepcopy


PROMOTION_VALIDATION_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "pvfam_001",
        "experiment_name": "SGDFNet_PromotionValidation_202604_FusionBundle_V1",
        "instance_slug": "pvfam_001_202604_fusion_bundle",
        "stage": "J8_or_promotion_validation_family",
        "branch": "promotion_validation_family",
        "hypothesis": "The current best unified candidate ffam_002 should remain coherent on a fresh 2026 month when evaluated as a frozen release-style bundle.",
        "changed_factor": "promotion_validation_2026_04_fusion_bundle",
        "config_updates": {
            "target_months": ["2026-04"],
            "include_tail_flag": True,
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "pvfam_002",
        "experiment_name": "SGDFNet_PromotionValidation_202604_PointOnlyControl_V1",
        "instance_slug": "pvfam_002_202604_point_only_control",
        "stage": "J8_or_promotion_validation_family",
        "branch": "promotion_validation_family",
        "hypothesis": "A point-only control on the same 2026 month helps separate point extrapolation quality from interval packaging quality.",
        "changed_factor": "promotion_validation_2026_04_point_only_control",
        "config_updates": {
            "target_months": ["2026-04"],
            "include_tail_flag": False,
        },
    },
]


def list_promotion_validation_candidates() -> list[dict]:
    return deepcopy(PROMOTION_VALIDATION_CANDIDATES)
