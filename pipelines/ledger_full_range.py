"""
Ledger full-range pipeline: daily runs for a date range.

Runs the complete ledger_full pipeline (five stages) for each day in [start, end]
and produces a range-level manifest and summary.

Range pipeline stages per day:
  ledger_predict → ledger_weight → ledger_fuse → ledger_classifier → final_outputs

Output:
  outputs/runs/range_{start}_to_{end}/
    range_manifest.json
    range_summary.csv
"""

from __future__ import annotations

import copy
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SUBMISSION_COLUMNS = [
    "business_day", "ds", "hour_business", "period",
    "dayahead_price", "realtime_price",
]


def is_existing_final_valid(
    runs_root: Path, target_date: str
) -> tuple[bool, list[str]]:
    """Strong validation of an existing day's submission output.

    Returns (is_valid, reasons) where *reasons* lists each failed check.
    All of the following must pass for ``is_valid`` to be True:

    1. ``submission_ready.csv`` exists.
    2. Columns exactly equal ``SUBMISSION_COLUMNS``.
    3. Exactly 24 rows.
    4. ``hour_business`` is precisely 1 .. 24.
    5. No duplicate ``hour_business`` values.
    6. ``business_day`` equals *target_date*.
    7. Hour-24 ``ds`` is ``{target_date+1day} 00:00:00``.
    8. ``dayahead_price`` and ``realtime_price`` are non-null and numeric.
    9. No ``_x`` / ``_y`` suffix columns.
    10. ``run_manifest.json`` exists.
    11. All five stages in the manifest report ``status == "complete"``.
    12. Manifest ``errors`` list is empty.
    """
    reasons: list[str] = []
    run_dir = runs_root / target_date
    sub_path = run_dir / "final" / "submission_ready.csv"

    # 1. File existence
    if not sub_path.exists():
        return False, [f"submission_ready.csv not found: {sub_path}"]

    try:
        df = pd.read_csv(sub_path)
    except Exception as exc:
        return False, [f"cannot read {sub_path}: {exc}"]

    # 2. Column exact match
    actual_cols = list(df.columns)
    if actual_cols != SUBMISSION_COLUMNS:
        reasons.append(
            f"columns mismatch: expected {SUBMISSION_COLUMNS}, got {actual_cols}"
        )

    # 3. Row count
    if len(df) != 24:
        reasons.append(f"row count: expected 24, got {len(df)}")

    # 4. hour_business 1..24
    if "hour_business" in df.columns:
        hours = sorted(df["hour_business"].unique())
        if hours != list(range(1, 25)):
            reasons.append(f"hour_business range: expected 1..24, got {hours}")
    else:
        reasons.append("column hour_business missing")

    # 5. Duplicate hours
    if "hour_business" in df.columns and df["hour_business"].duplicated().any():
        dups = df[df["hour_business"].duplicated()]["hour_business"].tolist()
        reasons.append(f"duplicate hour_business values: {dups}")

    # 6. business_day match
    if "business_day" in df.columns:
        bdays = df["business_day"].unique()
        if len(bdays) != 1 or str(bdays[0]) != target_date:
            reasons.append(
                f"business_day mismatch: expected {target_date}, got {bdays}"
            )
    else:
        reasons.append("column business_day missing")

    # 7. Hour-24 ds
    if "hour_business" in df.columns and "ds" in df.columns:
        h24 = df[df["hour_business"] == 24]
        if not h24.empty:
            next_day = pd.Timestamp(target_date) + pd.Timedelta(days=1)
            expected_ds = next_day.strftime("%Y-%m-%d %H:%M:%S")
            actual_ds = str(h24.iloc[0]["ds"])
            if expected_ds not in actual_ds:
                reasons.append(
                    f"hour-24 ds: expected '{expected_ds}', got '{actual_ds}'"
                )

    # 8. Non-null numeric prices
    for col in ("dayahead_price", "realtime_price"):
        if col in df.columns:
            null_mask = df[col].isna()
            if null_mask.any():
                bad_hours = df.loc[null_mask, "hour_business"].tolist()
                reasons.append(f"{col}: null in hours {bad_hours}")
            try:
                pd.to_numeric(df[col], errors="raise")
            except (ValueError, TypeError) as exc:
                reasons.append(f"{col}: non-numeric values — {exc}")
        else:
            reasons.append(f"column {col} missing")

    # 9. No _x/_y suffixes
    for col in df.columns:
        if col.endswith("_x") or col.endswith("_y"):
            reasons.append(f"suffix column detected: '{col}'")

    # If structural checks failed, don't bother with manifest checks
    if reasons:
        return False, reasons

    # 10. Manifest exists
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        return False, [f"run_manifest.json not found: {manifest_path}"]

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as exc:
        return False, [f"cannot read manifest {manifest_path}: {exc}"]

    # 11. Five stages complete
    stages = manifest.get("stages", {})
    expected_stages = [
        "ledger_predict", "ledger_weight", "ledger_fuse",
        "ledger_classifier", "final_outputs",
    ]
    for stage_name in expected_stages:
        stage = stages.get(stage_name, {})
        if stage.get("status") != "complete":
            reasons.append(
                f"stage '{stage_name}' status={stage.get('status', 'missing')}, "
                f"expected 'complete'"
            )

    # 12. No manifest errors
    manifest_errors = manifest.get("errors", [])
    if manifest_errors:
        reasons.append(f"manifest has {len(manifest_errors)} error(s): {manifest_errors}")

    return len(reasons) == 0, reasons


def run_ledger_full_range(args: Any) -> dict:
    """
    Main entry for ``--pipeline ledger_full_range``.

    Orchestrates daily ``ledger_full`` (five stages) across *start* .. *end*
    inclusive.  Writes ``range_manifest.json`` and ``range_summary.csv``
    into ``outputs/runs/range_{start}_to_{end}/``.

    Parameters
    ----------
    args : argparse.Namespace
        Must contain: start, end, data_path, plus optional
        continue_on_error, skip_existing_final, range_preflight.

    Returns
    -------
    dict — the range-level manifest.
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

    logger.info(f"=== ledger_full_range: {start_date} to {end_date} ===")

    # Build date list (inclusive)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    date_list = [d.strftime("%Y-%m-%d") for d in date_range]

    range_dir = runs_root / f"range_{start_date}_to_{end_date}"
    range_dir.mkdir(parents=True, exist_ok=True)

    # Initialise range manifest
    range_manifest: dict[str, Any] = {
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

    # ------------------------------------------------------------------
    # Preflight
    # ------------------------------------------------------------------
    if range_preflight:
        preflight_errors, preflight_warnings = _run_preflight(args, start_date)
        if preflight_errors or preflight_warnings:
            range_manifest["preflight_errors"] = preflight_errors
            range_manifest["preflight_warnings"] = preflight_warnings

        if preflight_errors:
            range_manifest["status"] = "preflight_failed"
            range_manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
            range_manifest["note"] = (
                "Preflight validation failed. Run with --no-range-preflight to skip, "
                "or fix the reported issues and retry."
            )
            _write_range_artifacts(range_dir, range_manifest)
            console_msg = (
                f"[ledger_full_range] preflight FAILED — {len(preflight_errors)} error(s)\n"
                f"  Manifest: {range_dir / 'range_manifest.json'}\n"
                f"  Next steps: fix errors above or use --no-range-preflight"
            )
            for err in preflight_errors:
                console_msg += f"\n    ERROR: {err}"
            logger.error(console_msg)
            return range_manifest

        if preflight_warnings:
            for w in preflight_warnings:
                logger.warning(f"Preflight warning: {w}")
                range_manifest["warnings"].append(w)

    # ------------------------------------------------------------------
    # Daily loop
    # ------------------------------------------------------------------
    from pipelines.ledger_full import run_ledger_full

    for target_date in date_list:
        logger.info(f"\n{'='*60}\nRange day: {target_date}\n{'='*60}")

        # --- skip-existing-final check ---
        if skip_existing_final:
            is_valid, skip_reasons = is_existing_final_valid(runs_root, target_date)
            if is_valid:
                logger.info(f"Skipping {target_date}: submission_ready.csv is valid")
                daily_manifest_path = runs_root / target_date / "run_manifest.json"
                range_manifest["daily_results"].append({
                    "date": target_date,
                    "status": "skipped",
                    "manifest_path": str(daily_manifest_path),
                    "submission_ready_path": str(runs_root / target_date / "final" / "submission_ready.csv"),
                    "warnings_count": 0,
                    "errors_count": 0,
                    "stage_statuses": {"ledger_full": "skipped"},
                    "skip_reason": "existing output valid",
                })
                range_manifest["skipped_days"] += 1
                _write_range_artifacts(range_dir, range_manifest)
                continue
            else:
                for r in skip_reasons:
                    logger.warning(f"  {target_date}: skip check failed — {r}")
                    range_manifest["warnings"].append(f"skip check failed for {target_date}: {r}")

        # --- run ledger_full for this day ---
        day_start_ts = time.time()
        day_args = _copy_args_for_day(args, target_date)
        day_result: dict[str, Any] = {}

        try:
            day_result = run_ledger_full(day_args)
            day_status = day_result.get("status", "unknown")
        except KeyboardInterrupt:
            range_manifest["status"] = "interrupted"
            range_manifest["errors"].append(f"Interrupted by user at {target_date}")
            _write_range_artifacts(range_dir, range_manifest)
            logger.error(f"Range interrupted at {target_date}")
            return range_manifest
        except Exception as exc:
            logger.exception(f"Range day {target_date} failed: {exc}")
            day_result = {"status": "error", "error": str(exc)}
            day_status = "error"

        day_elapsed = time.time() - day_start_ts

        # Record result
        daily_manifest_path = runs_root / target_date / "run_manifest.json"
        submission_path = runs_root / target_date / "final" / "submission_ready.csv"

        day_entry: dict[str, Any] = {
            "date": target_date,
            "status": day_status,
            "started_at": day_result.get("started_at"),
            "completed_at": day_result.get("completed_at"),
            "duration_seconds": round(day_elapsed, 1),
            "manifest_path": str(daily_manifest_path),
            "submission_ready_path": str(submission_path) if submission_path.exists() else None,
            "stage_statuses": {},
            "errors_count": 0,
            "warnings_count": 0,
        }

        stages = day_result.get("stages", {})
        for stage_name, stage_data in stages.items():
            if isinstance(stage_data, dict):
                day_entry["stage_statuses"][stage_name] = stage_data.get("status", "unknown")
                day_entry["errors_count"] += 1 if stage_data.get("status") == "failed" else 0

        # Top-level errors/warnings from the day manifest
        day_entry["errors_count"] += len(day_result.get("errors", []))
        day_entry["warnings_count"] = len(day_result.get("warnings", []))

        range_manifest["daily_results"].append(day_entry)

        if day_status in ("complete", "complete_with_warnings"):
            range_manifest["completed_days"] += 1
        elif day_status in ("failed", "error"):
            range_manifest["failed_days"] += 1
            err_msg = f"Day {target_date} status={day_status}"
            if day_result.get("error"):
                err_msg += f": {day_result['error']}"
            range_manifest["errors"].append(err_msg)
            if not continue_on_error:
                range_manifest["status"] = "failed"
                _write_range_artifacts(range_dir, range_manifest)
                logger.error(f"Range stopped at {target_date} (use --continue-on-error to continue)")
                return range_manifest

        # Flush range state after each day
        _write_range_artifacts(range_dir, range_manifest)

    # ------------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------------
    _finalise_range_manifest(range_manifest)
    _write_range_artifacts(range_dir, range_manifest)

    logger.info(
        f"ledger_full_range {start_date}..{end_date}: {range_manifest['status']} "
        f"({range_manifest['completed_days']}/{range_manifest['total_days']} days, "
        f"{range_manifest['failed_days']} failed, "
        f"{range_manifest['skipped_days']} skipped)"
    )
    return range_manifest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_preflight(args: Any, start_date: str) -> tuple[list[str], list[str]]:
    """Strict preflight checks for range pipeline.

    Returns (errors, warnings).  Any errors cause ``preflight_failed``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. data_path exists
    data_path = getattr(args, "data_path", "data/shandong_pmos_hourly.xlsx")
    if not Path(data_path).exists():
        errors.append(f"Data path not found: {data_path}")

    # 2. ledger_root exists
    ledger_root = Path(getattr(args, "ledger_root", "outputs/ledger"))
    if not ledger_root.exists():
        errors.append(
            f"Ledger root not found: {ledger_root}. "
            "Run backfill or copy from fixtures/seed_ledger/. "
            "(Use --no-range-preflight to skip.)"
        )
        return errors, warnings

    # 3. Four ledger files exist and are readable
    ledger_files = {
        "dayahead prediction": ledger_root / "dayahead" / "prediction" / "prediction_ledger.parquet",
        "dayahead actual": ledger_root / "dayahead" / "actual" / "actual_ledger.parquet",
        "realtime prediction": ledger_root / "realtime" / "prediction" / "prediction_ledger.parquet",
        "realtime actual": ledger_root / "realtime" / "actual" / "actual_ledger.parquet",
    }

    ledgers: dict[str, pd.DataFrame] = {}
    for label, path in ledger_files.items():
        if not path.exists():
            errors.append(f"Ledger file not found: {path} ({label})")
            continue
        try:
            ledgers[label] = pd.read_parquet(path)
        except Exception as exc:
            errors.append(
                f"Cannot read parquet ledger: {path} ({label}). "
                f"Ensure pyarrow is installed or regenerate ledger. Error: {exc}"
            )

    if errors:
        return errors, warnings

    # 4. D-30 .. D-1 window coverage for the *start* date
    start_dt = pd.Timestamp(start_date)
    window_end = start_dt - pd.Timedelta(days=1)
    window_start = start_dt - pd.Timedelta(days=30)
    window_dates = set(
        d.strftime("%Y-%m-%d")
        for d in pd.date_range(start=window_start, end=window_end, freq="D")
    )
    expected_days_in_window = len(window_dates)  # should be 30

    for label, df in ledgers.items():
        date_col = "target_day" if "target_day" in df.columns else "business_day"
        if date_col not in df.columns:
            errors.append(f"Ledger {label}: no '{date_col}' column")
            continue

        available = set(pd.to_datetime(df[date_col]).unique())
        available_str = {d.strftime("%Y-%m-%d") for d in available}
        missing = window_dates - available_str

        # Allow extra days and missing only if the whole window isn't covered
        if missing:
            # Check if at least enough days to cover the window, allowing
            # some days to be in the future of the window
            if len(available_str & window_dates) < expected_days_in_window:
                missing_sorted = sorted(missing)[:10]  # show first 10
                errors.append(
                    f"Ledger {label}: missing {len(missing)} day(s) in "
                    f"window {window_start.date()}..{window_end.date()}. "
                    f"First missing: {missing_sorted}"
                )

        # hour_business coverage
        if "hour_business" in df.columns and date_col in df.columns:
            # Check the target window days only
            window_dt_hours = pd.to_datetime(df[date_col])
            window_dates_hours_dt = pd.to_datetime(list(window_dates))
            window_df = df[window_dt_hours.isin(window_dates_hours_dt)]
            hours_per_day = window_df.groupby(date_col)["hour_business"].nunique()
            incomplete = hours_per_day[hours_per_day < 24]
            if not incomplete.empty:
                for bad_day, n_hours in incomplete.head(5).items():
                    bad_day_str = (
                        bad_day.strftime("%Y-%m-%d")
                        if hasattr(bad_day, "strftime")
                        else str(bad_day)
                    )
                    if "actual" in label:
                        errors.append(
                            f"Ledger {label}: day {bad_day_str} has "
                            f"{n_hours}/24 hour rows (expected 24)"
                        )
                    else:
                        warnings.append(
                            f"Ledger {label}: day {bad_day_str} has "
                            f"{n_hours}/24 hour rows"
                        )

        # Model coverage for prediction ledgers
        if "prediction" in label and "model_name" in df.columns:
            if "dayahead" in label:
                expected_models = {"lightgbm", "timesfm", "timemixer"}
            else:
                expected_models = {"timesfm", "sgdfnet", "timemixer", "rt916"}

            models_found = set(df["model_name"].unique())
            missing_models = expected_models - models_found
            if missing_models:
                errors.append(
                    f"Ledger {label}: missing models {missing_models}. "
                    f"Found: {models_found}"
                )

            # Per-day per-model row count check
            if date_col in df.columns and "hour_business" in df.columns:
                window_dt_models = pd.to_datetime(df[date_col])
                window_dates_models_dt = pd.to_datetime(list(window_dates))
                window_df = df[window_dt_models.isin(window_dates_models_dt)]
                model_day_counts = (
                    window_df.groupby([date_col, "model_name"])
                    .size()
                    .reset_index(name="n_rows")
                )
                under = model_day_counts[model_day_counts["n_rows"] < 24]
                for _, row in under.head(10).iterrows():
                    day_str = (
                        row[date_col].strftime("%Y-%m-%d")
                        if hasattr(row[date_col], "strftime")
                        else str(row[date_col])
                    )
                    errors.append(
                        f"Ledger {label}: model '{row['model_name']}' on {day_str} "
                        f"has {row['n_rows']}/24 rows"
                    )

    return errors, warnings


def _is_existing_final_valid(
    runs_root: Path, target_date: str
) -> tuple[bool, list[str]]:
    """Deprecated alias; use the module-level :func:`is_existing_final_valid`."""
    return is_existing_final_valid(runs_root, target_date)


def _copy_args_for_day(args: Any, target_date: str) -> Any:
    """Create a namespace copy with the target date set for ledger_full."""
    day_args = copy.copy(args)
    day_args.date = target_date
    day_args.pipeline = "ledger_full"
    day_args.start = None
    day_args.end = None
    return day_args


def _finalise_range_manifest(manifest: dict) -> None:
    """Derive the final status of the range manifest."""
    total = manifest["total_days"]
    completed = manifest["completed_days"]
    failed = manifest["failed_days"]
    skipped = manifest["skipped_days"]

    if failed == 0 and completed + skipped == total:
        manifest["status"] = "complete"
    elif failed > 0 and completed > 0:
        manifest["status"] = "partial"
    elif completed == 0 and skipped == total and total > 0:
        manifest["status"] = "all_skipped"
    elif failed == total:
        manifest["status"] = "failed"
    elif manifest["status"] not in ("preflight_failed", "interrupted"):
        manifest["status"] = "failed"

    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()


def _write_range_artifacts(range_dir: Path, manifest: dict) -> None:
    """Write both range_manifest.json and range_summary.csv."""
    manifest_path = range_dir / "range_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    _write_range_summary(range_dir, manifest)


def _write_range_summary(range_dir: Path, manifest: dict) -> None:
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

    summary_df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date", "status", "submission_ready_exists", "submission_ready_rows",
                 "errors_count", "warnings_count", "manifest_path", "submission_ready_path"]
    )
    summary_path = range_dir / "range_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.info(f"Range summary: {len(rows)} days -> {summary_path}")
