from __future__ import annotations

from copy import deepcopy


FUSION_FAMILY_CANDIDATES: list[dict] = [
    {
        "sequence_id": 1,
        "experiment_id": "ffam_001",
        "experiment_name": "SGDFNet_Fusion_SignedTailPointPlusInterval_V1",
        "instance_slug": "ffam_001_signed_tail_point_plus_interval",
        "stage": "J7_or_fusion_family",
        "branch": "fusion_family",
        "hypothesis": "The accepted signed-tail point repair and accepted quantile interval module should be packaged into a unified release-style candidate without degrading either side.",
        "changed_factor": "signed_tail_point_plus_interval_bundle",
        "config_updates": {
            "point_artifact": "C:\\Users\\37813\\.codex\\worktrees\\ce61\\elec\\outputs\\RT916_SpikeMarketLab\\experiments\\SGDFNet_SignedTailCalibration_TFPressure_V1_20260605_194106",
            "interval_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936",
        },
    },
    {
        "sequence_id": 2,
        "experiment_id": "ffam_002",
        "experiment_name": "SGDFNet_Fusion_SignedTailPointPlusIntervalTailFlag_V1",
        "instance_slug": "ffam_002_signed_tail_point_plus_interval_tailflag",
        "stage": "J7_or_fusion_family",
        "branch": "fusion_family",
        "hypothesis": "A unified bundle that also exposes a simple hard-case flag from the signed-tail calibration may be more useful for downstream release analysis without changing the point predictions.",
        "changed_factor": "signed_tail_point_plus_interval_bundle_with_tailflag",
        "config_updates": {
            "point_artifact": "C:\\Users\\37813\\.codex\\worktrees\\ce61\\elec\\outputs\\RT916_SpikeMarketLab\\experiments\\SGDFNet_SignedTailCalibration_TFPressure_V1_20260605_194106",
            "interval_artifact": "outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936",
            "include_tail_flag": True,
        },
    },
]


def list_fusion_family_candidates() -> list[dict]:
    return deepcopy(FUSION_FAMILY_CANDIDATES)
