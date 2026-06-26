"""
Ledger predict pipeline.

Runs all models for a single target day D, producing 24-hour predictions
per model, standardized to the ledger format.

Day-ahead models:  lightgbm, timesfm, timemixer   (3 models × 24 = 72 rows)
Real-time models:  timesfm, sgdfnet, timemixer, rt916  (4 models × 24 = 96 rows)

Phase 1 only: no validation, no weight learning. Just predictions.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from pipelines.prediction_ledger import (
    append_predictions_to_ledger,
    update_actual_ledger,
)
from runtime.resource_scheduler import (
    ResourceScheduler,
    ScheduleTask,
    ScheduleResult,
)
from utils.business_day import (
    standardize_business_columns,
    validate_daily_predictions,
    infer_period,
    business_day_from_timestamp,
    hour_business_from_timestamp,
)

logger = logging.getLogger(__name__)

# Model sets
DAYAHEAD_MODELS = ["lightgbm", "timesfm", "timemixer"]
REALTIME_MODELS = ["timesfm", "sgdfnet", "timemixer", "rt916"]


# ===========================================================================
# Main entry point
# ===========================================================================

def run_ledger_predict(args: Any) -> dict:
    """
    Main entry for --pipeline ledger_predict.

    Parameters
    ----------
    args : argparse.Namespace
        Must contain: date, data_path, epf_v1_root, output_root (optional),
        ledger_root, runs_root, max_cpu_workers, max_gpu_workers,
        allow_missing_models, force.

    Returns
    -------
    dict with manifest-like status.
    """
    target_date = args.date
    if not target_date:
        raise ValueError("--date is required for ledger_predict")

    data_path = args.data_path
    epf_root = getattr(args, "epf_v1_root", None)
    ledger_root = Path(getattr(args, "ledger_root", "outputs/ledger"))
    runs_root = Path(getattr(args, "runs_root", "outputs/runs"))
    max_cpu = getattr(args, "max_cpu_workers", 2)
    max_gpu = getattr(args, "max_gpu_workers", 1)
    allow_missing = getattr(args, "allow_missing_models", False)
    force = getattr(args, "force", False)

    # Setup directories
    run_dir = runs_root / target_date
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Setup file logging for this run
    _setup_run_logging(logs_dir)

    logger.info(f"=== ledger_predict: {target_date} ===")

    manifest = {
        "pipeline": "ledger_predict",
        "target_date": target_date,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "results": {},
        "warnings": [],
        "errors": [],
    }

    # Determine cutoff
    cutoff_date = (pd.Timestamp(target_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        # --- Dayahead predictions ---
        da_results = _run_model_set(
            target_date=target_date,
            task="dayahead",
            models=DAYAHEAD_MODELS,
            data_path=data_path,
            epf_root=epf_root,
            cutoff_date=cutoff_date,
            run_dir=run_dir,
            max_cpu=max_cpu,
            max_gpu=max_gpu,
            force=force,
        )
        manifest["results"]["dayahead"] = da_results

        # --- Realtime predictions ---
        rt_results = _run_model_set(
            target_date=target_date,
            task="realtime",
            models=REALTIME_MODELS,
            data_path=data_path,
            epf_root=epf_root,
            cutoff_date=cutoff_date,
            run_dir=run_dir,
            max_cpu=max_cpu,
            max_gpu=max_gpu,
            force=force,
        )
        manifest["results"]["realtime"] = rt_results

        # --- Collect and write all_model_predictions_long ---
        _write_long_tables(run_dir, target_date, manifest)

        # --- Append to prediction ledger ---
        _append_all_to_ledger(run_dir, target_date, ledger_root, manifest)

        # --- Extract and update actual ledger ---
        _extract_actuals(data_path, target_date, ledger_root, manifest)

        # --- Validate final status ---
        manifest = _finalize_manifest(manifest, allow_missing)

        logger.info(f"ledger_predict {target_date}: {manifest['status']}")

    except Exception as e:
        manifest["status"] = "error"
        manifest["errors"].append(str(e))
        logger.exception(f"ledger_predict failed: {e}")

    # Write manifest
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    return manifest


# ===========================================================================
# Model execution
# ===========================================================================

def _run_model_set(
    target_date: str,
    task: str,
    models: list[str],
    data_path: str,
    epf_root: Optional[str],
    cutoff_date: str,
    run_dir: Path,
    max_cpu: int,
    max_gpu: int,
    force: bool,
) -> dict:
    """Run all models for a given task (dayahead or realtime)."""
    results = {}

    # Build tasks
    tasks: list[ScheduleTask] = []
    for model_name in models:
        pred_dir = run_dir / task / "prediction"
        pred_dir.mkdir(parents=True, exist_ok=True)

        # Check cache
        output_path = pred_dir / f"{model_name}_predictions.csv"
        if output_path.exists() and not force:
            logger.info(f"[{task}/{model_name}] Cache hit: {output_path}")
            try:
                cached_df = pd.read_csv(output_path)
                results[model_name] = {
                    "status": "cached",
                    "output_path": str(output_path),
                    "rows": len(cached_df),
                }
                continue
            except Exception:
                logger.warning(f"Cache read failed, re-running {model_name}")

        # Create task
        task_spec = ScheduleTask(
            model_name=model_name,
            task_name=task,
            target_date=target_date,
            fn=_predict_model,
            kwargs={
                "model_name": model_name,
                "task": task,
                "target_date": target_date,
                "data_path": data_path,
                "epf_root": epf_root,
                "cutoff_date": cutoff_date,
                "output_path": str(output_path),
            },
        )
        tasks.append(task_spec)

    if not tasks:
        logger.info(f"[{task}] All models cached, nothing to run")
        return results

    # Run through scheduler
    scheduler = ResourceScheduler(
        max_cpu_workers=max_cpu,
        max_gpu_workers=max_gpu,
    )
    schedule_results = scheduler.run(tasks)

    for sr in schedule_results:
        if sr.success:
            results[sr.model_name] = {
                "status": "ok",
                "output_path": str(run_dir / task / "prediction" / f"{sr.model_name}_predictions.csv"),
                "elapsed_seconds": sr.elapsed_seconds,
            }
        else:
            results[sr.model_name] = {
                "status": "failed",
                "error": sr.error,
                "elapsed_seconds": sr.elapsed_seconds,
            }

    return results


def _predict_model(
    model_name: str,
    task: str,
    target_date: str,
    data_path: str,
    epf_root: Optional[str],
    cutoff_date: str,
    output_path: str,
) -> pd.DataFrame:
    """
    Run a single model prediction and save to CSV.

    Returns the standardized DataFrame.
    """
    logger.info(f"Predicting: {model_name}/{task} on {target_date}")

    if model_name == "lightgbm":
        df = _predict_lightgbm(task, target_date, data_path, epf_root, cutoff_date)
    elif model_name == "timesfm":
        df = _predict_timesfm(task, target_date, data_path, epf_root, cutoff_date)
    elif model_name == "timemixer":
        df = _predict_timemixer(task, target_date, data_path, cutoff_date)
    elif model_name == "sgdfnet":
        df = _predict_sgdfnet(task, target_date, data_path, cutoff_date)
    elif model_name == "rt916":
        df = _predict_rt916(task, target_date, data_path, cutoff_date)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Validate
    errors = validate_daily_predictions(df, target_date, model_name, task)
    if errors:
        logger.error(f"Validation errors for {model_name}/{task}: {errors}")
        # Don't fail here — let the scheduler handle it

    # Save
    df.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path} ({len(df)} rows)")

    return df


# ===========================================================================
# Per-model prediction implementations
# ===========================================================================

def _predict_lightgbm(
    task: str,
    target_date: str,
    data_path: str,
    epf_root: Optional[str],
    cutoff_date: str,
) -> pd.DataFrame:
    """LightGBM prediction via EPF v1.0 adapter."""
    if epf_root and Path(epf_root).exists():
        from runners.adapters.lightgbm_v1 import LightGBMV1Adapter
        adapter = LightGBMV1Adapter(epf_root)
        return adapter.predict(
            target_date=target_date,
            target=task,
            data_path=data_path,
            cutoff_date=cutoff_date,
        )
    else:
        # Fallback: use existing 2.0 LightGBM pipeline
        logger.info("EPF v1.0 not found, using 2.0 LightGBM")
        return _predict_via_registry("lightgbm", task, target_date, data_path, cutoff_date)


def _predict_timesfm(
    task: str,
    target_date: str,
    data_path: str,
    epf_root: Optional[str],
    cutoff_date: str,
) -> pd.DataFrame:
    """TimesFM prediction via EPF v1.0 adapter (canonical wrapper)."""
    if epf_root and Path(epf_root).exists():
        from runners.adapters.timesfm_v1 import TimesFMV1Adapter
        adapter = TimesFMV1Adapter(epf_root)
        return adapter.predict(
            target_date=target_date,
            target=task,
            data_path=data_path,
            cutoff_date=cutoff_date,
        )
    else:
        logger.info("EPF v1.0 not found, using 2.0 TimesFM")
        return _predict_via_registry("timesfm", task, target_date, data_path, cutoff_date)


def _predict_timemixer(
    task: str,
    target_date: str,
    data_path: str,
    cutoff_date: str,
) -> pd.DataFrame:
    """TimeMixer prediction using 2.0 model (GPU preferred)."""
    return _predict_via_registry("timemixer", task, target_date, data_path, cutoff_date)


def _predict_sgdfnet(
    task: str,
    target_date: str,
    data_path: str,
    cutoff_date: str,
) -> pd.DataFrame:
    """SGDFNet prediction using 2.0 model (CPU preferred)."""
    return _predict_via_registry("sgdfnet", task, target_date, data_path, cutoff_date)


def _predict_rt916(
    task: str,
    target_date: str,
    data_path: str,
    cutoff_date: str,
) -> pd.DataFrame:
    """RT916 prediction using 2.0 model (GPU preferred)."""
    return _predict_via_registry("rt916", task, target_date, data_path, cutoff_date)


def _predict_via_registry(
    model_name: str,
    task: str,
    target_date: str,
    data_path: str,
    cutoff_date: str,
) -> pd.DataFrame:
    """
    Run prediction via the existing 2.0 model registry.

    Calls model.predict_range() and standardizes the output.
    """
    from runners.registry import get_model_pipeline

    pipeline = get_model_pipeline(model_name)

    result = pipeline.predict_range(
        target=task,
        data_path=data_path,
        predict_date=target_date,
        start=target_date,
        end=target_date,
    )

    if result is None or result.frame is None:
        raise RuntimeError(f"{model_name}/{task} returned None")

    df = result.frame.copy()

    # Standardize
    df = standardize_business_columns(
        df,
        ds_col="时刻",
        task_label=task,
        model_name=model_name,
        forecast_date=target_date,
        target_day=target_date,
        data_cutoff=cutoff_date,
        run_id=f"{model_name}_v2_{target_date}",
        model_version="v2.0",
    )

    # Keep required columns
    keep_cols = [
        "task", "model_name", "forecast_date", "target_day",
        "business_day", "ds", "hour_business", "period", "y_pred",
        "data_cutoff", "run_id", "model_version",
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    return df


# ===========================================================================
# Output aggregation
# ===========================================================================

def _write_long_tables(run_dir: Path, target_date: str, manifest: dict):
    """Write all_model_predictions_long.csv for each task."""
    for task in ["dayahead", "realtime"]:
        pred_dir = run_dir / task / "prediction"
        if not pred_dir.exists():
            continue

        pieces = []
        for csv_file in sorted(pred_dir.glob("*_predictions.csv")):
            try:
                df = pd.read_csv(csv_file)
                pieces.append(df)
            except Exception as e:
                manifest["warnings"].append(f"Failed to read {csv_file}: {e}")

        if pieces:
            long_df = pd.concat(pieces, ignore_index=True)
            long_path = pred_dir / "all_model_predictions_long.csv"
            long_df.to_csv(long_path, index=False)

            n_rows = len(long_df)
            expected = {"dayahead": 72, "realtime": 96}[task]
            manifest["results"][f"{task}_long_rows"] = n_rows
            if n_rows != expected:
                manifest["warnings"].append(
                    f"{task} long table: expected {expected} rows, got {n_rows}"
                )
            logger.info(f"{task} long table: {n_rows} rows → {long_path}")


def _append_all_to_ledger(
    run_dir: Path,
    target_date: str,
    ledger_root: Path,
    manifest: dict,
):
    """Append all predictions to the prediction ledger."""
    for task in ["dayahead", "realtime"]:
        long_path = run_dir / task / "prediction" / "all_model_predictions_long.csv"
        if not long_path.exists():
            manifest["warnings"].append(f"No long table for {task}, skipping ledger append")
            continue

        df = pd.read_csv(long_path)
        result = append_predictions_to_ledger(
            df=df,
            ledger_root=ledger_root,
            task=task,
            source_file=str(long_path),
        )
        manifest["results"][f"{task}_ledger"] = result


def _extract_actuals(
    data_path: str,
    target_date: str,
    ledger_root: Path,
    manifest: dict,
):
    """
    Extract actual prices from the raw data file for target_date
    and append to the actual ledger.
    """
    if not data_path or not Path(data_path).exists():
        manifest["warnings"].append(f"Data file not found: {data_path}")
        return

    try:
        ext = os.path.splitext(data_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            raw = pd.read_excel(data_path)
        else:
            raw = pd.read_csv(data_path)

        # Find timestamp column
        ts_col = None
        for c in ["时刻", "ds", "timestamp", "time", "datetime"]:
            if c in raw.columns:
                ts_col = c
                break

        if ts_col is None:
            manifest["warnings"].append("No timestamp column in data file")
            return

        raw["ds"] = pd.to_datetime(raw[ts_col], errors="coerce")

        # Filter to target_date's business hours
        target_dt = pd.Timestamp(target_date)
        # Business day D spans D 01:00 to D+1 00:00
        start_ts = target_dt.replace(hour=1, minute=0, second=0)
        end_ts = (target_dt + pd.Timedelta(days=1)).replace(hour=0, minute=0, second=0)

        mask = (raw["ds"] >= start_ts) & (raw["ds"] <= end_ts)
        day_data = raw[mask].copy()

        if len(day_data) == 0:
            manifest["warnings"].append(f"No actual data for {target_date}")
            return

        logger.info(f"Extracted {len(day_data)} actual rows for {target_date}")

        # Standardize
        day_data["business_day"] = day_data["ds"].apply(business_day_from_timestamp)
        day_data["hour_business"] = day_data["ds"].apply(hour_business_from_timestamp)
        day_data["period"] = day_data["hour_business"].apply(infer_period)

        # Find actual price columns
        for task, col_names in [
            ("dayahead", ["日前电价", "da_price", "dayahead_price"]),
            ("realtime", ["实时电价", "rt_price", "realtime_price"]),
        ]:
            y_col = None
            for cn in col_names:
                if cn in day_data.columns:
                    y_col = cn
                    break

            if y_col is None:
                continue

            act_df = day_data[["ds", "business_day", "hour_business", "period", y_col]].copy()
            act_df["y_true"] = pd.to_numeric(day_data[y_col], errors="coerce")
            act_df["task"] = task
            act_df["target_day"] = target_date

            act_df = act_df.dropna(subset=["y_true"])

            result = update_actual_ledger(
                df=act_df,
                ledger_root=ledger_root,
                task=task,
                source_file=data_path,
            )
            manifest["results"][f"{task}_actual_ledger"] = result

    except Exception as e:
        manifest["warnings"].append(f"Actual extraction failed: {e}")
        logger.warning(f"Actual extraction error: {e}")


def _finalize_manifest(manifest: dict, allow_missing: bool) -> dict:
    """Determine final status and add completion timestamp."""
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

    errors = manifest.get("errors", [])
    warnings = manifest.get("warnings", [])

    # Check model failures
    failed_models = []
    for task in ["dayahead", "realtime"]:
        task_results = manifest.get("results", {}).get(task, {})
        for model, info in task_results.items():
            if isinstance(info, dict) and info.get("status") == "failed":
                failed_models.append(f"{task}/{model}")

    if failed_models:
        manifest["failed_models"] = failed_models
        if allow_missing:
            manifest["status"] = "complete_with_warnings"
            warnings.append(f"Missing models: {failed_models}")
        else:
            manifest["status"] = "failed"
            errors.append(f"Required models failed: {failed_models}")
    elif errors:
        manifest["status"] = "failed"
    elif warnings:
        manifest["status"] = "complete_with_warnings"
    else:
        manifest["status"] = "complete"

    return manifest


def _setup_run_logging(logs_dir: Path):
    """Add a file handler for this pipeline run."""
    handler = logging.FileHandler(logs_dir / "pipeline.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger().addHandler(handler)
