from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.protocol_b import load_protocol_b_config, run_protocol_b_experiment
@dataclass
class PromotionValidationConfig:
    experiment_name: str
    base_data_path: str
    incremental_data_path: str
    output_root: str
    target_months: list[str]
    accepted_point_artifact: str
    accepted_interval_artifact: str
    include_tail_flag: bool = True
    frozen_execution_baseline_reference: str | None = None


def _load_config(path: str | Path) -> PromotionValidationConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return PromotionValidationConfig(
        experiment_name=raw["experiment_name"],
        base_data_path=raw["base_data_path"],
        incremental_data_path=raw["incremental_data_path"],
        output_root=raw["output_root"],
        target_months=raw.get("target_months", []),
        accepted_point_artifact=raw["accepted_point_artifact"],
        accepted_interval_artifact=raw["accepted_interval_artifact"],
        include_tail_flag=raw.get("include_tail_flag", True),
        frozen_execution_baseline_reference=raw.get("frozen_execution_baseline_reference"),
    )


def _resolve_artifact(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else PROJECT_ROOT.parent / path


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)


def _target_year(target_months: list[str]) -> int:
    years = {int(month.split("-")[0]) for month in target_months}
    if len(years) != 1:
        raise ValueError(f"Promotion validation expects a single target year, got {sorted(years)}")
    return next(iter(years))


def _build_month_filter(df: pd.DataFrame, target_months: list[str], timestamp_col: str = "timestamp") -> pd.DataFrame:
    out = df.copy()
    out["target_month"] = pd.to_datetime(out[timestamp_col]).dt.strftime("%Y-%m")
    return out[out["target_month"].isin(set(target_months))].copy()


def _stage_predictions_only(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "split" in out.columns:
        out = out[out["split"] == "test"].copy()
    return out.sort_values("timestamp").reset_index(drop=True)


def _run_protocol_from_config(base_config_path: Path, experiment_name: str, data_path: str, target_year: int, temp_dir: Path) -> Path:
    cfg = _load_yaml(base_config_path)
    cfg["experiment_name"] = experiment_name
    cfg["data_path"] = data_path
    cfg["target_year"] = target_year
    cfg["output_root"] = str(temp_dir)
    instantiated = temp_dir / f"{experiment_name}.yaml"
    _write_yaml(instantiated, cfg)
    return run_protocol_b_experiment(instantiated)


def _run_signed_tail_from_reference(reference_config_path: Path, experiment_name: str, data_path: str, target_year: int, baseline_artifact: Path, temp_dir: Path) -> Path:
    cfg = _load_yaml(reference_config_path)
    cfg["experiment_name"] = experiment_name
    cfg["data_path"] = data_path
    cfg["target_year"] = target_year
    cfg["output_root"] = str(temp_dir)
    cfg["baseline_artifact"] = str(baseline_artifact)
    instantiated = temp_dir / f"{experiment_name}.yaml"
    _write_yaml(instantiated, cfg)

    import subprocess

    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "run_signed_tail_calibration.py"), "--config", str(instantiated)],
        cwd=str(PROJECT_ROOT.parent),
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip().splitlines()[-1].strip())


def _run_probability_from_reference(reference_config_path: Path, experiment_name: str, data_path: str, target_year: int, baseline_artifact: Path, temp_dir: Path) -> Path:
    cfg = _load_yaml(reference_config_path)
    cfg["experiment_name"] = experiment_name
    cfg["data_path"] = data_path
    cfg["target_year"] = target_year
    cfg["output_root"] = str(temp_dir)
    cfg["baseline_artifact"] = str(baseline_artifact)
    instantiated = temp_dir / f"{experiment_name}.yaml"
    _write_yaml(instantiated, cfg)

    import subprocess

    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "run_v2_probability.py"), "--config", str(instantiated)],
        cwd=str(PROJECT_ROOT.parent),
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip().splitlines()[-1].strip())


def _build_fusion(point_artifact: Path, interval_artifact: Path, run_dir: Path, include_tail_flag: bool) -> pd.DataFrame:
    point_pred = pd.read_csv(point_artifact / "predictions.csv")
    interval_pred = pd.read_csv(interval_artifact / "predictions.csv")
    point_pred["timestamp"] = pd.to_datetime(point_pred["timestamp"])
    interval_pred["timestamp"] = pd.to_datetime(interval_pred["timestamp"])

    merge_cols = ["timestamp", "delta_q_low", "delta_q_high", "rt_q_low", "rt_q_high", "spike_probability"]
    available_merge_cols = [col for col in merge_cols if col in interval_pred.columns]
    fused = point_pred.merge(interval_pred[available_merge_cols], on="timestamp", how="left")
    if include_tail_flag and "tail_sign" in fused.columns:
        fused["tail_flag"] = (fused["tail_sign"] != "none").astype(int)
    fused.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")
    return fused


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.write_bytes(src.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Promotion-style validation for the current SGDFNet unified candidate on fresh 2026 windows.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = _load_config(args.config)
    output_root = PROJECT_ROOT.parent / config.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / f"{config.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    accepted_point_artifact = _resolve_artifact(config.accepted_point_artifact)
    accepted_interval_artifact = _resolve_artifact(config.accepted_interval_artifact)
    target_year = _target_year(config.target_months)

    registry_path = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    frozen_baseline_config = PROJECT_ROOT.parent / registry["accepted_core_baseline"]["config"]
    followup_config = PROJECT_ROOT / "reports" / "followup_cycle" / "instances" / "followup_002_tf_moving_average_plus_pressure" / "experiment_config.yaml"
    signed_tail_config = Path(registry["accepted_signed_tail_calibration"]["config"])
    interval_config = PROJECT_ROOT.parent / registry["accepted_interval_module"]["config"]

    temp_root = PROJECT_ROOT.parent / "outputs" / "RT916_SpikeMarketLab" / "experiments" / "_pv_cache"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_root = temp_root / datetime.now().strftime("pv_%H%M%S")
    temp_root.mkdir(parents=True, exist_ok=True)

    base_baseline_artifact = _run_protocol_from_config(
        frozen_baseline_config,
        "pv_base",
        config.base_data_path,
        target_year,
        temp_root / "base_baseline",
    )

    tfpressure_baseline_artifact = _run_protocol_from_config(
        followup_config,
        "pv_tfp",
        config.base_data_path,
        target_year,
        temp_root / "tfpressure_baseline",
    )

    signed_tail_artifact = _run_signed_tail_from_reference(
        signed_tail_config,
        "pv_stc",
        config.base_data_path,
        target_year,
        tfpressure_baseline_artifact,
        temp_root / "signed_tail",
    )

    interval_artifact = _run_probability_from_reference(
        interval_config,
        "pv_p1",
        config.base_data_path,
        target_year,
        base_baseline_artifact,
        temp_root / "interval",
    )

    signed_tail_pred = _stage_predictions_only(
        _build_month_filter(pd.read_csv(signed_tail_artifact / "predictions.csv"), config.target_months)
    )
    interval_pred = _stage_predictions_only(
        _build_month_filter(pd.read_csv(interval_artifact / "predictions.csv"), config.target_months)
    )

    signed_tail_month_artifact = run_dir / "signed_tail_month_artifact"
    signed_tail_month_artifact.mkdir(parents=True, exist_ok=True)
    signed_tail_pred.to_csv(signed_tail_month_artifact / "predictions.csv", index=False, encoding="utf-8-sig")
    _copy_if_exists(signed_tail_artifact / "signed_tail_calibration_monthly_summary.csv", signed_tail_month_artifact / "signed_tail_calibration_monthly_summary.csv")
    _copy_if_exists(signed_tail_artifact / "signed_tail_calibration_summary.json", signed_tail_month_artifact / "signed_tail_calibration_summary.json")
    _copy_if_exists(signed_tail_artifact / "feature_manifest.csv", signed_tail_month_artifact / "feature_manifest.csv")

    interval_month_artifact = run_dir / "interval_month_artifact"
    interval_month_artifact.mkdir(parents=True, exist_ok=True)
    interval_pred.to_csv(interval_month_artifact / "predictions.csv", index=False, encoding="utf-8-sig")
    _copy_if_exists(interval_artifact / "probability_monthly_summary.csv", interval_month_artifact / "probability_monthly_summary.csv")
    _copy_if_exists(interval_artifact / "probability_summary.json", interval_month_artifact / "probability_summary.json")
    _copy_if_exists(interval_artifact / "feature_manifest.csv", interval_month_artifact / "feature_manifest.csv")

    fused = _build_fusion(signed_tail_month_artifact, interval_month_artifact, run_dir, config.include_tail_flag)

    probability_summary_path = interval_artifact / "probability_summary.json"
    if probability_summary_path.exists():
        _copy_if_exists(probability_summary_path, run_dir / "probability_summary.json")
    probability_monthly_path = interval_artifact / "probability_monthly_summary.csv"
    if probability_monthly_path.exists():
        _copy_if_exists(probability_monthly_path, run_dir / "probability_monthly_summary.csv")
    signed_tail_monthly_path = signed_tail_artifact / "signed_tail_calibration_monthly_summary.csv"
    if signed_tail_monthly_path.exists():
        _copy_if_exists(signed_tail_monthly_path, run_dir / "signed_tail_calibration_monthly_summary.csv")
    signed_tail_summary_path = signed_tail_artifact / "signed_tail_calibration_summary.json"
    if signed_tail_summary_path.exists():
        _copy_if_exists(signed_tail_summary_path, run_dir / "signed_tail_calibration_summary.json")

    manifest = {
        "config_path": str(Path(args.config).resolve()),
        "run_dir": str(run_dir.resolve()),
        "validated_months": list(config.target_months),
        "accepted_point_artifact": str(accepted_point_artifact),
        "accepted_interval_artifact": str(accepted_interval_artifact),
        "reconstructed_base_baseline_artifact": str(base_baseline_artifact),
        "reconstructed_tfpressure_baseline_artifact": str(tfpressure_baseline_artifact),
        "reconstructed_signed_tail_artifact": str(signed_tail_artifact),
        "reconstructed_interval_artifact": str(interval_artifact),
        "reconstruction_cache_root": str(temp_root),
        "frozen_execution_baseline_reference": config.frozen_execution_baseline_reference,
        "prediction_row_count": int(len(fused)),
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(str(run_dir))


if __name__ == "__main__":
    main()
