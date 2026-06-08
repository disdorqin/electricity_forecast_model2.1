from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_contract import FeatureConfig, load_dataset, preprocess_dataframe


def load_and_preprocess_dataset(data_path: str | Path, feature_config: FeatureConfig) -> tuple[pd.DataFrame, list[str]]:
    raw = load_dataset(data_path)
    return preprocess_dataframe(raw, feature_config)


def filter_time_range(frame: pd.DataFrame, start: str | pd.Timestamp, end: str | pd.Timestamp) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return frame[(frame["timestamp"] >= start_ts) & (frame["timestamp"] <= end_ts)].copy()
