from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
import sys
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.data_contract import FeatureConfig, build_feature_manifest, load_dataset, preprocess_dataframe
from sgdfnet.protocol_b import _month_starts, _prepare_splits


@dataclass
class SignedTailConfig:
    experiment_name: str
    data_path: str
    output_root: str
    baseline_artifact: str
    target_year: int = 2025
    val_days: int = 30
    train_min_rows: int = 24 * 90
    tail_quantile: float = 0.90
    min_tail_count: int = 12
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    model_config: dict | None = None


def _load_config(path: str | Path) -> SignedTailConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SignedTailConfig(
        experiment_name=raw["experiment_name"],
        data_path=raw["data_path"],
        output_root=raw["output_root"],
        baseline_artifact=raw["baseline_artifact"],
        target_year=raw.get("target_year", 2025),
        val_days=raw.get("val_days", 30),
        train_min_rows=raw.get("train_min_rows", 24 * 90),
        tail_quantile=raw.get("tail_quantile", 0.90),
        min_tail_count=raw.get("min_tail_count", 12),
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


def _safe_predict_proba(x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, model_config: dict) -> np.ndarray:
    if y_train.nunique() < 2:
        return np.full(len(x_test), float(y_train.iloc[0]) if len(y_train) else 0.0, dtype=float)
    clf = HistGradientBoostingClassifier(early_stopping=False, **_hgb_params(model_config))
    clf.fit(x_train, y_train.to_numpy(dtype=int))
    return clf.predict_proba(x_test)[:, 1]


def _thresholds(train_delta: pd.Series, tail_quantile: float, min_tail_count: int) -> tuple[float, float]:
    positive = train_delta[train_delta > 0]
    negative = train_delta[train_delta < 0]

    if len(positive) >= min_tail_count:
        pos_threshold = float(positive.quantile(tail_quantile))
    elif len(positive) > 0:
        pos_threshold = float(positive.max())
    else:
        pos_threshold = float("inf")

    if len(negative) >= min_tail_count:
        neg_threshold = float(negative.quantile(1.0 - tail_quantile))
    elif len(negative) > 0:
        neg_threshold = float(negative.min())
    else:
        neg_threshold = float("-inf")

    return pos_threshold, neg_threshold


def _rank_recall(labels: pd.Series, scores: pd.Series) -> float:
    positives = int(labels.sum())
    if positives <= 0:
        return float("nan")
    top_idx = scores.rank(method="first", ascending=False) <= positives
    return float(labels[top_idx].sum() / positives)


def _safe_ap(labels: pd.Series, scores: pd.Series) -> float:
    if labels.sum() <= 0:
        return float("nan")
    if labels.nunique() < 2:
        return 1.0
    return float(average_precision_score(labels, scores))


def _safe_brier(labels: pd.Series, scores: pd.Series) -> float:
    if labels.nunique() < 2:
        return float("nan")
    return float(brier_score_loss(labels, scores))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SGDFNet signed-tail probability branch on top of point predictions.")
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

    all_rows = []
    summary_rows = []
    for month_start in _month_starts(config.target_year):
        month_label = month_start.strftime("%Y-%m")
        train_df, _, test_df = _prepare_splits(frame, month_start, config.val_days)
        if len(train_df) < config.train_min_rows or test_df.empty:
            continue

        x_train = train_df[feature_cols]
        x_test = test_df[feature_cols]
        pos_threshold, neg_threshold = _thresholds(train_df["delta_target"], config.tail_quantile, config.min_tail_count)

        y_train_pos = (train_df["delta_target"] >= pos_threshold).astype(int)
        y_train_neg = (train_df["delta_target"] <= neg_threshold).astype(int)
        pos_prob = _safe_predict_proba(x_train, y_train_pos, x_test, config.model_config)
        neg_prob = _safe_predict_proba(x_train, y_train_neg, x_test, config.model_config)

        baseline_test_month = baseline_test[baseline_test["target_month"] == month_label].copy()
        merged = test_df[["timestamp", "segment", "segment_id", "da_anchor", "rt_actual", "delta_target"]].copy()
        merged["target_month"] = month_label
        merged = merged.merge(baseline_test_month[["timestamp", "delta_hat", "rt_hat"]], on="timestamp", how="left")
        merged["positive_tail_probability"] = pos_prob
        merged["negative_tail_probability"] = neg_prob
        merged["signed_tail_probability"] = np.maximum(pos_prob, neg_prob)
        merged["positive_tail_threshold_train"] = pos_threshold
        merged["negative_tail_threshold_train"] = neg_threshold
        merged["split"] = "test"
        all_rows.append(merged)

        pos_truth = (merged["delta_target"] >= pos_threshold).astype(int)
        neg_truth = (merged["delta_target"] <= neg_threshold).astype(int)
        summary_rows.append(
            {
                "month": month_label,
                "positive_tail_threshold_train": pos_threshold,
                "negative_tail_threshold_train": neg_threshold,
                "positive_tail_recall_topk": _rank_recall(pos_truth, merged["positive_tail_probability"]),
                "negative_tail_recall_topk": _rank_recall(neg_truth, merged["negative_tail_probability"]),
                "positive_tail_average_precision": _safe_ap(pos_truth, merged["positive_tail_probability"]),
                "negative_tail_average_precision": _safe_ap(neg_truth, merged["negative_tail_probability"]),
                "positive_tail_brier": _safe_brier(pos_truth, merged["positive_tail_probability"]),
                "negative_tail_brier": _safe_brier(neg_truth, merged["negative_tail_probability"]),
                "signed_tail_probability_mean": float(merged["signed_tail_probability"].mean()),
            }
        )

    predictions = pd.concat(all_rows, ignore_index=True).sort_values("timestamp")
    predictions.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    monthly = pd.DataFrame(summary_rows)
    monthly["signed_mean_average_precision"] = monthly[["positive_tail_average_precision", "negative_tail_average_precision"]].mean(axis=1)
    monthly["signed_mean_recall_topk"] = monthly[["positive_tail_recall_topk", "negative_tail_recall_topk"]].mean(axis=1)
    monthly.to_csv(run_dir / "signed_tail_monthly_summary.csv", index=False, encoding="utf-8-sig")

    signed_summary = {
        "mean_positive_tail_recall_topk": float(monthly["positive_tail_recall_topk"].mean()),
        "mean_negative_tail_recall_topk": float(monthly["negative_tail_recall_topk"].mean()),
        "mean_positive_tail_average_precision": float(monthly["positive_tail_average_precision"].mean()),
        "mean_negative_tail_average_precision": float(monthly["negative_tail_average_precision"].mean()),
        "mean_signed_recall_topk": float(monthly["signed_mean_recall_topk"].mean()),
        "mean_signed_average_precision": float(monthly["signed_mean_average_precision"].mean()),
        "mean_positive_tail_brier": float(monthly["positive_tail_brier"].mean()),
        "mean_negative_tail_brier": float(monthly["negative_tail_brier"].mean()),
        "config_path": str(Path(args.config).resolve()),
        "baseline_artifact": config.baseline_artifact,
    }
    (run_dir / "signed_tail_summary.json").write_text(json.dumps(signed_summary, ensure_ascii=False, indent=2), encoding="utf-8")
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
