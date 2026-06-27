#!/usr/bin/env python
"""TimeMixer 时间对齐检查工具。

验证 TimeMixer 输出是否符合营业日对齐要求：
  - 24 行 (hour_business 1..24)
  - hour 24 对应的是 D+1 00:00，不是 D 00:00
  - 不存在 hour 0
  - 不存在 D 00:00 的时间戳

可选：与其他模型对比 business_day / hour_business 集合是否一致。

用法:
    python scripts/check_timemixer_alignment.py outputs/runs/2026-02-24
    python scripts/check_timemixer_alignment.py outputs/runs/2026-02-24 --compare
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def _read_csv_safe(path: Path) -> pd.DataFrame | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"  [WARN] Cannot read {path.name}: {e}")
        return None


def check_timemixer_alignment(pred_dir: str, compare: bool = False) -> bool:
    """Check TimeMixer alignment for a given prediction directory."""
    path = Path(pred_dir)
    if not path.is_dir():
        print(f"ERROR: Directory not found: {pred_dir}")
        return False

    print(f"=== TimeMixer Alignment Check: {pred_dir} ===\n")

    all_ok = True

    # Locate TimeMixer predictions
    tm_files = list(path.rglob("*timemixer*_predictions.csv")) + list(
        path.rglob("timemixer*/predictions.csv")
    )
    # Also check direct filenames
    for candidate in ["timemixer_predictions.csv"]:
        fp = path / candidate
        if fp.exists():
            tm_files.append(fp)

    if not tm_files:
        print("  [FAIL] No TimeMixer predictions found")
        return False

    for tm_path in sorted(set(tm_files)):
        print(f"--- {tm_path.relative_to(path.parent)} ---")
        df = _read_csv_safe(tm_path)
        if df is None:
            print("  [FAIL] Cannot read file")
            all_ok = False
            continue

        issues: list[str] = []

        # 1) Row count
        if len(df) != 24:
            issues.append(f"expected 24 rows, got {len(df)}")
        else:
            print(f"  Rows: 24 OK")

        # 2) hour_business check
        if "hour_business" in df.columns:
            hours = sorted(df["hour_business"].dropna().astype(int).unique())
            expected = list(range(1, 25))
            if hours == expected:
                print(f"  hour_business: 1..24 OK")
            else:
                missing = set(expected) - set(hours)
                extra = set(hours) - set(expected)
                if missing:
                    issues.append(f"missing hours: {sorted(missing)}")
                if extra:
                    issues.append(f"extra hours: {sorted(extra)}")

            # Check no hour 0
            if 0 in df["hour_business"].values:
                issues.append("hour_business=0 found!")

        # 3) hour 24 = D+1 00:00 check
        if "hour_business" in df.columns and "ds" in df.columns:
            h24 = df[df["hour_business"] == 24]
            if not h24.empty:
                ds_h24 = pd.to_datetime(h24["ds"].iloc[0])
                if ds_h24.hour == 0:
                    print(f"  hour 24 ds: {ds_h24} OK (D+1 00:00)")
                else:
                    issues.append(f"hour 24 ds={ds_h24}: expected hour=00 (D+1 00:00)")

            # Detect D 00:00 entries (hour_business=24 should be D+1 00:00, which is correct)
            ts_all = pd.to_datetime(df["ds"], errors="coerce")
            midnight_entries = ts_all[ts_all.apply(lambda x: x.hour == 0)]
            if not midnight_entries.empty and "hour_business" in df.columns:
                invalid_midnight = []
                for idx in midnight_entries.index:
                    if df.loc[idx, "hour_business"] != 24:
                        invalid_midnight.append(str(midnight_entries[idx]))
                if invalid_midnight:
                    issues.append(f"non-hour-24 midnight entries: {invalid_midnight}")

        # 4) business_day consistency
        if "business_day" in df.columns and "ds" in df.columns:
            ts_all = pd.to_datetime(df["ds"], errors="coerce")
            biz_days = pd.to_datetime(df["business_day"], errors="coerce")
            # hour 1-23 should have same date as business_day
            non_midnight = df[df["hour_business"] != 24]
            mismatches = 0
            for _, row in non_midnight.iterrows():
                ts = pd.to_datetime(row["ds"])
                bd = pd.to_datetime(row["business_day"])
                if ts.date() != bd.date():
                    mismatches += 1
            if mismatches > 0:
                issues.append(f"{mismatches} rows have ds date != business_day (non-midnight)")

        # Print issues
        for issue in issues:
            print(f"  [FAIL] {issue}")
            all_ok = False

        if not issues:
            print("  Alignment: PASS")
        print()

    # Optional: compare with other models
    if compare:
        print("--- Cross-model comparison ---")
        other_files = []
        for f in path.iterdir():
            if f.name.endswith("_predictions.csv") and "timemixer" not in f.name:
                other_files.append(f)
        if not other_files:
            print("  No other model predictions found for comparison")
        else:
            # Get TimeMixer business_day set
            tm_biz_days = set()
            for tm_path in tm_files:
                df = _read_csv_safe(tm_path)
                if df is not None and "business_day" in df.columns:
                    tm_biz_days.update(df["business_day"].dropna().unique())
            tm_biz_days = sorted(tm_biz_days)

            for other_path in sorted(other_files):
                df_other = _read_csv_safe(other_path)
                if df_other is None:
                    continue
                label = other_path.stem.replace("_predictions", "")
                if "business_day" in df_other.columns:
                    other_biz = sorted(df_other["business_day"].dropna().unique())
                    match = "MATCH" if other_biz == tm_biz_days else "MISMATCH"
                    print(f"  business_day {label}: {other_biz} ({match})")
                if "hour_business" in df_other.columns:
                    other_hours = sorted(df_other["hour_business"].dropna().astype(int).unique())
                    match = "MATCH" if other_hours == list(range(1, 25)) else "MISMATCH"
                    print(f"  hour_business {label}: {other_hours} ({match})")
            print()

    print(f"=== Result: {'ALL OK' if all_ok else 'ISSUES FOUND'} ===")
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Check TimeMixer hour alignment")
    parser.add_argument("pred_dir", help="Path to prediction directory (e.g. outputs/runs/2026-02-24)")
    parser.add_argument("--compare", action="store_true", help="Compare with other models")
    args = parser.parse_args()

    ok = check_timemixer_alignment(args.pred_dir, compare=args.compare)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
