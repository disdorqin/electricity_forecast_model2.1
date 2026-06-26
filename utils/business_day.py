"""
Business day utilities for electricity market forecasting.

Key rule: hour 24 of business_day D = timestamp D+1 00:00:00

All outputs must use business_day + hour_business for dedup, merging,
row-count checks, and fusion. Never use ds.normalize() alone.

Standardized output columns:
  - business_day: str "YYYY-MM-DD"  (the business/contract day)
  - ds: datetime64[ns]  (actual wall-clock timestamp)
  - hour_business: int 1..24
  - period: str "1_8", "9_16", or "17_24"
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Period classification
# ---------------------------------------------------------------------------

def infer_period(hour_business: int) -> str:
    """Map business hour (1..24) to period label."""
    if 1 <= hour_business <= 8:
        return "1_8"
    elif 9 <= hour_business <= 16:
        return "9_16"
    elif 17 <= hour_business <= 24:
        return "17_24"
    raise ValueError(f"hour_business must be 1..24, got {hour_business}")


# ---------------------------------------------------------------------------
# Business day conversion
# ---------------------------------------------------------------------------

def business_day_from_timestamp(ts: pd.Timestamp) -> str:
    """
    Convert a wall-clock timestamp to its business day.

    Rules:
      - 00:00:00 on day D+1  → hour 24 of business day D
      - All other hours      → business day = date portion
    """
    if ts.hour == 0 and ts.minute == 0 and ts.second == 0:
        return (ts - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return ts.strftime("%Y-%m-%d")


def hour_business_from_timestamp(ts: pd.Timestamp) -> int:
    """
    Convert a wall-clock timestamp to business hour (1..24).

    hour 24 of business day D = timestamp D+1 00:00:00
    """
    if ts.hour == 0 and ts.minute == 0 and ts.second == 0:
        return 24
    return ts.hour


def timestamp_from_business(business_day: str, hour_business: int) -> pd.Timestamp:
    """
    Convert (business_day, hour_business) back to wall-clock timestamp.

    hour 24 of D → D+1 00:00:00
    """
    day = pd.Timestamp(business_day)
    if hour_business == 24:
        return (day + pd.Timedelta(days=1)).replace(hour=0, minute=0, second=0)
    return day.replace(hour=hour_business, minute=0, second=0)


# ---------------------------------------------------------------------------
# Standardize a prediction DataFrame
# ---------------------------------------------------------------------------

def standardize_business_columns(
    df: pd.DataFrame,
    ds_col: str = "ds",
    y_pred_col: Optional[str] = None,
    y_true_col: Optional[str] = None,
    task_label: Optional[str] = None,
    model_name: Optional[str] = None,
    forecast_date: Optional[str] = None,
    target_day: Optional[str] = None,
    data_cutoff: Optional[str] = None,
    run_id: Optional[str] = None,
    model_version: Optional[str] = None,
) -> pd.DataFrame:
    """
    Standardize a DataFrame to the ledger-compatible format.

    Input can have any column names; this function maps them to the
    standardized schema and adds derived columns (business_day,
    hour_business, period).

    Parameters
    ----------
    df : pd.DataFrame
        Raw prediction data. Must contain a timestamp column.
    ds_col : str
        Name of the timestamp column in df (e.g. "ds", "时刻", "timestamp").
    y_pred_col : str, optional
        Name of prediction column. Auto-detected if None.
    y_true_col : str, optional
        Name of actual/true value column.
    task_label : str, optional
        "dayahead" or "realtime". Inferred if None.
    model_name : str, optional
        Model identifier.
    forecast_date : str, optional
        When the forecast was run (YYYY-MM-DD).
    target_day : str, optional
        The business day being predicted.
    data_cutoff : str, optional
        Latest data timestamp used for the prediction.
    run_id : str, optional
        Unique run identifier.
    model_version : str, optional
        Model version string.

    Returns
    -------
    pd.DataFrame with standardized columns.
    """
    df = df.copy()

    # --- Resolve ds column ---
    candidates = [ds_col, "ds", "时刻", "timestamp", "time", "datetime"]
    found_ds = None
    for c in candidates:
        if c in df.columns:
            found_ds = c
            break
    if found_ds is None:
        raise ValueError(f"No timestamp column found in {list(df.columns)}. Tried: {candidates}")
    df["ds"] = pd.to_datetime(df[found_ds])
    if found_ds != "ds":
        df = df.drop(columns=[found_ds])

    # --- Resolve y_pred ---
    pred_candidates = []
    if y_pred_col:
        pred_candidates.append(y_pred_col)
    pred_candidates.extend(["prediction", "y_pred", "pred_y", "预测值",
                             "预测日前电价", "预测实时电价", "rt_hat"])
    pred_found = None
    for c in pred_candidates:
        if c in df.columns:
            pred_found = c
            break
    if pred_found is None:
        # Try to find numeric column that looks like a prediction
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for nc in numeric_cols:
            if nc.lower() not in ("hour", "month", "day", "year", "index"):
                pred_found = nc
                logger.warning(f"Guessing prediction column: {pred_found}")
                break
    if pred_found is None:
        raise ValueError(f"No prediction column found in {list(df.columns)}")
    df["y_pred"] = pd.to_numeric(df[pred_found], errors="coerce")
    if pred_found != "y_pred":
        df = df.drop(columns=[pred_found], errors="ignore")

    # --- Resolve y_true ---
    if y_true_col and y_true_col in df.columns:
        df["y_true"] = pd.to_numeric(df[y_true_col], errors="coerce")
        if y_true_col != "y_true":
            df = df.drop(columns=[y_true_col], errors="ignore")
    elif "y_true" in df.columns:
        df["y_true"] = pd.to_numeric(df["y_true"], errors="coerce")
    elif "y" in df.columns:
        df["y_true"] = pd.to_numeric(df["y"], errors="coerce")
        df = df.drop(columns=["y"], errors="ignore")

    # --- Add derived business columns ---
    df["business_day"] = df["ds"].apply(business_day_from_timestamp)
    df["hour_business"] = df["ds"].apply(hour_business_from_timestamp)
    df["period"] = df["hour_business"].apply(infer_period)

    # --- Add scalar metadata columns ---
    if task_label:
        df["task"] = task_label
    if model_name:
        df["model_name"] = model_name
    if forecast_date:
        df["forecast_date"] = forecast_date
    if target_day:
        df["target_day"] = target_day
        # Also set business_day from target_day if ds-based derivation is unreliable
        df["business_day"] = target_day
    if data_cutoff:
        df["data_cutoff"] = data_cutoff
    if run_id:
        df["run_id"] = run_id
    if model_version:
        df["model_version"] = model_version

    return df


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_daily_predictions(
    df: pd.DataFrame,
    target_day: str,
    model_name: str,
    task: str,
) -> list[str]:
    """
    Validate that a model produced exactly 24 rows for a target day,
    with hour_business 1..24, no duplicates, no missing hours.

    Returns list of error messages (empty = valid).
    """
    errors: list[str] = []

    # Filter to target_day
    mask = df["business_day"] == target_day
    day_df = df[mask]

    n = len(day_df)
    if n != 24:
        errors.append(
            f"{task}/{model_name} on {target_day}: expected 24 rows, got {n}"
        )

    if n > 0:
        hours = day_df["hour_business"].values
        expected = set(range(1, 25))
        actual = set(int(h) for h in hours)

        if actual != expected:
            missing = expected - actual
            extra = actual - expected
            if missing:
                errors.append(f"{task}/{model_name}: missing hours {sorted(missing)}")
            if extra:
                errors.append(f"{task}/{model_name}: extra hours {sorted(extra)}")

        # Check for duplicate hours
        dup_hours = day_df["hour_business"].duplicated()
        if dup_hours.any():
            dup_vals = day_df.loc[dup_hours, "hour_business"].unique()
            errors.append(f"{task}/{model_name}: duplicate hours {list(dup_vals)}")

        # Check hour 24 date alignment
        h24 = day_df[day_df["hour_business"] == 24]
        for _, row in h24.iterrows():
            expected_ts = timestamp_from_business(target_day, 24)
            if pd.Timestamp(row["ds"]).date() != expected_ts.date():
                errors.append(
                    f"{task}/{model_name}: hour 24 timestamp {row['ds']} != "
                    f"expected {expected_ts}"
                )

    return errors


def check_all_models_24_rows(
    predictions_long: pd.DataFrame,
    task: str,
    target_day: str,
) -> dict:
    """
    Check that every model in the long table has exactly 24 rows.

    Returns dict: {model_name: error_list}
    """
    results = {}
    models = predictions_long["model_name"].unique()
    for model in sorted(models):
        model_df = predictions_long[predictions_long["model_name"] == model]
        errors = validate_daily_predictions(model_df, target_day, model, task)
        results[model] = errors
        if errors:
            for e in errors:
                logger.error(e)
    return results


# ---------------------------------------------------------------------------
# Output columns definition
# ---------------------------------------------------------------------------

PREDICTION_LEDGER_COLUMNS = [
    "task",
    "model_name",
    "forecast_date",
    "target_day",
    "business_day",
    "ds",
    "hour_business",
    "period",
    "y_pred",
    "data_cutoff",
    "run_id",
    "model_version",
    "created_at",
    "source_file",
]

ACTUAL_LEDGER_COLUMNS = [
    "task",
    "target_day",
    "business_day",
    "ds",
    "hour_business",
    "period",
    "y_true",
    "actual_available_at",
    "source_file",
]

TRAINING_TABLE_COLUMNS = [
    "task",
    "model_name",
    "target_day",
    "business_day",
    "ds",
    "hour_business",
    "period",
    "y_pred",
    "y_true",
    "age_days",
    "day_gate",
]

FUSED_DEBUG_COLUMNS = [
    "task",
    "business_day",
    "hour_business",
    "period",
    "available_models",
    "missing_models",
    "raw_weights",
    "renormalized_weights",
    "renormalized",
    "y_fused",
]
