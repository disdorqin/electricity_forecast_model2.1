from __future__ import annotations

from typing import Any

import pandas as pd

from .metrics import build_metrics_frame, build_segment_metrics, build_tail_metrics
from .models import DeltaRegressor, HGBModelConfig, SegmentConditionedDeltaRegressor


def build_regressor(model_config: HGBModelConfig):
    if model_config.segment_conditioned_models:
        return SegmentConditionedDeltaRegressor(model_config)
    return DeltaRegressor(model_config)


def score_prediction_frame(pred_df: pd.DataFrame) -> dict[str, Any]:
    return {
        "overall": build_metrics_frame(pred_df),
        "segment_metrics": build_segment_metrics(pred_df).to_dict(orient="records"),
        "tail_metrics": build_tail_metrics(pred_df).to_dict(orient="records"),
    }
