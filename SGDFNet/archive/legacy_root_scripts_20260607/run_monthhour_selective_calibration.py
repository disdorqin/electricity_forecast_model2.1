from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
import sys
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.data_contract import FeatureConfig, build_feature_manifest, load_dataset, preprocess_dataframe
from sgdfnet.protocol_b import _month_starts, _prepare_splits


@dataclass
class MonthHourSelectiveCalibrationConfig:
    experiment_name: str
    data_path: str
    output_root: str
    baseline_artifact: str
    target_year: int = 2025
    val_days: int = 30
    train_min_rows: int = 24 * 90
    calibration_hours: list[int] = field(default_factory=lambda: [9, 10, 11, 14, 15, 16])
    calibration_segments: list[str] = field(default_factory=lambda: ["9_16"])
    month_bucket_mode: str = "season"
    min_group_size: int = 8
    bias_shrinkage: float = 0.5
    bias_cap_abs: float | None = None
    val_min_delta_mae_gain: float = 0.0
    val_min_rt_capped_smape_gain: float = 0.0
    require_predicted_sign_match: bool = False
    predicted_abs_gate_quantile: float | None = None
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)


def _load_config(path: str | Path) -> MonthHourSelectiveCalibrationConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return MonthHourSelectiveCalibrationConfig(
        experiment_name=raw["experiment_name"],
        data_path=raw["data_path"],
        output_root=raw["output_root"],
        baseline_artifact=raw["baseline_artifact"],
        target_year=raw.get("target_year", 2025),
        val_days=raw.get("val_days", 30),
        train_min_rows=raw.get("train_min_rows", 24 * 90),
        calibration_hours=raw.get("calibration_hours", [9, 10, 11, 14, 15, 16]),
        calibration_segments=raw.get("calibration_segments", ["9_16"]),
        month_bucket_mode=raw.get("month_bucket_mode", "season"),
        min_group_size=raw.get("min_group_size", 8),
        bias_shrinkage=raw.get("bias_shrinkage", 0.5),
        bias_cap_abs=raw.get("bias_cap_abs"),
        val_min_delta_mae_gain=raw.get("val_min_delta_mae_gain", 0.0),
        val_min_rt_capped_smape_gain=raw.get("val_min_rt_capped_smape_gain", 0.0),
        require_predicted_sign_match=raw.get("require_predicted_sign_match", False),
        predicted_abs_gate_quantile=raw.get("predicted_abs_gate_quantile"),
        feature_config=FeatureConfig(**raw.get("feature_config", {})),
    )


def _season_bucket(ts: pd.Timestamp) -> str:
    month = int(ts.month)
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def _capped_smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    yt = y_true.where(y_true >= 50, 50)
    yp = y_pred.where(y_pred >= 50, 50)
    return float((200.0 * (yp - yt).abs() / (yt.abs() + yp.abs() + 1e-6)).mean())


def _month_bucket(series: pd.Series, mode: str) -> pd.Series:
    ts = pd.to_datetime(series)
    if mode == "month":
        return ts.dt.strftime("%m")
    if mode == "quarter":
        return ("Q" + ts.dt.quarter.astype(str))
    return ts.map(_season_bucket)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SGDFNet month-hour selective calibration on top of point predictions.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = _load_config(args.config)
    output_root = PROJECT_ROOT.parent / config.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / f"{config.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_df = load_dataset(PROJECT_ROOT.parent / config.data_path)
    frame, feature_cols = preprocess_dataframe(raw_df, config.feature_config)
    build_feature_manifest(feature_cols).to_csv(run_dir / "feature_manifest.csv", index=False, encoding="utf-8-sig")

    baseline_pred = pd.read_csv(PROJECT_ROOT.parent / config.baseline_artifact / "predictions.csv")
    baseline_pred["timestamp"] = pd.to_datetime(baseline_pred["timestamp"])

    all_rows = []
    monthly_rows = []
    for month_start in _month_starts(config.target_year):
        month_label = month_start.strftime("%Y-%m")
        train_df, val_df, test_df = _prepare_splits(frame, month_start, config.val_days)
        if len(train_df) < config.train_min_rows or val_df.empty or test_df.empty:
            continue

        baseline_val_month = baseline_pred[(baseline_pred["split"] == "val") & (baseline_pred["target_month"] == month_label)].copy()
        baseline_test_month = baseline_pred[(baseline_pred["split"] == "test") & (baseline_pred["target_month"] == month_label)].copy()

        val_scored = val_df[["timestamp", "segment", "da_anchor", "rt_actual", "delta_target"]].copy()
        val_scored = val_scored.merge(baseline_val_month[["timestamp", "delta_hat", "rt_hat"]], on="timestamp", how="left")
        test_scored = test_df[["timestamp", "segment", "da_anchor", "rt_actual", "delta_target"]].copy()
        test_scored = test_scored.merge(baseline_test_month[["timestamp", "delta_hat", "rt_hat"]], on="timestamp", how="left")

        val_scored["hour"] = pd.to_datetime(val_scored["timestamp"]).dt.hour.replace({0: 24}).astype(int)
        test_scored["hour"] = pd.to_datetime(test_scored["timestamp"]).dt.hour.replace({0: 24}).astype(int)
        val_scored["month_bucket"] = _month_bucket(val_scored["timestamp"], config.month_bucket_mode)
        test_scored["month_bucket"] = _month_bucket(test_scored["timestamp"], config.month_bucket_mode)
        val_scored["abs_delta_hat"] = val_scored["delta_hat"].abs()
        test_scored["abs_delta_hat"] = test_scored["delta_hat"].abs()
        val_scored["pred_sign"] = np.sign(val_scored["delta_hat"]).astype(int)
        test_scored["pred_sign"] = np.sign(test_scored["delta_hat"]).astype(int)

        abs_gate_threshold = None
        if config.predicted_abs_gate_quantile is not None:
            abs_gate_threshold = float(val_scored["abs_delta_hat"].quantile(config.predicted_abs_gate_quantile))

        bias_records: list[dict[str, object]] = []
        val_scored["_residual"] = val_scored["delta_target"] - val_scored["delta_hat"]
        base_mask = val_scored["segment"].isin(config.calibration_segments) & val_scored["hour"].isin(config.calibration_hours)
        if abs_gate_threshold is not None:
            base_mask = base_mask & (val_scored["abs_delta_hat"] >= abs_gate_threshold)

        for (segment, bucket, hour), group in val_scored[base_mask].groupby(["segment", "month_bucket", "hour"], dropna=False):
            if len(group) < config.min_group_size:
                continue
            for sign_key in ([1, -1] if config.require_predicted_sign_match else [0]):
                subgroup = group[group["pred_sign"] == sign_key].copy() if sign_key != 0 else group.copy()
                if len(subgroup) < config.min_group_size:
                    continue
                bias = float(subgroup["_residual"].median()) * float(config.bias_shrinkage)
                if config.bias_cap_abs is not None:
                    bias = float(np.clip(bias, -config.bias_cap_abs, config.bias_cap_abs))
                delta_mae_before = float((subgroup["delta_target"] - subgroup["delta_hat"]).abs().mean())
                delta_mae_after = float((subgroup["delta_target"] - (subgroup["delta_hat"] + bias)).abs().mean())
                rt_capped_before = _capped_smape(subgroup["rt_actual"], subgroup["rt_hat"])
                rt_capped_after = _capped_smape(subgroup["rt_actual"], subgroup["da_anchor"] + subgroup["delta_hat"] + bias)
                if (
                    (delta_mae_before - delta_mae_after) >= float(config.val_min_delta_mae_gain)
                    and (rt_capped_before - rt_capped_after) >= float(config.val_min_rt_capped_smape_gain)
                ):
                    bias_records.append(
                        {
                            "segment": segment,
                            "month_bucket": bucket,
                            "hour": int(hour),
                            "pred_sign": int(sign_key),
                            "bias": bias,
                            "rows": int(len(subgroup)),
                        }
                    )

        test_scored["target_month"] = month_label
        test_scored["split"] = "test"
        test_scored["applied_monthhour_bias"] = 0.0
        active_mask = test_scored["segment"].isin(config.calibration_segments) & test_scored["hour"].isin(config.calibration_hours)
        if abs_gate_threshold is not None:
            active_mask = active_mask & (test_scored["abs_delta_hat"] >= abs_gate_threshold)

        for record in bias_records:
            mask = (
                active_mask
                & (test_scored["segment"] == record["segment"])
                & (test_scored["month_bucket"] == record["month_bucket"])
                & (test_scored["hour"] == record["hour"])
            )
            if config.require_predicted_sign_match and int(record["pred_sign"]) != 0:
                mask = mask & (test_scored["pred_sign"] == int(record["pred_sign"]))
            test_scored.loc[mask, "applied_monthhour_bias"] = float(record["bias"])

        test_scored["delta_hat"] = test_scored["delta_hat"] + test_scored["applied_monthhour_bias"]
        test_scored["rt_hat"] = test_scored["da_anchor"] + test_scored["delta_hat"]
        all_rows.append(test_scored.copy())

        monthly_rows.append(
            {
                "month": month_label,
                "applied_fraction": float((test_scored["applied_monthhour_bias"] != 0.0).mean()),
                "mean_abs_applied_bias": float(test_scored["applied_monthhour_bias"].abs().mean()),
                "n_bias_records": int(len(bias_records)),
                "predicted_abs_gate_threshold": abs_gate_threshold if abs_gate_threshold is not None else np.nan,
            }
        )

    predictions = pd.concat(all_rows, ignore_index=True).sort_values("timestamp")
    predictions.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(run_dir / "monthhour_selective_monthly_summary.csv", index=False, encoding="utf-8-sig")
    summary = {
        "mean_applied_fraction": float(monthly["applied_fraction"].mean()),
        "mean_abs_applied_bias": float(monthly["mean_abs_applied_bias"].mean()),
        "mean_bias_records": float(monthly["n_bias_records"].mean()),
        "config_path": str(Path(args.config).resolve()),
        "baseline_artifact": config.baseline_artifact,
        "calibration_hours": config.calibration_hours,
        "calibration_segments": config.calibration_segments,
    }
    (run_dir / "monthhour_selective_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "config_path": str(Path(args.config).resolve()),
                "run_dir": str(run_dir.resolve()),
                "feature_columns": feature_cols,
                "baseline_artifact": config.baseline_artifact,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(str(run_dir))


if __name__ == "__main__":
    main()
