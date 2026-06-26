"""
Apply daily ledger weights to fuse predictions.

Reads per-model predictions and learned weights, then produces
weighted-average fused predictions.

Key rules:
  - For each (business_day, hour_business), find available models
  - Use task + period weights
  - Renormalize weights for available models only
  - NEVER use fillna(0) — missing models are excluded
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def apply_daily_ledger_weights(
    predictions_long: pd.DataFrame,
    weights: pd.DataFrame,
    target_day: str,
    task: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply learned weights to predictions for a single day.

    Parameters
    ----------
    predictions_long : pd.DataFrame
        All model predictions in long format. Must contain:
        task, model_name, target_day, business_day, ds, hour_business,
        period, y_pred.

    weights : pd.DataFrame
        Per-(task, period) weights. Columns: task, period, model_name, weight.

    target_day : str
        The target business day (YYYY-MM-DD).

    task : str
        "dayahead" or "realtime".

    Returns
    -------
    fused_df : pd.DataFrame
        Fused predictions with columns: task, business_day, ds,
        hour_business, period, y_fused.

    debug_df : pd.DataFrame
        Debug info with columns: task, business_day, hour_business, period,
        available_models, missing_models, raw_weights, renormalized_weights,
        renormalized, y_fused.
    """
    # Filter predictions to target_day and task
    pred = predictions_long.copy()
    pred = pred[(pred["target_day"] == target_day) & (pred["task"] == task)]

    if pred.empty:
        raise ValueError(f"No predictions found for {task} on {target_day}")

    # Filter weights to this task
    wdf = weights[weights["task"] == task].copy()

    if wdf.empty:
        raise ValueError(f"No weights found for {task}")

    # Get all model names from weights
    all_models = sorted(wdf["model_name"].unique())

    # Fuse hour by hour
    fused_rows = []
    debug_rows = []

    for hour in range(1, 25):
        hour_pred = pred[pred["hour_business"] == hour]

        if hour_pred.empty:
            logger.warning(f"No predictions for hour {hour}")
            continue

        period = hour_pred["period"].iloc[0]
        ds_val = hour_pred["ds"].iloc[0]
        bday = hour_pred["business_day"].iloc[0]

        # Get weights for this period
        period_weights = wdf[wdf["period"] == period]

        if period_weights.empty:
            logger.warning(f"No weights for {task}/{period}, using equal weights")
            # Equal weights fallback
            available_models = sorted(hour_pred["model_name"].unique())
            eq_weight = 1.0 / len(available_models)
            weights_dict = {m: eq_weight for m in available_models}
        else:
            weights_dict = dict(zip(period_weights["model_name"], period_weights["weight"]))

        # Map model to prediction
        model_preds = {}
        for _, row in hour_pred.iterrows():
            m = row["model_name"]
            y = row["y_pred"]
            if not pd.isna(y):
                model_preds[m] = float(y)

        available = sorted(model_preds.keys())
        all_model_set = set(weights_dict.keys())
        missing = sorted(all_model_set - set(available))

        if not available:
            logger.warning(f"No available models for hour {hour}")
            continue

        # Collect raw weights for available models
        raw_w = {m: weights_dict.get(m, 0.0) for m in available}

        # Renormalize
        total_raw = sum(raw_w.values())
        if total_raw <= 0:
            # Equal weights as fallback
            renorm_w = {m: 1.0 / len(available) for m in available}
            was_renormalized = True
        else:
            renorm_w = {m: raw_w[m] / total_raw for m in available}
            was_renormalized = abs(total_raw - 1.0) > 0.001 or len(missing) > 0

        # Weighted average
        y_fused = sum(renorm_w[m] * model_preds[m] for m in available)

        fused_rows.append({
            "task": task,
            "business_day": bday,
            "ds": ds_val,
            "hour_business": hour,
            "period": period,
            "y_fused": round(y_fused, 4),
        })

        debug_rows.append({
            "task": task,
            "business_day": bday,
            "hour_business": hour,
            "period": period,
            "available_models": ",".join(available),
            "missing_models": ",".join(missing) if missing else "",
            "raw_weights": ",".join(f"{m}:{raw_w.get(m, 0):.4f}" for m in available),
            "renormalized_weights": ",".join(f"{m}:{renorm_w[m]:.4f}" for m in available),
            "renormalized": was_renormalized,
            "y_fused": round(y_fused, 4),
        })

    fused_df = pd.DataFrame(fused_rows)
    debug_df = pd.DataFrame(debug_rows)

    # Verify 24 rows
    if len(fused_df) != 24:
        logger.warning(
            f"Fused {task}: expected 24 rows, got {len(fused_df)}"
        )

    # Check no fillna(0)
    if (fused_df["y_fused"] == 0).any():
        logger.warning("Fused predictions contain zeros — possible fillna(0) issue")

    return fused_df, debug_df
