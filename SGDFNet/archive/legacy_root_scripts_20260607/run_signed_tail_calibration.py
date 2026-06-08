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
from run_signed_tail_probability import _hgb_params, _safe_predict_proba, _thresholds


@dataclass
class SignedTailCalibrationConfig:
    experiment_name: str
    data_path: str
    output_root: str
    baseline_artifact: str
    target_year: int = 2025
    val_days: int = 30
    train_min_rows: int = 24 * 90
    tail_quantile: float = 0.90
    min_tail_count: int = 12
    probability_trigger_quantile: float = 0.85
    probability_scope: str = "global"
    calibration_scope: str = "all"
    bias_shrinkage: float = 1.0
    bias_cap_abs: float | None = None
    predicted_abs_gate_quantile: float | None = None
    require_predicted_sign_match: bool = False
    val_min_delta_mae_gain: float = 0.0
    val_min_rt_capped_smape_gain: float = 0.0
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    model_config: dict | None = None


def _load_config(path: str | Path) -> SignedTailCalibrationConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SignedTailCalibrationConfig(
        experiment_name=raw["experiment_name"],
        data_path=raw["data_path"],
        output_root=raw["output_root"],
        baseline_artifact=raw["baseline_artifact"],
        target_year=raw.get("target_year", 2025),
        val_days=raw.get("val_days", 30),
        train_min_rows=raw.get("train_min_rows", 24 * 90),
        tail_quantile=raw.get("tail_quantile", 0.90),
        min_tail_count=raw.get("min_tail_count", 12),
        probability_trigger_quantile=raw.get("probability_trigger_quantile", 0.85),
        probability_scope=raw.get("probability_scope", "global"),
        calibration_scope=raw.get("calibration_scope", "all"),
        bias_shrinkage=raw.get("bias_shrinkage", 1.0),
        bias_cap_abs=raw.get("bias_cap_abs"),
        predicted_abs_gate_quantile=raw.get("predicted_abs_gate_quantile"),
        require_predicted_sign_match=raw.get("require_predicted_sign_match", False),
        val_min_delta_mae_gain=raw.get("val_min_delta_mae_gain", 0.0),
        val_min_rt_capped_smape_gain=raw.get("val_min_rt_capped_smape_gain", 0.0),
        feature_config=FeatureConfig(**raw.get("feature_config", {})),
        model_config=raw.get("model_config", {}),
    )


def _apply_bias_map(df: pd.DataFrame, bias_map: dict[str, float], scope: str) -> pd.DataFrame:
    adjusted = df.copy()
    bias = pd.Series(0.0, index=adjusted.index, dtype=float)
    for key, value in bias_map.items():
        sign, selector = key.split("|", 1)
        base_mask = adjusted["tail_sign"] == sign
        if selector == "all":
            mask = base_mask
        elif selector == "segment=9_16":
            mask = base_mask & (adjusted["segment"] == "9_16")
        else:
            mask = base_mask
        bias.loc[mask] = float(value)
    adjusted["delta_hat"] = adjusted["delta_hat"] + bias
    adjusted["rt_hat"] = adjusted["da_anchor"] + adjusted["delta_hat"]
    adjusted["applied_signed_tail_bias"] = bias
    return adjusted


def _capped_smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    yt = y_true.where(y_true >= 50, 50)
    yp = y_pred.where(y_pred >= 50, 50)
    return float((200.0 * (yp - yt).abs() / (yt.abs() + yp.abs() + 1e-6)).mean())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SGDFNet signed-tail calibration branch on top of point predictions.")
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

        x_train = train_df[feature_cols]
        x_val = val_df[feature_cols]
        x_test = test_df[feature_cols]
        pos_threshold, neg_threshold = _thresholds(train_df["delta_target"], config.tail_quantile, config.min_tail_count)

        y_train_pos = (train_df["delta_target"] >= pos_threshold).astype(int)
        y_train_neg = (train_df["delta_target"] <= neg_threshold).astype(int)
        pos_prob_val = _safe_predict_proba(x_train, y_train_pos, x_val, config.model_config)
        neg_prob_val = _safe_predict_proba(x_train, y_train_neg, x_val, config.model_config)
        pos_prob_test = _safe_predict_proba(x_train, y_train_pos, x_test, config.model_config)
        neg_prob_test = _safe_predict_proba(x_train, y_train_neg, x_test, config.model_config)

        baseline_val_month = baseline_pred[(baseline_pred["split"] == "val") & (baseline_pred["target_month"] == month_label)].copy()
        baseline_test_month = baseline_pred[(baseline_pred["split"] == "test") & (baseline_pred["target_month"] == month_label)].copy()

        val_scored = val_df[["timestamp", "segment", "da_anchor", "rt_actual", "delta_target"]].copy()
        val_scored = val_scored.merge(baseline_val_month[["timestamp", "delta_hat", "rt_hat"]], on="timestamp", how="left")
        val_scored["positive_tail_probability"] = pos_prob_val
        val_scored["negative_tail_probability"] = neg_prob_val
        val_scored["abs_delta_hat"] = val_scored["delta_hat"].abs()

        test_scored = test_df[["timestamp", "segment", "da_anchor", "rt_actual", "delta_target"]].copy()
        test_scored = test_scored.merge(baseline_test_month[["timestamp", "delta_hat", "rt_hat"]], on="timestamp", how="left")
        test_scored["positive_tail_probability"] = pos_prob_test
        test_scored["negative_tail_probability"] = neg_prob_test
        test_scored["abs_delta_hat"] = test_scored["delta_hat"].abs()
        test_scored["target_month"] = month_label
        test_scored["split"] = "test"

        if config.probability_scope == "segment_9_16":
            val_scope = val_scored[val_scored["segment"] == "9_16"].copy()
        else:
            val_scope = val_scored.copy()

        pos_trigger = float(val_scope["positive_tail_probability"].quantile(config.probability_trigger_quantile))
        neg_trigger = float(val_scope["negative_tail_probability"].quantile(config.probability_trigger_quantile))
        abs_gate_threshold = None
        if config.predicted_abs_gate_quantile is not None:
            abs_gate_threshold = float(val_scope["abs_delta_hat"].quantile(config.predicted_abs_gate_quantile))

        bias_map: dict[str, float] = {}
        residual = val_scope["delta_target"] - val_scope["delta_hat"]
        val_scope = val_scope.assign(_residual=residual)

        pos_mask = val_scope["positive_tail_probability"] >= pos_trigger
        neg_mask = val_scope["negative_tail_probability"] >= neg_trigger
        if abs_gate_threshold is not None:
            pos_mask = pos_mask & (val_scope["abs_delta_hat"] >= abs_gate_threshold)
            neg_mask = neg_mask & (val_scope["abs_delta_hat"] >= abs_gate_threshold)
        if config.require_predicted_sign_match:
            pos_mask = pos_mask & (val_scope["delta_hat"] > 0)
            neg_mask = neg_mask & (val_scope["delta_hat"] < 0)

        if config.calibration_scope == "segment_9_16":
            pos_mask = pos_mask & (val_scope["segment"] == "9_16")
            neg_mask = neg_mask & (val_scope["segment"] == "9_16")
            pos_selector = "segment=9_16"
            neg_selector = "segment=9_16"
        else:
            pos_selector = "all"
            neg_selector = "all"

        if pos_mask.any():
            positive_bias = float(val_scope.loc[pos_mask, "_residual"].median()) * float(config.bias_shrinkage)
            if config.bias_cap_abs is not None:
                positive_bias = float(np.clip(positive_bias, -config.bias_cap_abs, config.bias_cap_abs))
            pos_val_subset = val_scope.loc[pos_mask].copy()
            pos_delta_mae_before = float((pos_val_subset["delta_target"] - pos_val_subset["delta_hat"]).abs().mean())
            pos_delta_mae_after = float((pos_val_subset["delta_target"] - (pos_val_subset["delta_hat"] + positive_bias)).abs().mean())
            pos_rt_capped_before = _capped_smape(pos_val_subset["rt_actual"], pos_val_subset["rt_hat"])
            pos_rt_capped_after = _capped_smape(pos_val_subset["rt_actual"], pos_val_subset["da_anchor"] + pos_val_subset["delta_hat"] + positive_bias)
            if (
                (pos_delta_mae_before - pos_delta_mae_after) >= float(config.val_min_delta_mae_gain)
                and (pos_rt_capped_before - pos_rt_capped_after) >= float(config.val_min_rt_capped_smape_gain)
            ):
                bias_map[f"positive|{pos_selector}"] = positive_bias
        if neg_mask.any():
            negative_bias = float(val_scope.loc[neg_mask, "_residual"].median()) * float(config.bias_shrinkage)
            if config.bias_cap_abs is not None:
                negative_bias = float(np.clip(negative_bias, -config.bias_cap_abs, config.bias_cap_abs))
            neg_val_subset = val_scope.loc[neg_mask].copy()
            neg_delta_mae_before = float((neg_val_subset["delta_target"] - neg_val_subset["delta_hat"]).abs().mean())
            neg_delta_mae_after = float((neg_val_subset["delta_target"] - (neg_val_subset["delta_hat"] + negative_bias)).abs().mean())
            neg_rt_capped_before = _capped_smape(neg_val_subset["rt_actual"], neg_val_subset["rt_hat"])
            neg_rt_capped_after = _capped_smape(neg_val_subset["rt_actual"], neg_val_subset["da_anchor"] + neg_val_subset["delta_hat"] + negative_bias)
            if (
                (neg_delta_mae_before - neg_delta_mae_after) >= float(config.val_min_delta_mae_gain)
                and (neg_rt_capped_before - neg_rt_capped_after) >= float(config.val_min_rt_capped_smape_gain)
            ):
                bias_map[f"negative|{neg_selector}"] = negative_bias

        test_scored["tail_sign"] = np.where(
            test_scored["positive_tail_probability"] >= pos_trigger,
            "positive",
            np.where(test_scored["negative_tail_probability"] >= neg_trigger, "negative", "none"),
        )
        if abs_gate_threshold is not None:
            test_scored.loc[test_scored["abs_delta_hat"] < abs_gate_threshold, "tail_sign"] = "none"
        if config.require_predicted_sign_match:
            test_scored.loc[(test_scored["tail_sign"] == "positive") & (test_scored["delta_hat"] <= 0), "tail_sign"] = "none"
            test_scored.loc[(test_scored["tail_sign"] == "negative") & (test_scored["delta_hat"] >= 0), "tail_sign"] = "none"
        adjusted = _apply_bias_map(test_scored[test_scored["tail_sign"] != "none"].copy(), bias_map, config.calibration_scope)
        untouched = test_scored[test_scored["tail_sign"] == "none"].copy()
        untouched["applied_signed_tail_bias"] = 0.0
        adjusted_month = pd.concat([adjusted, untouched], ignore_index=True).sort_values("timestamp")
        adjusted_month["positive_tail_trigger"] = pos_trigger
        adjusted_month["negative_tail_trigger"] = neg_trigger
        adjusted_month["predicted_abs_gate_threshold"] = abs_gate_threshold if abs_gate_threshold is not None else np.nan
        adjusted_month["positive_tail_threshold_train"] = pos_threshold
        adjusted_month["negative_tail_threshold_train"] = neg_threshold
        all_rows.append(adjusted_month)

        monthly_rows.append(
            {
                "month": month_label,
                "positive_tail_trigger": pos_trigger,
                "negative_tail_trigger": neg_trigger,
                "positive_bias": bias_map.get(f"positive|{pos_selector}", 0.0),
                "negative_bias": bias_map.get(f"negative|{neg_selector}", 0.0),
                "applied_fraction": float((adjusted_month["tail_sign"] != "none").mean()),
                "positive_applied_fraction": float((adjusted_month["tail_sign"] == "positive").mean()),
                "negative_applied_fraction": float((adjusted_month["tail_sign"] == "negative").mean()),
                "predicted_abs_gate_threshold": abs_gate_threshold if abs_gate_threshold is not None else np.nan,
            }
        )

    predictions = pd.concat(all_rows, ignore_index=True).sort_values("timestamp")
    predictions.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(run_dir / "signed_tail_calibration_monthly_summary.csv", index=False, encoding="utf-8-sig")
    summary = {
        "mean_applied_fraction": float(monthly["applied_fraction"].mean()),
        "mean_positive_applied_fraction": float(monthly["positive_applied_fraction"].mean()),
        "mean_negative_applied_fraction": float(monthly["negative_applied_fraction"].mean()),
        "config_path": str(Path(args.config).resolve()),
        "baseline_artifact": config.baseline_artifact,
        "bias_shrinkage": config.bias_shrinkage,
        "bias_cap_abs": config.bias_cap_abs,
        "predicted_abs_gate_quantile": config.predicted_abs_gate_quantile,
        "require_predicted_sign_match": config.require_predicted_sign_match,
        "val_min_delta_mae_gain": config.val_min_delta_mae_gain,
        "val_min_rt_capped_smape_gain": config.val_min_rt_capped_smape_gain,
    }
    (run_dir / "signed_tail_calibration_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
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
