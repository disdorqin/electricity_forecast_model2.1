from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .checkpointing import load_checkpoint, save_checkpoint
from .dataset import filter_time_range, load_and_preprocess_dataset
from .eval_a0 import build_hourly_metrics, evaluate_predictions
from .io_utils import resolve_output_dir, snapshot_run_config, write_json
from .metrics import build_metrics_frame, build_segment_metrics
from .models import DeltaRegressor, SegmentConditionedDeltaRegressor
from .protocol_b import (
    ProtocolBConfig,
    _apply_calibration_map,
    _build_segment_bias_map,
    _build_train_sample_weight,
    _prepare_splits,
    load_protocol_b_config,
    run_protocol_b_experiment,
)
from .runtime_helpers import build_regressor
from .data_contract import build_feature_manifest


def load_config(config_path: str | Path) -> ProtocolBConfig:
    return load_protocol_b_config(config_path)


def _build_train_val_split_for_cutoff(frame: pd.DataFrame, train_end: str | pd.Timestamp, val_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_end_ts = pd.Timestamp(train_end) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    val_start = train_end_ts - pd.Timedelta(days=val_days) + pd.Timedelta(seconds=1)
    train_df = frame[frame["timestamp"] < val_start].copy()
    val_df = frame[(frame["timestamp"] >= val_start) & (frame["timestamp"] <= train_end_ts)].copy()
    return train_df, val_df


def _fit_model_and_calibration(config: ProtocolBConfig, frame: pd.DataFrame, feature_cols: list[str], train_end: str | pd.Timestamp, val_days: int) -> dict[str, Any]:
    train_df, val_df = _build_train_val_split_for_cutoff(frame, train_end, val_days)
    if train_df.empty or val_df.empty:
        raise ValueError("Train/validation split is empty for the requested train_end/val_days.")
    train_weight, train_tail_threshold = _build_train_sample_weight(train_df, config.model_config)
    model = build_regressor(config.model_config)
    model.fit(train_df, feature_cols, sample_weight=None if train_weight is None else train_weight.to_numpy(dtype=float))

    val_scored = val_df.copy()
    val_scored["delta_hat"] = model.predict(val_scored, feature_cols)
    val_scored["rt_hat"] = val_scored["da_anchor"] + val_scored["delta_hat"]

    calibration_map: dict[str, float] = {}
    if config.apply_segment_bias_calibration:
        calibration_map = _build_segment_bias_map(
            val_scored,
            config.calibration_segments,
            config.calibration_reducer,
            config.calibration_residual_quantile,
        )

    val_scored = _apply_calibration_map(val_scored, calibration_map, config.calibration_mode)
    return {
        "model": model,
        "train_df": train_df,
        "val_df": val_df,
        "val_scored": val_scored,
        "train_tail_threshold": train_tail_threshold,
        "calibration_map": calibration_map,
    }


def write_prediction_outputs(pred_df: pd.DataFrame, output_dir: str | Path, metrics_payload: dict[str, Any] | None = None) -> None:
    output_path = Path(output_dir)
    pred_df.to_csv(output_path / "predictions.csv", index=False, encoding="utf-8-sig")
    summary = {
        "row_count": int(len(pred_df)),
        "start": None if pred_df.empty else str(pred_df["timestamp"].min()),
        "end": None if pred_df.empty else str(pred_df["timestamp"].max()),
    }
    if metrics_payload:
        summary["metrics_available"] = metrics_payload.get("metrics_available", False)
    write_json(output_path / "prediction_summary.json", summary)


def train_sgdfnet(config: ProtocolBConfig, data_path: str | Path, train_end: str, val_days: int, output_dir: str | Path) -> dict[str, Any]:
    output_path = resolve_output_dir(output_dir)
    frame, feature_cols = load_and_preprocess_dataset(data_path, config.feature_config)
    feature_manifest = build_feature_manifest(feature_cols)
    feature_manifest.to_csv(output_path / "feature_manifest.csv", index=False, encoding="utf-8-sig")

    fitted = _fit_model_and_calibration(config, frame, feature_cols, train_end, val_days)
    checkpoint_path = save_checkpoint(
        {
            "model": fitted["model"],
            "feature_cols": feature_cols,
            "config": asdict(config),
            "train_end": str(train_end),
            "val_days": int(val_days),
            "calibration_map": fitted["calibration_map"],
            "calibration_mode": config.calibration_mode,
            "train_tail_threshold": fitted["train_tail_threshold"],
        },
        output_path,
    )

    train_log = pd.DataFrame(
        [
            {"split": "train", "rows": len(fitted["train_df"])},
            {"split": "val", "rows": len(fitted["val_df"])},
        ]
    )
    train_log.to_csv(output_path / "train_log.csv", index=False, encoding="utf-8-sig")

    train_summary = {
        "checkpoint_path": str(checkpoint_path),
        "train_rows": int(len(fitted["train_df"])),
        "val_rows": int(len(fitted["val_df"])),
        "val_metrics": build_metrics_frame(fitted["val_scored"]),
        "feature_count": len(feature_cols),
    }
    write_json(output_path / "train_summary.json", train_summary)
    return train_summary


def predict_sgdfnet(
    config: ProtocolBConfig,
    data_path: str | Path,
    checkpoint_path: str | Path,
    predict_start: str,
    predict_end: str,
    output_dir: str | Path,
) -> dict[str, Any]:
    output_path = resolve_output_dir(output_dir)
    frame, _ = load_and_preprocess_dataset(data_path, config.feature_config)
    checkpoint = load_checkpoint(checkpoint_path)
    feature_cols = checkpoint["feature_cols"]

    pred_df = filter_time_range(frame, predict_start, predict_end)
    if pred_df.empty:
        raise ValueError("Prediction time range has no rows in dataset.")

    model = checkpoint["model"]
    pred_df = pred_df.copy()
    pred_df["delta_hat"] = model.predict(pred_df, feature_cols)
    pred_df["rt_hat"] = pred_df["da_anchor"] + pred_df["delta_hat"]
    pred_df = _apply_calibration_map(pred_df, checkpoint.get("calibration_map", {}), checkpoint.get("calibration_mode", "segment_bias"))

    write_prediction_outputs(
        pred_df[
            [
                "timestamp",
                "segment",
                "segment_id",
                "da_anchor",
                "rt_actual",
                "delta_target",
                "delta_hat",
                "rt_hat",
                "direction_label",
                "hour",
                "month",
            ]
        ].copy(),
        output_path,
    )

    metrics_payload = evaluate_predictions(output_path / "predictions.csv", output_path)
    if metrics_payload.get("metrics_available"):
        write_json(output_path / "metrics.json", metrics_payload["metrics"])
        hourly_metrics = build_hourly_metrics(pred_df)
        hourly_metrics.to_csv(output_path / "hourly_metrics.csv", index=False, encoding="utf-8-sig")

    run_audit = {
        "mode": "predict",
        "checkpoint_path": str(Path(checkpoint_path)),
        "predict_start": str(pd.Timestamp(predict_start)),
        "predict_end": str(pd.Timestamp(predict_end)),
        "feature_count": len(feature_cols),
        "metrics_used_actuals": bool(metrics_payload.get("metrics_available", False)),
        "calibration_loaded_from_checkpoint": bool(checkpoint.get("calibration_map")),
    }
    write_json(output_path / "run_audit.json", run_audit)
    return run_audit


def train_and_predict_sgdfnet(
    config: ProtocolBConfig,
    data_path: str | Path,
    train_end: str,
    val_days: int,
    predict_start: str,
    predict_end: str,
    output_dir: str | Path,
) -> dict[str, Any]:
    output_path = resolve_output_dir(output_dir)
    train_dir = output_path / "train"
    predict_dir = output_path / "predict"
    train_summary = train_sgdfnet(config, data_path, train_end, val_days, train_dir)
    predict_summary = predict_sgdfnet(
        config,
        data_path,
        train_dir / "checkpoint.joblib",
        predict_start,
        predict_end,
        predict_dir,
    )
    summary = {"train": train_summary, "predict": predict_summary}
    write_json(output_path / "run_audit.json", summary)
    return summary


def run_rolling_2025(config: ProtocolBConfig, data_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    output_path = resolve_output_dir(output_dir)
    original_output_root = config.output_root
    config.output_root = str(output_path)
    config.data_path = str(data_path)
    temp_config_path = output_path / "rolling_runtime_config.yaml"
    temp_config_path.write_text(yaml.safe_dump(asdict(config), allow_unicode=True, sort_keys=False), encoding="utf-8")
    try:
        run_dir = run_protocol_b_experiment(temp_config_path)
    finally:
        config.output_root = original_output_root

    generated_predictions = pd.read_csv(run_dir / "predictions.csv")
    test_predictions = generated_predictions[generated_predictions["split"] == "test"].copy()
    monthly_overall = (
        pd.read_csv(run_dir / "monthly_summary.csv")
        .query("split == 'test'")
        [["month", "rt_smape", "rt_capped_smape"]]
        .rename(columns={"month": "target_month"})
    )
    monthly_overall.to_csv(output_path / "monthly_overall_smape_2025.csv", index=False, encoding="utf-8-sig")

    monthly_segment = []
    for (month, segment), group in test_predictions.groupby(["target_month", "segment"]):
        metrics = build_metrics_frame(group)
        monthly_segment.append(
            {
                "target_month": month,
                "segment": segment,
                "rt_smape": metrics["rt_smape"],
                "rt_capped_smape": metrics["rt_capped_smape"],
            }
        )
    pd.DataFrame(monthly_segment).to_csv(output_path / "monthly_segment_smape_2025.csv", index=False, encoding="utf-8-sig")

    build_hourly_metrics(test_predictions).to_csv(output_path / "hourly_smape_2025.csv", index=False, encoding="utf-8-sig")
    test_predictions.to_csv(output_path / "predictions_2025.csv", index=False, encoding="utf-8-sig")
    write_json(output_path / "rolling_summary.json", build_metrics_frame(test_predictions))
    write_json(
        output_path / "target_check_2025.json",
        {
            "official_metric": "rt_capped_smape_floor_50",
            "full_year_metrics": build_metrics_frame(test_predictions),
        },
    )
    write_json(
        output_path / "run_audit.json",
        {
            "mode": "rolling_2025",
            "source_run_dir": str(run_dir),
            "data_path": str(data_path),
        },
    )
    return {"run_dir": str(run_dir)}
