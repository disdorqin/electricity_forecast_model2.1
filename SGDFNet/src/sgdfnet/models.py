from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


@dataclass
class HGBModelConfig:
    loss: str = "absolute_error"
    quantile_alpha: float = 0.5
    learning_rate: float = 0.05
    max_depth: int = 6
    max_iter: int = 300
    min_samples_leaf: int = 40
    l2_regularization: float = 0.1
    random_state: int = 42
    tail_sample_weight: float = 1.0
    tail_quantile: float = 0.85
    segment_conditioned_models: bool = False
    risk_hour_primary_hours: list[int] | None = None
    risk_hour_secondary_hours: list[int] | None = None
    risk_hour_segments: list[str] | None = None
    risk_hour_primary_weight: float = 1.0
    risk_hour_secondary_weight: float = 1.0


class DeltaRegressor:
    def __init__(self, config: HGBModelConfig) -> None:
        self.config = config
        self.model = HistGradientBoostingRegressor(
            loss=config.loss,
            quantile=config.quantile_alpha,
            learning_rate=config.learning_rate,
            max_depth=config.max_depth,
            max_iter=config.max_iter,
            min_samples_leaf=config.min_samples_leaf,
            l2_regularization=config.l2_regularization,
            random_state=config.random_state,
            early_stopping=False,
        )

    def fit(
        self,
        frame: pd.DataFrame,
        feature_cols: list[str],
        target_col: str = "delta_target",
        sample_weight: np.ndarray | None = None,
    ) -> None:
        x = frame[feature_cols]
        y = frame[target_col].to_numpy(dtype=float)
        self.model.fit(x, y, sample_weight=sample_weight)

    def predict(self, frame: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
        return self.model.predict(frame[feature_cols])


class SegmentConditionedDeltaRegressor:
    def __init__(self, config: HGBModelConfig) -> None:
        self.config = config
        self.segment_models: dict[str, DeltaRegressor] = {}
        self.global_model = DeltaRegressor(config)

    def fit(
        self,
        frame: pd.DataFrame,
        feature_cols: list[str],
        target_col: str = "delta_target",
        sample_weight: np.ndarray | None = None,
    ) -> None:
        self.global_model.fit(frame, feature_cols, target_col=target_col, sample_weight=sample_weight)
        for segment, seg_df in frame.groupby("segment"):
            seg_weight = None
            if sample_weight is not None:
                seg_weight = np.asarray(sample_weight)[seg_df.index.to_numpy()]
            model = DeltaRegressor(self.config)
            model.fit(seg_df, feature_cols, target_col=target_col, sample_weight=seg_weight)
            self.segment_models[str(segment)] = model

    def predict(self, frame: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
        preds = pd.Series(np.zeros(len(frame), dtype=float), index=frame.index, dtype=float)
        for segment, seg_df in frame.groupby("segment"):
            model = self.segment_models.get(str(segment), self.global_model)
            preds.loc[seg_df.index] = model.predict(seg_df, feature_cols)
        return preds.to_numpy(dtype=float)
