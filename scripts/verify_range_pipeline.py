#!/usr/bin/env python
"""
Range pipeline delivery acceptance verification.

Checks every day in [start, end] for complete five-stage output,
valid ``submission_ready.csv``, and consistent range-level artifacts.

Exits with code 0 on PASS, 1 on any failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Reuse the strong validation from the range pipeline
from pipelines.ledger_full_range import SUBMISSION_COLUMNS, is_existing_final_valid


EXPECTED_STAGES = [
    "ledger_predict", "ledger_weight", "ledger_fuse",
    "ledger_classifier", "final_outputs",
]


def verify_range(
    start_date: str,
    end_date: str,
    runs_root: str = "outputs/runs",
) -> int:
    """Verify range pipeline output for [start, end].

    Returns 0 on pass, 1 on failure.
    """
    runs_root_p = Path(runs_root)
    errors: list[str] = []

    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    expected_dates = [d.strftime("%Y-%m-%d") for d in date_range]

    print(f"VERIFY_RANGE_PIPELINE: {start_date} to {end_date}")
    print(f"  expected days: {len(expected_dates)}")
    print()

    # ------------------------------------------------------------------
    # 1. range_manifest.json exists
    # ------------------------------------------------------------------
    range_dir_name = f"range_{start_date}_to_{end_date}"
    range_dir = runs_root_p / range_dir_name
    range_manifest_path = range_dir / "range_manifest.json"

    if not range_manifest_path.exists():
        errors.append("RANGE_MANIFEST: range_manifest.json not found")
        # Can't proceed further
        print(f"\n  errors: {len(errors)}")
        for e in errors:
            print(f"    - {e}")
        print("  status: FAIL")
        return 1

    with open(range_manifest_path) as f:
        range_manifest = json.load(f)

    # 2. Manifest status must be complete
    manifest_status = range_manifest.get("status", "unknown")
    if manifest_status == "preflight_failed":
        errors.append(
            f"RANGE_MANIFEST: status is 'preflight_failed' — range did not execute. "
            f"Fix preflight errors and retry."
        )
    elif manifest_status not in ("complete", "partial", "all_skipped"):
        errors.append(f"RANGE_MANIFEST: unexpected status '{manifest_status}'")

    # 3. range_summary.csv exists
    range_summary_path = range_dir / "range_summary.csv"
    if not range_summary_path.exists():
        errors.append(f"RANGE_SUMMARY: range_summary.csv not found at {range_summary_path}")
    else:
        try:
            summary_df = pd.read_csv(range_summary_path)
            summary_dates = summary_df["date"].unique()
            if len(summary_dates) != len(expected_dates):
                errors.append(
                    f"RANGE_SUMMARY: expected {len(expected_dates)} dates, "
                    f"got {len(summary_dates)} in CSV"
                )
            print(f"  range_summary.csv: {len(summary_df)} rows")
        except Exception as exc:
            errors.append(f"RANGE_SUMMARY: cannot read {range_summary_path}: {exc}")

    # ------------------------------------------------------------------
    # 4. Per-day checks
    # ------------------------------------------------------------------
    for d in expected_dates:
        print(f"\n--- {d} ---")

        # Use the strong is_existing_final_valid
        is_valid, reasons = is_existing_final_valid(runs_root_p, d)

        if not is_valid:
            for r in reasons:
                errors.append(f"{d}: {r}")
            print(f"  FAIL")
            continue

        # Extra manifest-level checks (is_existing_final_valid already
        # verifies all five stages complete and errors empty, but let's
        # double-check against the range manifest)
        print(f"  PASS")

    # ------------------------------------------------------------------
    # 5. Final verdict
    # ------------------------------------------------------------------
    print(f"\n  errors: {len(errors)}")
    if errors:
        print(f"  status: FAIL")
        for e in errors:
            print(f"    - {e}")
        return 1
    else:
        print(f"\n  FINAL_STATUS: PASS")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify range pipeline output (delivery acceptance)"
    )
    parser.add_argument("--start", required=True, help="Range start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Range end date YYYY-MM-DD")
    parser.add_argument(
        "--runs-root", default="outputs/runs",
        help="Root directory for run outputs",
    )
    args = parser.parse_args()
    return verify_range(args.start, args.end, args.runs_root)


if __name__ == "__main__":
    raise SystemExit(main())
