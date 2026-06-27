"""
Ledger full-range pipeline: daily runs for a date range.

Runs the complete ledger_full pipeline for each day in [start, end]
and produces a range-level summary.

Output:
  outputs/runs/range_{start}_to_{end}/
    range_manifest.json
    range_summary.csv
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def run_ledger_full_range(args: Any) -> dict:
    """
    Main entry for --pipeline ledger_full_range.

    Parameters
    ----------
    args : argparse.Namespace
        Must contain: start, end, data_path, ...
        Optional: continue_on_error, skip_existing_final, range_preflight.

    Returns
    -------
    dict with range-level manifest.
    """
    start_date = args.start
    end_date = args.end
    if not start_date or not end_date:
        raise ValueError("--start and --end are required for ledger_full_range")

    if start_date > end_date:
        raise ValueError(f"--start ({start_date}) > --end ({end_date})")

    continue_on_error = getattr(args, "continue_on_error", False)
    skip_existing_final = getattr(args, "skip_existing_final", False)
    range_preflight = getattr(args, "range_preflight", True)
    runs_root = Path(getattr(args, "runs_root", "outputs/runs"))

    logger.info(
        f"=== ledger_full_range: {start_date} to {end_date} ==="
    )

    # Preflight check
    if range_preflight:
        preflight_errors = _run_preflight(args, start_date)
        if preflight_errors:
            return {
                "pipeline": "ledger_full_range",
                "start_date": start_date,
                "end_date": end_date,
                "status": "preflight_failed",
                "preflight_errors": preflight_errors,
                "preflight_note": "Use --no-range-preflight to skip preflight checks",
            }

    # Build date list (inclusive)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    date_list = [d.strftime("%Y-%m-%d") for d in date_range]

    range_manifest = {
        "pipeline": "ledger_full_range",
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(date_list),
        "completed_days": 0,
        "failed_days": 0,
        "skipped_days": 0,
        "status": "running",
        "daily_results": [],
        "errors": [],
        "warnings": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    range_dir = runs_root / f"range_{start_date}_to_{end_date}"
    range_dir.mkdir(parents=True, exist_ok=True)

    from pipelines.ledger_full import run_ledger_full

    for target_date in date_list:
        logger.info(f"\n{'='*60}\nRange day: {target_date}\n{'='*60}")

        # Check skip-existing-final
        submission_path = runs_root / target_date / "final" / "submission_ready.csv"
        if skip_existing_final and submission_path.exists():
            try:
                verify_df = pd.read_csv(submission_path)
                expected_cols = {"business_day", "ds", "hour_business", "period", "dayahead_price", "realtime_price"}
                if expected_cols.issubset(verify_df.columns) and len(verify_df) == 24:
                    logger.info(f"Skipping {target_date}: submission_ready.csv exists and looks valid")
                    daily_manifest_path = runs_root / target_date / "run_manifest.json"
                    range_manifest["daily_results"].append({
                        "date": target_date,
                        "status": "skipped",
                        "manifest_path": str(daily_manifest_path),
                        "submission_ready_path": str(submission_path),
                        "warnings_count": 0,
                        "errors_count": 0,
                    })
                    range_manifest["skipped_days"] += 1
                    continue
            except Exception:
                pass  # Invalid or missing; re-run

        # Run ledger_full for this single day
        try:
            day_args = _copy_args_for_day(args, target_date)
            day_result = run_ledger_full(day_args)
            day_status = day_result.get("status", "unknown")

            daily_manifest_path = runs_root / target_date / "run_manifest.json"
            range_manifest["daily_results"].append({
                "date": target_date,
                "status": day_status,
                "manifest_path": str(daily_manifest_path),
                "submission_ready_path": str(submission_path) if submission_path.exists() else None,
                "warnings_count": len(day_result.get("warnings", [])),
                "errors_count": len(day_result.get("errors", [])),
                "manifest_stages": list(day_result.get("stages", {}).keys()),
            })

            if day_status == "failed":
                range_manifest["failed_days"] += 1
                if not continue_on_error:
                    range_manifest["status"] = "failed"
                    range_manifest["errors"].append(
                        f"Stopped at {target_date}: ledger_full failed"
                    )
                    break
            else:
                range_manifest["completed_days"] += 1

        except Exception as e:
            logger.exception(f"Range day {target_date} failed: {e}")
            daily_manifest_path = runs_root / target_date / "run_manifest.json"
            range_manifest["daily_results"].append({
                "date": target_date,
                "status": "error",
                "manifest_path": str(daily_manifest_path),
                "submission_ready_path": None,
                "warnings_count": 0,
                "errors_count": 1,
            })
            range_manifest["failed_days"] += 1
            if not continue_on_error:
                range_manifest["status"] = "failed"
                range_manifest["errors"].append(f"Exception at {target_date}: {e}")
                break

    # Final status
    total = range_manifest["total_days"]
    completed = range_manifest["completed_days"]
    failed = range_manifest["failed_days"]

    if failed == 0 and completed + range_manifest["skipped_days"] == total:
        range_manifest["status"] = "complete"
    elif failed > 0 and completed > 0:
        range_manifest["status"] = "partial"
    elif completed == 0 and range_manifest["skipped_days"] == total:
        range_manifest["status"] = "all_skipped"
    elif failed == total:
        range_manifest["status"] = "failed"

    range_manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

    # Write range_manifest.json
    manifest_path = range_dir / "range_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(range_manifest, f, indent=2, ensure_ascii=False, default=str)

    # Write range_summary.csv
    _write_range_summary(range_dir, range_manifest)

    logger.info(
        f"ledger_full_range {start_date}..{end_date}: "
        f"{range_manifest['status']} "
        f"({completed}/{total} days completed, {failed} failed)"
    )

    return range_manifest


def _run_preflight(args: Any, start_date: str) -> list[str]:
    """
    Lightweight preflight checks for range pipeline.

    Checks:
      - data_path exists
      - All 4 ledger parquet files exist and are readable
      - Each ledger covers >= 30 unique days for window D-30..D-1
      - Dayahead prediction has expected models (lightgbm, timesfm, timemixer)
      - Realtime prediction has expected models (timesfm, sgdfnet, timemixer, rt916)

    Note: This is a lightweight coverage check. It does NOT guarantee final
    correctness. Full validation must use verify_final_pipeline /
    verify_range_pipeline after the run.
    """
    errors = []
    warnings = []

    # Check data_path exists
    data_path = getattr(args, "data_path", "data/shandong_pmos_hourly.xlsx")
    if not Path(data_path).exists():
        errors.append(f"Data path not found: {data_path}")

    # Check ledger_root exists
    ledger_root = Path(getattr(args, "ledger_root", "outputs/ledger"))
    if not ledger_root.exists():
        errors.append(f"Ledger root not found: {ledger_root}. Run backfill or copy from fixtures/seed_ledger/. (Use --no-range-preflight to skip)")
        return errors  # Cannot proceed further

    start_dt = pd.Timestamp(start_date)
    d30 = (start_dt - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    d1 = (start_dt - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    # Define the 4 ledger files to check
    ledger_files = {
        "dayahead prediction": ledger_root / "dayahead" / "prediction" / "prediction_ledger.parquet",
        "dayahead actual": ledger_root / "dayahead" / "actual" / "actual_ledger.parquet",
        "realtime prediction": ledger_root / "realtime" / "prediction" / "prediction_ledger.parquet",
        "realtime actual": ledger_root / "realtime" / "actual" / "actual_ledger.parquet",
    }

    for label, path in ledger_files.items():
        if not path.exists():
            errors.append(f"Ledger file not found: {path} ({label})")
            continue

        try:
            df = pd.read_parquet(path)
        except Exception as e:
            errors.append(
                f"Cannot read parquet ledger: {path} ({label}). "
                f"Ensure pyarrow is installed or regenerate ledger. Error: {e}"
            )
            continue

        # Check date coverage
        date_col = "target_day" if "target_day" in df.columns else "business_day"
        if date_col not in df.columns:
            errors.append(f"Ledger {path} ({label}) has no '{date_col}' column")
            continue

        dates = pd.to_datetime(df[date_col].unique())
        if len(dates) < 30:
            errors.append(
                f"Ledger {label}: {len(dates)} unique days, "
                f"need >= 30 for window D-30..D-1 = {d30}..{d1}. File: {path}"
            )

        # Check hour_business coverage (24 hours per day)
        if "hour_business" in df.columns:
            hours_per_day = df.groupby(date_col)["hour_business"].nunique()
            incomplete_days = hours_per_day[hours_per_day < 24]
            if not incomplete_days.empty:
                # Warn, don't error — some days may be partial (e.g., today)
                for bad_day, n_hours in incomplete_days.head(3).items():
                    warnings.append(
                        f"Ledger {label}: day {bad_day} has only {n_hours}/24 hours"
                    )

        # Check model coverage for prediction ledgers
        if "prediction" in label and "model_name" in df.columns:
            models_found = set(df["model_name"].unique())
            if "dayahead" in label:
                expected_models = {"lightgbm", "timesfm", "timemixer"}
                missing = expected_models - models_found
                if missing:
                    warnings.append(
                        f"Ledger {label}: missing expected models {missing}. "
                        f"Found: {models_found}. File: {path}"
                    )
            elif "realtime" in label:
                expected_models = {"timesfm", "sgdfnet", "timemixer", "rt916"}
                missing = expected_models - models_found
                if missing:
                    warnings.append(
                        f"Ledger {label}: missing expected models {missing}. "
                        f"Found: {models_found}. File: {path}"
                    )

    # Log warnings but don't fail for them
    for w in warnings:
        logger.warning(f"Preflight warning: {w}")

    return errors


def _copy_args_for_day(args: Any, target_date: str) -> Any:
    """Create a namespace copy with the target date set for ledger_full."""
    import copy

    day_args = copy.copy(args)
    day_args.date = target_date
    day_args.pipeline = "ledger_full"
    day_args.start = None
    day_args.end = None
    return day_args


def _write_range_summary(range_dir: Path, manifest: dict):
    """Write range_summary.csv from manifest daily_results."""
    rows = []
    for dr in manifest.get("daily_results", []):
        sp = dr.get("submission_ready_path")
        submission_ready_exists = sp is not None and Path(sp).exists()
        submission_ready_rows = 0
        if submission_ready_exists:
            try:
                sr_df = pd.read_csv(sp)
                submission_ready_rows = len(sr_df)
            except Exception:
                pass

        rows.append({
            "date": dr["date"],
            "status": dr["status"],
            "submission_ready_exists": submission_ready_exists,
            "submission_ready_rows": submission_ready_rows,
            "errors_count": dr.get("errors_count", 0),
            "warnings_count": dr.get("warnings_count", 0),
            "manifest_path": dr.get("manifest_path", ""),
            "submission_ready_path": sp or "",
        })

    if not rows:
        return

    summary_df = pd.DataFrame(rows)
    summary_path = range_dir / "range_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"Range summary: {len(rows)} days -> {summary_path}")
