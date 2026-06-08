from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from .data_contract import FeatureConfig, build_feature_manifest, load_dataset, preprocess_dataframe
from .metrics import build_metrics_frame, build_segment_metrics, build_tail_metrics
from .models import DeltaRegressor, HGBModelConfig, SegmentConditionedDeltaRegressor
from .runtime_helpers import build_regressor


@dataclass
class ProtocolBConfig:
    experiment_name: str
    data_path: str
    output_root: str
    target_year: int = 2025
    val_days: int = 30
    train_min_rows: int = 24 * 90
    apply_segment_bias_calibration: bool = False
    calibration_segments: list[str] = field(default_factory=list)
    calibration_mode: str = "segment_bias"
    calibration_threshold_quantile: float | None = None
    calibration_recent_days: int | None = None
    calibration_reducer: str = "median"
    calibration_residual_quantile: float | None = None
    calibration_hour_scope: str = "all"
    calibration_month_bucket_mode: str = "season"
    calibration_error_quantile: float = 0.8
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    model_config: HGBModelConfig = field(default_factory=HGBModelConfig)


def load_protocol_b_config(path: str | Path) -> ProtocolBConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ProtocolBConfig(
        experiment_name=raw["experiment_name"],
        data_path=raw["data_path"],
        output_root=raw["output_root"],
        target_year=raw.get("target_year", 2025),
        val_days=raw.get("val_days", 30),
        train_min_rows=raw.get("train_min_rows", 24 * 90),
        apply_segment_bias_calibration=raw.get("apply_segment_bias_calibration", False),
        calibration_segments=raw.get("calibration_segments", []),
        calibration_mode=raw.get("calibration_mode", "segment_bias"),
        calibration_threshold_quantile=raw.get("calibration_threshold_quantile"),
        calibration_recent_days=raw.get("calibration_recent_days"),
        calibration_reducer=raw.get("calibration_reducer", "median"),
        calibration_residual_quantile=raw.get("calibration_residual_quantile"),
        calibration_hour_scope=raw.get("calibration_hour_scope", "all"),
        calibration_month_bucket_mode=raw.get("calibration_month_bucket_mode", "season"),
        calibration_error_quantile=raw.get("calibration_error_quantile", 0.8),
        feature_config=FeatureConfig(**raw.get("feature_config", {})),
        model_config=HGBModelConfig(**raw.get("model_config", {})),
    )


def _month_starts(year: int) -> list[pd.Timestamp]:
    return [pd.Timestamp(year=year, month=month, day=1) for month in range(1, 13)]


def _prepare_splits(frame: pd.DataFrame, month_start: pd.Timestamp, val_days: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    next_month = month_start + pd.offsets.MonthBegin(1)
    val_start = month_start - pd.Timedelta(days=val_days)
    train_df = frame[frame["timestamp"] < val_start].copy()
    val_df = frame[(frame["timestamp"] >= val_start) & (frame["timestamp"] < month_start)].copy()
    test_df = frame[(frame["timestamp"] >= month_start) & (frame["timestamp"] < next_month)].copy()
    return train_df, val_df, test_df


def _score_split(split_name: str, month_label: str, split_df: pd.DataFrame) -> dict[str, float | str | int]:
    row: dict[str, float | str | int] = {"split": split_name, "month": month_label, "count": len(split_df)}
    row.update(build_metrics_frame(split_df))
    return row


def _build_train_sample_weight(train_df: pd.DataFrame, model_config: HGBModelConfig) -> tuple[pd.Series | None, float | None]:
    weight = pd.Series(1.0, index=train_df.index, dtype=float)
    threshold = None
    changed = False
    if model_config.tail_sample_weight > 1.0:
        threshold = float(train_df["delta_target"].abs().quantile(model_config.tail_quantile))
        weight.loc[train_df["delta_target"].abs() >= threshold] *= float(model_config.tail_sample_weight)
        changed = True

    primary_hours = set(model_config.risk_hour_primary_hours or [])
    secondary_hours = set(model_config.risk_hour_secondary_hours or [])
    primary_segments = set(model_config.risk_hour_segments or [])
    if model_config.risk_hour_primary_weight > 1.0 and primary_hours:
        mask = train_df["hour"].isin(primary_hours)
        if primary_segments:
            mask = mask & train_df["segment"].isin(primary_segments)
        weight.loc[mask] *= float(model_config.risk_hour_primary_weight)
        changed = True
    if model_config.risk_hour_secondary_weight > 1.0 and secondary_hours:
        mask = train_df["hour"].isin(secondary_hours)
        if primary_segments:
            mask = mask & train_df["segment"].isin(primary_segments)
        weight.loc[mask] *= float(model_config.risk_hour_secondary_weight)
        changed = True
    return (weight if changed else None), threshold


def _reduce_residual(series: pd.Series, reducer: str, residual_quantile: float | None = None) -> float:
    if reducer == "quantile":
        q = 0.5 if residual_quantile is None else float(residual_quantile)
        return float(series.quantile(q))
    if reducer == "mean":
        return float(series.mean())
    return float(series.median())


def _build_segment_bias_map(
    val_scored: pd.DataFrame,
    calibration_segments: list[str],
    reducer: str,
    residual_quantile: float | None = None,
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    if not calibration_segments:
        calibration_segments = sorted(val_scored["segment"].dropna().unique().tolist())
    bias_map: dict[str, float] = {}
    residual = val_scored["delta_target"] - val_scored["delta_hat"]
    tmp = val_scored.assign(_residual=residual)
    for segment in calibration_segments:
        seg_df = tmp[tmp["segment"] == segment]
        if not seg_df.empty:
            bias_map[str(segment)] = _reduce_residual(seg_df["_residual"], reducer, residual_quantile)
    return bias_map


def _season_bucket(month_series: pd.Series) -> pd.Series:
    mapping = {
        12: "winter",
        1: "winter",
        2: "winter",
        3: "spring",
        4: "spring",
        5: "spring",
        6: "summer",
        7: "summer",
        8: "summer",
        9: "autumn",
        10: "autumn",
        11: "autumn",
    }
    return month_series.map(mapping)


def _build_hour_bias_map(
    val_scored: pd.DataFrame,
    reducer: str,
    residual_quantile: float | None = None,
    scope: str = "all",
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    tmp = val_scored.copy()
    tmp["_residual"] = tmp["delta_target"] - tmp["delta_hat"]
    if scope == "risk_915":
        tmp = tmp[tmp["hour"].isin([9, 10, 15])]
    elif scope == "risk_extended":
        tmp = tmp[tmp["hour"].isin([9, 10, 11, 14, 15])]
    bias_map: dict[str, float] = {}
    for hour, hour_df in tmp.groupby("hour"):
        if not hour_df.empty:
            bias_map[f"hour={int(hour)}"] = _reduce_residual(hour_df["_residual"], reducer, residual_quantile)
    return bias_map


def _build_segment_hour_bias_map(
    val_scored: pd.DataFrame,
    calibration_segments: list[str],
    reducer: str,
    residual_quantile: float | None = None,
    scope: str = "all",
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    tmp = val_scored.copy()
    tmp["_residual"] = tmp["delta_target"] - tmp["delta_hat"]
    if calibration_segments:
        tmp = tmp[tmp["segment"].isin(calibration_segments)]
    if scope == "risk_915":
        tmp = tmp[tmp["hour"].isin([9, 10, 15])]
    elif scope == "risk_extended":
        tmp = tmp[tmp["hour"].isin([9, 10, 11, 14, 15])]
    bias_map: dict[str, float] = {}
    for (segment, hour), g in tmp.groupby(["segment", "hour"]):
        if not g.empty:
            bias_map[f"{segment}|hour={int(hour)}"] = _reduce_residual(g["_residual"], reducer, residual_quantile)
    return bias_map


def _build_month_bucket_hour_bias_map(
    val_scored: pd.DataFrame,
    reducer: str,
    residual_quantile: float | None = None,
    month_bucket_mode: str = "season",
    scope: str = "all",
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    tmp = val_scored.copy()
    tmp["_residual"] = tmp["delta_target"] - tmp["delta_hat"]
    tmp["_month_bucket"] = _season_bucket(tmp["timestamp"].dt.month) if month_bucket_mode == "season" else tmp["timestamp"].dt.month.astype(str)
    if scope == "risk_915":
        tmp = tmp[tmp["hour"].isin([9, 10, 15])]
    elif scope == "risk_extended":
        tmp = tmp[tmp["hour"].isin([9, 10, 11, 14, 15])]
    bias_map: dict[str, float] = {}
    for (bucket, hour), g in tmp.groupby(["_month_bucket", "hour"]):
        if not g.empty:
            bias_map[f"{bucket}|hour={int(hour)}"] = _reduce_residual(g["_residual"], reducer, residual_quantile)
    return bias_map


def _build_segment_hour_sign_bias_map(
    val_scored: pd.DataFrame,
    calibration_segments: list[str],
    reducer: str,
    residual_quantile: float | None = None,
    scope: str = "all",
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    tmp = val_scored.copy()
    tmp["_residual"] = tmp["delta_target"] - tmp["delta_hat"]
    tmp["_pred_sign"] = (tmp["delta_hat"] > 0).astype(int)
    if calibration_segments:
        tmp = tmp[tmp["segment"].isin(calibration_segments)]
    if scope == "risk_915":
        tmp = tmp[tmp["hour"].isin([9, 10, 15])]
    elif scope == "risk_extended":
        tmp = tmp[tmp["hour"].isin([9, 10, 11, 14, 15])]
    bias_map: dict[str, float] = {}
    for (segment, hour, pred_sign), g in tmp.groupby(["segment", "hour", "_pred_sign"]):
        if not g.empty:
            bias_map[f"{segment}|hour={int(hour)}|pred_sign={int(pred_sign)}"] = _reduce_residual(
                g["_residual"], reducer, residual_quantile
            )
    return bias_map


def _build_error_gate_bias_map(
    val_scored: pd.DataFrame,
    reducer: str,
    residual_quantile: float | None = None,
    error_quantile: float = 0.8,
    mode: str = "error_gate_bias",
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    tmp = val_scored.copy()
    tmp["_residual"] = tmp["delta_target"] - tmp["delta_hat"]
    tmp["_abs_residual"] = tmp["_residual"].abs()
    threshold = float(tmp["_abs_residual"].quantile(error_quantile))
    bias_map: dict[str, float] = {"threshold": threshold}
    hard_df = tmp[tmp["_abs_residual"] >= threshold]
    if hard_df.empty:
        bias_map["hard_bias"] = 0.0
        return bias_map
    if mode == "combo_error_sign_gate_bias":
        hard_df = hard_df.assign(_pred_sign=(hard_df["delta_hat"] > 0).astype(int))
        for pred_sign, g in hard_df.groupby("_pred_sign"):
            bias_map[f"hard_bias|pred_sign={int(pred_sign)}"] = _reduce_residual(g["_residual"], reducer, residual_quantile)
    elif mode == "segment_error_gate_bias":
        for segment, g in hard_df.groupby("segment"):
            bias_map[f"hard_bias|segment={segment}"] = _reduce_residual(g["_residual"], reducer, residual_quantile)
    else:
        bias_map["hard_bias"] = _reduce_residual(hard_df["_residual"], reducer, residual_quantile)
    return bias_map


def _build_segment_sign_bias_map(
    val_scored: pd.DataFrame,
    calibration_segments: list[str],
    reducer: str,
    residual_quantile: float | None = None,
) -> dict[str, float]:
    if val_scored.empty:
        return {}
    if not calibration_segments:
        calibration_segments = sorted(val_scored["segment"].dropna().unique().tolist())
    bias_map: dict[str, float] = {}
    residual = val_scored["delta_target"] - val_scored["delta_hat"]
    tmp = val_scored.assign(_residual=residual, _pred_sign=(val_scored["delta_hat"] > 0).astype(int))
    for segment in calibration_segments:
        seg_df = tmp[tmp["segment"] == segment]
        if seg_df.empty:
            continue
        for pred_sign, sign_df in seg_df.groupby("_pred_sign"):
            if not sign_df.empty:
                bias_map[f"{segment}|pred_sign={int(pred_sign)}"] = _reduce_residual(
                    sign_df["_residual"],
                    reducer,
                    residual_quantile,
                )
    return bias_map


def _build_segment_threshold_bias_map(
    val_scored: pd.DataFrame,
    calibration_segments: list[str],
    threshold_quantile: float | None,
    reducer: str,
    residual_quantile: float | None = None,
) -> dict[str, float]:
    if val_scored.empty or threshold_quantile is None:
        return {}
    if not calibration_segments:
        calibration_segments = sorted(val_scored["segment"].dropna().unique().tolist())
    bias_map: dict[str, float] = {}
    residual = val_scored["delta_target"] - val_scored["delta_hat"]
    tmp = val_scored.assign(_residual=residual, _abs_pred=val_scored["delta_hat"].abs())
    for segment in calibration_segments:
        seg_df = tmp[tmp["segment"] == segment]
        if seg_df.empty:
            continue
        threshold = float(seg_df["_abs_pred"].quantile(threshold_quantile))
        strong_df = seg_df[seg_df["_abs_pred"] >= threshold]
        if strong_df.empty:
            continue
        bias_map[f"{segment}|threshold"] = _reduce_residual(strong_df["_residual"], reducer, residual_quantile)
        bias_map[f"{segment}|threshold_value"] = threshold
    return bias_map


def _restrict_calibration_window(val_scored: pd.DataFrame, recent_days: int | None) -> pd.DataFrame:
    if val_scored.empty or recent_days is None or recent_days <= 0:
        return val_scored
    cutoff = val_scored["timestamp"].max() - pd.Timedelta(days=recent_days)
    restricted = val_scored[val_scored["timestamp"] >= cutoff].copy()
    return restricted if not restricted.empty else val_scored


def _apply_calibration_map(scored: pd.DataFrame, calibration_map: dict[str, float], calibration_mode: str) -> pd.DataFrame:
    if not calibration_map:
        return scored
    adjusted = scored.copy()
    if calibration_mode == "segment_sign_bias":
        key = adjusted["segment"].astype(str) + "|pred_sign=" + (adjusted["delta_hat"] > 0).astype(int).astype(str)
        bias = key.map(calibration_map).fillna(0.0)
    elif calibration_mode == "segment_threshold_bias":
        bias = pd.Series(0.0, index=adjusted.index, dtype=float)
        for segment in adjusted["segment"].dropna().unique():
            bias_value = calibration_map.get(f"{segment}|threshold")
            threshold_value = calibration_map.get(f"{segment}|threshold_value")
            if bias_value is None or threshold_value is None:
                continue
            mask = (adjusted["segment"] == segment) & (adjusted["delta_hat"].abs() >= float(threshold_value))
            bias.loc[mask] = float(bias_value)
    elif calibration_mode == "hour_bias":
        key = "hour=" + adjusted["hour"].astype(int).astype(str)
        bias = key.map(calibration_map).fillna(0.0)
    elif calibration_mode == "segment_hour_bias":
        key = adjusted["segment"].astype(str) + "|hour=" + adjusted["hour"].astype(int).astype(str)
        bias = key.map(calibration_map).fillna(0.0)
    elif calibration_mode == "month_hour_bias":
        month_bucket = _season_bucket(adjusted["timestamp"].dt.month)
        key = month_bucket.astype(str) + "|hour=" + adjusted["hour"].astype(int).astype(str)
        bias = key.map(calibration_map).fillna(0.0)
    elif calibration_mode == "segment_hour_sign_bias":
        key = (
            adjusted["segment"].astype(str)
            + "|hour="
            + adjusted["hour"].astype(int).astype(str)
            + "|pred_sign="
            + (adjusted["delta_hat"] > 0).astype(int).astype(str)
        )
        bias = key.map(calibration_map).fillna(0.0)
    elif calibration_mode == "error_gate_bias":
        threshold = float(calibration_map.get("threshold", float("inf")))
        hard_bias = float(calibration_map.get("hard_bias", 0.0))
        bias = pd.Series(0.0, index=adjusted.index, dtype=float)
        bias.loc[adjusted["delta_hat"].abs() >= threshold] = hard_bias
    elif calibration_mode == "combo_error_sign_gate_bias":
        threshold = float(calibration_map.get("threshold", float("inf")))
        key = "hard_bias|pred_sign=" + (adjusted["delta_hat"] > 0).astype(int).astype(str)
        hard_bias = key.map(calibration_map).fillna(0.0)
        bias = pd.Series(0.0, index=adjusted.index, dtype=float)
        mask = adjusted["delta_hat"].abs() >= threshold
        bias.loc[mask] = hard_bias.loc[mask]
    elif calibration_mode == "segment_error_gate_bias":
        threshold = float(calibration_map.get("threshold", float("inf")))
        key = "hard_bias|segment=" + adjusted["segment"].astype(str)
        hard_bias = key.map(calibration_map).fillna(0.0)
        bias = pd.Series(0.0, index=adjusted.index, dtype=float)
        mask = adjusted["delta_hat"].abs() >= threshold
        bias.loc[mask] = hard_bias.loc[mask]
    else:
        bias = adjusted["segment"].map(calibration_map).fillna(0.0)
    adjusted["delta_hat"] = adjusted["delta_hat"] + bias
    adjusted["rt_hat"] = adjusted["da_anchor"] + adjusted["delta_hat"]
    return adjusted


def run_protocol_b_experiment(config_path: str | Path) -> Path:
    config = load_protocol_b_config(config_path)
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = f"{config.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_df = load_dataset(config.data_path)
    frame, feature_cols = preprocess_dataframe(raw_df, config.feature_config)
    feature_manifest = build_feature_manifest(feature_cols)
    feature_manifest.to_csv(run_dir / "feature_manifest.csv", index=False, encoding="utf-8-sig")

    monthly_predictions: list[pd.DataFrame] = []
    monthly_summary_rows: list[dict[str, float | str | int]] = []
    split_audits: list[dict[str, object]] = []

    for month_start in _month_starts(config.target_year):
        month_label = month_start.strftime("%Y-%m")
        train_df, val_df, test_df = _prepare_splits(frame, month_start, config.val_days)
        split_audit = {
            "month": month_label,
            "train_start": None if train_df.empty else str(train_df["timestamp"].min()),
            "train_end": None if train_df.empty else str(train_df["timestamp"].max()),
            "val_start": None if val_df.empty else str(val_df["timestamp"].min()),
            "val_end": None if val_df.empty else str(val_df["timestamp"].max()),
            "test_start": None if test_df.empty else str(test_df["timestamp"].min()),
            "test_end": None if test_df.empty else str(test_df["timestamp"].max()),
            "train_rows": int(len(train_df)),
            "val_rows": int(len(val_df)),
            "test_rows": int(len(test_df)),
        }
        split_audits.append(split_audit)
        if len(train_df) < config.train_min_rows or val_df.empty or test_df.empty:
            continue

        train_weight, train_tail_threshold = _build_train_sample_weight(train_df, config.model_config)

        model = build_regressor(config.model_config)
        model.fit(
            train_df,
            feature_cols,
            sample_weight=None if train_weight is None else train_weight.to_numpy(dtype=float),
        )

        val_scored_for_calibration = val_df.copy()
        val_scored_for_calibration["delta_hat"] = model.predict(val_scored_for_calibration, feature_cols)
        val_scored_for_calibration["rt_hat"] = val_scored_for_calibration["da_anchor"] + val_scored_for_calibration["delta_hat"]
        calibration_source = _restrict_calibration_window(val_scored_for_calibration, config.calibration_recent_days)

        if config.apply_segment_bias_calibration:
            if config.calibration_mode == "segment_sign_bias":
                calibration_map = _build_segment_sign_bias_map(
                    calibration_source,
                    config.calibration_segments,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                )
            elif config.calibration_mode == "segment_threshold_bias":
                calibration_map = _build_segment_threshold_bias_map(
                    calibration_source,
                    config.calibration_segments,
                    config.calibration_threshold_quantile,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                )
            elif config.calibration_mode == "hour_bias":
                calibration_map = _build_hour_bias_map(
                    calibration_source,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                    config.calibration_hour_scope,
                )
            elif config.calibration_mode == "segment_hour_bias":
                calibration_map = _build_segment_hour_bias_map(
                    calibration_source,
                    config.calibration_segments,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                    config.calibration_hour_scope,
                )
            elif config.calibration_mode == "month_hour_bias":
                calibration_map = _build_month_bucket_hour_bias_map(
                    calibration_source,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                    config.calibration_month_bucket_mode,
                    config.calibration_hour_scope,
                )
            elif config.calibration_mode == "segment_hour_sign_bias":
                calibration_map = _build_segment_hour_sign_bias_map(
                    calibration_source,
                    config.calibration_segments,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                    config.calibration_hour_scope,
                )
            elif config.calibration_mode in {"error_gate_bias", "combo_error_sign_gate_bias", "segment_error_gate_bias"}:
                calibration_map = _build_error_gate_bias_map(
                    calibration_source,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                    config.calibration_error_quantile,
                    config.calibration_mode,
                )
            else:
                calibration_map = _build_segment_bias_map(
                    calibration_source,
                    config.calibration_segments,
                    config.calibration_reducer,
                    config.calibration_residual_quantile,
                )
        else:
            calibration_map = {}

        for split_name, split_df in [("val", val_df), ("test", test_df)]:
            scored = split_df.copy()
            if split_name == "val":
                scored = val_scored_for_calibration.copy()
            else:
                scored["delta_hat"] = model.predict(scored, feature_cols)
                scored["rt_hat"] = scored["da_anchor"] + scored["delta_hat"]
            scored = _apply_calibration_map(scored, calibration_map, config.calibration_mode)
            scored["split"] = split_name
            scored["target_month"] = month_label
            scored["train_tail_threshold"] = train_tail_threshold
            scored["segment_bias_map"] = json.dumps(calibration_map, ensure_ascii=False)
            monthly_predictions.append(
                scored[
                    [
                        "timestamp",
                        "target_month",
                        "split",
                        "segment",
                        "segment_id",
                        "da_anchor",
                        "rt_actual",
                        "delta_target",
                        "delta_hat",
                        "rt_hat",
                        "direction_label",
                        "train_tail_threshold",
                        "segment_bias_map",
                    ]
                ].copy()
            )
            row = _score_split(split_name, month_label, scored)
            row["tail_sample_weight"] = config.model_config.tail_sample_weight
            row["tail_quantile"] = config.model_config.tail_quantile
            row["train_tail_threshold"] = train_tail_threshold
            row["segment_bias_map"] = json.dumps(calibration_map, ensure_ascii=False)
            monthly_summary_rows.append(row)

    if not monthly_predictions:
        raise RuntimeError("No valid monthly predictions were generated under Protocol B.")

    predictions = pd.concat(monthly_predictions, ignore_index=True).sort_values(["timestamp", "split"])
    predictions.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")

    monthly_summary = pd.DataFrame(monthly_summary_rows)
    monthly_summary.to_csv(run_dir / "monthly_summary.csv", index=False, encoding="utf-8-sig")

    with open(run_dir / "monthly_split_audits.json", "w", encoding="utf-8") as f:
        json.dump(split_audits, f, ensure_ascii=False, indent=2)

    test_predictions = predictions[predictions["split"] == "test"].copy()
    full_year_summary = build_metrics_frame(test_predictions)
    full_year_summary["experiment_name"] = config.experiment_name
    full_year_summary["target_year"] = config.target_year
    full_year_summary["test_row_count"] = int(len(test_predictions))
    tail_metrics = build_tail_metrics(test_predictions)
    segment_metrics = build_segment_metrics(test_predictions)
    for _, row in segment_metrics.iterrows():
        segment = row["segment"]
        full_year_summary[f"segment_{segment}_rt_smape"] = float(row["rt_smape"])
        full_year_summary[f"segment_{segment}_rt_capped_smape"] = float(row["rt_capped_smape"])
    for _, row in tail_metrics.iterrows():
        key = int(round((1.0 - float(row["tail_quantile"])) * 100))
        full_year_summary[f"top{key}_tail_delta_mae"] = float(row["tail_delta_mae"])
        full_year_summary[f"top{key}_tail_rt_smape"] = float(row["tail_rt_smape"])
        full_year_summary[f"top{key}_tail_direction_accuracy"] = float(row["tail_direction_accuracy"])

    with open(run_dir / "full_year_summary.json", "w", encoding="utf-8") as f:
        json.dump(full_year_summary, f, ensure_ascii=False, indent=2)

    segment_metrics.to_csv(run_dir / "full_year_segment_metrics.csv", index=False, encoding="utf-8-sig")
    tail_metrics.to_csv(run_dir / "full_year_tail_metrics.csv", index=False, encoding="utf-8-sig")

    with open(run_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "config_path": str(Path(config_path).resolve()),
                "run_dir": str(run_dir.resolve()),
                "feature_columns": feature_cols,
                "config": {
                    "experiment_name": config.experiment_name,
                    "data_path": config.data_path,
                    "output_root": config.output_root,
                    "target_year": config.target_year,
                    "val_days": config.val_days,
                    "train_min_rows": config.train_min_rows,
                    "apply_segment_bias_calibration": config.apply_segment_bias_calibration,
                    "calibration_segments": config.calibration_segments,
                    "calibration_mode": config.calibration_mode,
                    "calibration_threshold_quantile": config.calibration_threshold_quantile,
                    "calibration_recent_days": config.calibration_recent_days,
                    "calibration_reducer": config.calibration_reducer,
                    "calibration_residual_quantile": config.calibration_residual_quantile,
                    "calibration_hour_scope": config.calibration_hour_scope,
                    "calibration_month_bucket_mode": config.calibration_month_bucket_mode,
                    "calibration_error_quantile": config.calibration_error_quantile,
                    "feature_config": asdict(config.feature_config),
                    "model_config": asdict(config.model_config),
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return run_dir
