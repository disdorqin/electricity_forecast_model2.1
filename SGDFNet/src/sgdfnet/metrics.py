from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def _valid_metric_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = ["rt_actual", "rt_hat", "delta_target", "delta_hat"]
    if df.empty:
        return df.copy()
    return df.dropna(subset=required).copy()


def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> float:
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(200.0 * np.abs(y_pred - y_true) / denom))


def capped_smape(y_true: np.ndarray, y_pred: np.ndarray, floor: float = 50.0, eps: float = 1e-6) -> float:
    y_true_capped = np.where(y_true < floor, floor, y_true)
    y_pred_capped = np.where(y_pred < floor, floor, y_pred)
    denom = np.abs(y_true_capped) + np.abs(y_pred_capped) + eps
    return float(np.mean(200.0 * np.abs(y_pred_capped - y_true_capped) / denom))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_pred - y_true)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_pred - y_true) ** 2)))


def direction_accuracy(delta_true: np.ndarray, delta_pred: np.ndarray) -> float:
    true_sign = delta_true > 0
    pred_sign = delta_pred > 0
    return float(np.mean(true_sign == pred_sign))


def positive_direction_recall(delta_true: np.ndarray, delta_pred: np.ndarray) -> float:
    true_pos = delta_true > 0
    if true_pos.sum() == 0:
        return float("nan")
    pred_pos = delta_pred > 0
    return float(np.mean(pred_pos[true_pos]))


def build_metrics_frame(df: pd.DataFrame) -> dict[str, float]:
    valid_df = _valid_metric_frame(df)
    if valid_df.empty:
        return {
            "rt_smape": float("nan"),
            "rt_capped_smape": float("nan"),
            "rt_mae": float("nan"),
            "rt_rmse": float("nan"),
            "delta_mae": float("nan"),
            "delta_rmse": float("nan"),
            "direction_accuracy": float("nan"),
            "positive_direction_recall": float("nan"),
        }
    rt_true = valid_df["rt_actual"].to_numpy(dtype=float)
    rt_pred = valid_df["rt_hat"].to_numpy(dtype=float)
    delta_true = valid_df["delta_target"].to_numpy(dtype=float)
    delta_pred = valid_df["delta_hat"].to_numpy(dtype=float)
    return {
        "rt_smape": smape(rt_true, rt_pred),
        "rt_capped_smape": capped_smape(rt_true, rt_pred),
        "rt_mae": mae(rt_true, rt_pred),
        "rt_rmse": rmse(rt_true, rt_pred),
        "delta_mae": mae(delta_true, delta_pred),
        "delta_rmse": rmse(delta_true, delta_pred),
        "direction_accuracy": direction_accuracy(delta_true, delta_pred),
        "positive_direction_recall": positive_direction_recall(delta_true, delta_pred),
    }


def build_segment_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment, seg_df in df.groupby("segment"):
        valid_seg_df = _valid_metric_frame(seg_df)
        row = {"segment": segment, "count": len(valid_seg_df)}
        row.update(build_metrics_frame(seg_df))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("segment").reset_index(drop=True)


def build_tail_metrics(df: pd.DataFrame, quantiles: Iterable[float] = (0.90, 0.95)) -> pd.DataFrame:
    valid_df = _valid_metric_frame(df)
    rows = []
    abs_delta = valid_df["delta_target"].abs()
    for q in quantiles:
        threshold = abs_delta.quantile(q)
        tail_df = valid_df[abs_delta >= threshold].copy()
        row = {
            "tail_quantile": q,
            "count": len(tail_df),
            "threshold_abs_delta": float(threshold),
        }
        if len(tail_df) > 0:
            row["tail_delta_mae"] = mae(tail_df["delta_target"].to_numpy(), tail_df["delta_hat"].to_numpy())
            row["tail_rt_smape"] = smape(tail_df["rt_actual"].to_numpy(), tail_df["rt_hat"].to_numpy())
            row["tail_direction_accuracy"] = direction_accuracy(
                tail_df["delta_target"].to_numpy(), tail_df["delta_hat"].to_numpy()
            )
        else:
            row["tail_delta_mae"] = float("nan")
            row["tail_rt_smape"] = float("nan")
            row["tail_direction_accuracy"] = float("nan")
        rows.append(row)
    return pd.DataFrame(rows)
