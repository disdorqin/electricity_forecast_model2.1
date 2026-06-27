#!/usr/bin/env python
"""可复现性检查工具。

用相同种子运行两次 ledger_smoke，比较两次输出的
all_model_predictions_long.csv 是否一致。

用法:
    python scripts/check_reproducibility.py 2026-02-24
    python scripts/check_reproducibility.py 2026-02-24 --seed 42 --deterministic
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd


def _file_sha256(path: Path) -> str:
    """Return SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compare_csv_files(path_a: Path, path_b: Path, label: str) -> list[str]:
    """Compare two CSV files and return list of differences."""
    issues: list[str] = []
    if not path_a.exists() and not path_b.exists():
        return []
    if not path_a.exists():
        issues.append(f"[{label}] Missing in run A")
        return issues
    if not path_b.exists():
        issues.append(f"[{label}] Missing in run B")
        return issues

    df_a = pd.read_csv(path_a)
    df_b = pd.read_csv(path_b)

    if len(df_a) != len(df_b):
        issues.append(f"[{label}] Row count: A={len(df_a)} vs B={len(df_b)}")
        return issues

    # Check y_pred column
    for col in ["y_pred"]:
        if col in df_a.columns and col in df_b.columns:
            if not df_a[col].equals(df_b[col]):
                mismatches = (df_a[col] != df_b[col]).sum()
                max_diff = abs(df_a[col] - df_b[col]).max()
                issues.append(
                    f"[{label}] {col}: {mismatches}/{len(df_a)} rows differ, "
                    f"max_abs_diff={max_diff:.6f}"
                )

    # Compare hashes only when no value differences found
    if not issues:
        sha_a = _file_sha256(path_a)
        sha_b = _file_sha256(path_b)
        if sha_a != sha_b:
            issues.append(
                f"[{label}] SHA256 mismatch (content differs in non-y_pred columns)"
            )

    return issues


def check_reproducibility(
    date: str,
    seed: int = 42,
    deterministic: bool = False,
    keep_tmp: bool = False,
) -> bool:
    """Run ledger_smoke twice and compare outputs."""
    print(f"=== Reproducibility Check: date={date}, seed={seed}, deterministic={deterministic} ===\n")

    tmp_a = Path(tempfile.mkdtemp(prefix="repro_a_"))
    tmp_b = Path(tempfile.mkdtemp(prefix="repro_b_"))

    project_root = Path(__file__).resolve().parent.parent
    results_root = project_root / "outputs" / "repro_check"
    results_root.mkdir(parents=True, exist_ok=True)

    # Clean up any existing output for the target date
    for tmp in [tmp_a, tmp_b]:
        ledger_dir = tmp / "ledger"
        runs_dir = tmp / "runs"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        runs_dir.mkdir(parents=True, exist_ok=True)

    def _run(test_dir: Path, tag: str) -> tuple[bool, Path]:
        """Run ledger_smoke once."""
        cmd = [
            sys.executable, "main.py", date,
            "--pipeline", "ledger_smoke",
            "--ledger-root", str(test_dir / "ledger"),
            "--runs-root", str(test_dir / "runs"),
            "--seed", str(seed),
        ]
        if deterministic:
            cmd.append("--deterministic")

        print(f">>> Run {tag}: {' '.join(cmd)}")
        t0 = time.time()
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        elapsed = time.time() - t0
        print(f"    Exit: {result.returncode}, Elapsed: {elapsed:.1f}s")
        if result.returncode != 0:
            print(f"    STDOUT: {result.stdout[-500:]}")
            print(f"    STDERR: {result.stderr[-500:]}")
        return result.returncode == 0, test_dir

    # Run A
    ok_a, _ = _run(tmp_a, "A")
    # Run B
    ok_b, _ = _run(tmp_b, "B")

    if not ok_a or not ok_b:
        print("\n[FAIL] One or both runs failed")
        if not ok_a:
            print("  Run A: FAILED")
        if not ok_b:
            print("  Run B: FAILED")
        return False

    # Collect all comparison files
    all_ok = True

    # Compare model-level CSV files
    for task in ["dayahead", "realtime"]:
        pred_dir_a = tmp_a / "runs" / date / task / "prediction"
        pred_dir_b = tmp_b / "runs" / date / task / "prediction"

        if not pred_dir_a.exists() or not pred_dir_b.exists():
            print(f"\n  [SKIP] {task}: prediction directory missing")
            continue

        # Compare all_model_predictions_long.csv
        long_a = pred_dir_a / "all_model_predictions_long.csv"
        long_b = pred_dir_b / "all_model_predictions_long.csv"
        issues = _compare_csv_files(long_a, long_b, f"{task}/long")
        for issue in issues:
            print(f"  {issue}")
            all_ok = False

        # Compare per-model files
        csv_files_a = sorted(pred_dir_a.glob("*_predictions.csv"))
        for f_a in csv_files_a:
            if f_a.name == "all_model_predictions_long.csv":
                continue
            f_b = pred_dir_b / f_a.name
            model_label = f"{task}/{f_a.stem.replace('_predictions', '')}"
            issues = _compare_csv_files(f_a, f_b, model_label)
            for issue in issues:
                print(f"  {issue}")
                all_ok = False

    # Compare run manifests
    manifest_a = tmp_a / "runs" / date / "run_manifest.json"
    manifest_b = tmp_b / "runs" / date / "run_manifest.json"
    if manifest_a.exists() and manifest_b.exists():
        sha_a = _file_sha256(manifest_a)
        sha_b = _file_sha256(manifest_b)
        if sha_a != sha_b:
            # Manifest timestamps will differ — check structural equality instead
            import json

            with open(manifest_a) as f:
                m_a = json.load(f)
            with open(manifest_b) as f:
                m_b = json.load(f)
            # Remove timestamps before comparing
            for key in ["started_at", "completed_at"]:
                m_a.pop(key, None)
                m_b.pop(key, None)
            if m_a != m_b:
                print(f"  [WARN] run_manifest.json: structural differences (non-timestamp)")
                all_ok = False

    print()
    if all_ok:
        print("=== Result: PASS (all outputs identical) ===")
    else:
        print("=== Result: FAIL (outputs differ between runs) ===")

    # Copy results for inspection
    shutil.copytree(str(tmp_a), str(results_root / f"{date}_A"), dirs_exist_ok=True)
    shutil.copytree(str(tmp_b), str(results_root / f"{date}_B"), dirs_exist_ok=True)
    print(f"  Results saved to: {results_root}/{date}_A/ and {results_root}/{date}_B/")

    if not keep_tmp:
        shutil.rmtree(str(tmp_a))
        shutil.rmtree(str(tmp_b))
        print(f"  Temp dirs cleaned up")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Check ledger_smoke reproducibility")
    parser.add_argument("date", help="Target date YYYY-MM-DD")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--deterministic", action="store_true", help="Enable deterministic mode")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep temp output directories")
    args = parser.parse_args()

    ok = check_reproducibility(
        args.date,
        seed=args.seed,
        deterministic=args.deterministic,
        keep_tmp=args.keep_tmp,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
