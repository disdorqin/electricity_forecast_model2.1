from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import average_precision_score, brier_score_loss

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
import sys
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.data_contract import FeatureConfig, build_feature_manifest, load_dataset, preprocess_dataframe
from sgdfnet.protocol_b import _prepare_splits, _month_starts


@dataclass
class ProbabilityConfig:
    experiment_name: str
    data_path: str
    output_root: str
    baseline_artifact: str
    target_year: int = 2025
    val_days: int = 30
    train_min_rows: int = 24 * 90
    spike_quantile: float = 0.90
    interval_alpha_low: float = 0.10
    interval_alpha_high: float = 0.90
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    model_config: dict | None = None


def _load_config(path: str | Path) -> ProbabilityConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ProbabilityConfig(
        experiment_name=raw["experiment_name"],
        data_path=raw["data_path"],
        output_root=raw["output_root"],
        baseline_artifact=raw["baseline_artifact"],
        target_year=raw.get("target_year", 2025),
        val_days=raw.get("val_days", 30),
        train_min_rows=raw.get("train_min_rows", 24 * 90),
        spike_quantile=raw.get("spike_quantile", 0.90),
        interval_alpha_low=raw.get("interval_alpha_low", 0.10),
        interval_alpha_high=raw.get("interval_alpha_high", 0.90),
        feature_config=FeatureConfig(**raw.get("feature_config", {})),
        model_config=raw.get("model_config", {}),
    )


def _hgb_params(model_config: dict) -> dict:
    return {
        "learning_rate": model_config.get("learning_rate", 0.05),
        "max_depth": model_config.get("max_depth", 6),
        "max_iter": model_config.get("max_iter", 300),
        "min_samples_leaf": model_config.get("min_samples_leaf", 40),
        "l2_regularization": model_config.get("l2_regularization", 0.1),
        "random_state": model_config.get("random_state", 42),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SGDFNet V2 probability/interval branch on top of frozen point predictions.")
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
    baseline_test = baseline_pred[baseline_pred["split"] == "test"].copy()
    baseline_val = baseline_pred[baseline_pred["split"] == "val"].copy()

    all_rows = []
    summary_rows = []
    for month_start in _month_starts(config.target_year):
        month_label = month_start.strftime("%Y-%m")
        train_df, val_df, test_df = _prepare_splits(frame, month_start, config.val_days)
        if len(train_df) < config.train_min_rows or val_df.empty or test_df.empty:
            continue
        x_train = train_df[feature_cols]
        x_val = val_df[feature_cols]
        x_test = test_df[feature_cols]

        baseline_val_month = baseline_val[baseline_val["target_month"] == month_label][["timestamp", "delta_hat", "rt_hat"]].copy()
        baseline_test_month = baseline_test[baseline_test["target_month"] == month_label][["timestamp", "delta_hat", "rt_hat"]].copy()

        lower = HistGradientBoostingRegressor(loss="quantile", quantile=config.interval_alpha_low, early_stopping=False, **_hgb_params(config.model_config))
        upper = HistGradientBoostingRegressor(loss="quantile", quantile=config.interval_alpha_high, early_stopping=False, **_hgb_params(config.model_config))
        lower.fit(x_train, train_df["delta_target"].to_numpy(dtype=float))
        upper.fit(x_train, train_df["delta_target"].to_numpy(dtype=float))
        q_low_test = lower.predict(x_test)
        q_high_test = upper.predict(x_test)

        threshold = float(train_df["delta_target"].abs().quantile(config.spike_quantile))
        y_train_spike = (train_df["delta_target"].abs() >= threshold).astype(int)
        clf = HistGradientBoostingClassifier(early_stopping=False, **_hgb_params(config.model_config))
        clf.fit(x_train, y_train_spike.to_numpy(dtype=int))
        spike_prob_test = clf.predict_proba(x_test)[:, 1]

        merged = test_df[["timestamp", "segment", "segment_id", "da_anchor", "rt_actual", "delta_target"]].copy()
        merged["target_month"] = month_label
        merged = merged.merge(baseline_test_month, on="timestamp", how="left")
        merged["delta_q_low"] = q_low_test
        merged["delta_q_high"] = q_high_test
        merged["rt_q_low"] = merged["da_anchor"] + merged["delta_q_low"]
        merged["rt_q_high"] = merged["da_anchor"] + merged["delta_q_high"]
        merged["spike_probability"] = spike_prob_test
        merged["spike_label_train_threshold"] = threshold
        merged["split"] = "test"
        all_rows.append(merged)

        topk = max(1, int(len(merged) * (1.0 - config.spike_quantile)))
        truth_spike = (merged["delta_target"].abs() >= threshold).astype(int)
        top_idx = merged["spike_probability"].rank(method="first", ascending=False) <= topk
        recall_topk = float(truth_spike[top_idx].sum() / max(truth_spike.sum(), 1))
        ap = float(average_precision_score(truth_spike, merged["spike_probability"])) if truth_spike.sum() > 0 else float("nan")
        coverage = float(((merged["rt_actual"] >= merged["rt_q_low"]) & (merged["rt_actual"] <= merged["rt_q_high"])).mean())
        summary_rows.append(
            {
                "month": month_label,
                "spike_threshold": threshold,
                "spike_recall_topk": recall_topk,
                "spike_average_precision": ap,
                "interval_coverage": coverage,
                "interval_mean_width": float((merged["rt_q_high"] - merged["rt_q_low"]).mean()),
                "interval_brier_proxy": float(brier_score_loss(truth_spike, merged["spike_probability"])) if truth_spike.nunique() > 1 else float("nan"),
            }
        )

    predictions = pd.concat(all_rows, ignore_index=True).sort_values("timestamp")
    predictions.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    monthly = pd.DataFrame(summary_rows)
    monthly.to_csv(run_dir / "probability_monthly_summary.csv", index=False, encoding="utf-8-sig")

    prob_summary = {
        "mean_spike_recall_topk": float(monthly["spike_recall_topk"].mean()),
        "mean_spike_average_precision": float(monthly["spike_average_precision"].mean()),
        "mean_interval_coverage": float(monthly["interval_coverage"].mean()),
        "mean_interval_width": float(monthly["interval_mean_width"].mean()),
        "mean_interval_brier_proxy": float(monthly["interval_brier_proxy"].mean()),
        "config_path": str(Path(args.config).resolve()),
        "baseline_artifact": config.baseline_artifact,
    }
    (run_dir / "probability_summary.json").write_text(json.dumps(prob_summary, ensure_ascii=False, indent=2), encoding="utf-8")
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
