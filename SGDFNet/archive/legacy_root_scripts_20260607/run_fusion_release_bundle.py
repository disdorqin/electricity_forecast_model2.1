from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


@dataclass
class FusionConfig:
    experiment_name: str
    output_root: str
    point_artifact: str
    interval_artifact: str
    include_tail_flag: bool = False


def _load_config(path: str | Path) -> FusionConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return FusionConfig(
        experiment_name=raw["experiment_name"],
        output_root=raw["output_root"],
        point_artifact=raw["point_artifact"],
        interval_artifact=raw["interval_artifact"],
        include_tail_flag=raw.get("include_tail_flag", False),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a unified SGDFNet fusion release bundle from accepted point and interval artifacts.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    config = _load_config(args.config)
    output_root = project_root / config.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / f"{config.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    point_artifact = Path(config.point_artifact)
    if not point_artifact.is_absolute():
        point_artifact = project_root / point_artifact
    interval_artifact = Path(config.interval_artifact)
    if not interval_artifact.is_absolute():
        interval_artifact = project_root / interval_artifact

    point_pred = pd.read_csv(point_artifact / "predictions.csv")
    interval_pred = pd.read_csv(interval_artifact / "predictions.csv")

    merge_cols = ["timestamp", "delta_q_low", "delta_q_high", "rt_q_low", "rt_q_high", "spike_probability"]
    available_merge_cols = [col for col in merge_cols if col in interval_pred.columns]
    fused = point_pred.merge(interval_pred[available_merge_cols], on="timestamp", how="left")
    if config.include_tail_flag and "tail_sign" in point_pred.columns:
        fused["tail_flag"] = (fused["tail_sign"] != "none").astype(int)

    fused.to_csv(run_dir / "predictions.csv", index=False, encoding="utf-8-sig")

    interval_summary = interval_artifact / "probability_summary.json"
    if interval_summary.exists():
        shutil.copy2(interval_summary, run_dir / "probability_summary.json")
    interval_monthly = interval_artifact / "probability_monthly_summary.csv"
    if interval_monthly.exists():
        shutil.copy2(interval_monthly, run_dir / "probability_monthly_summary.csv")
    interval_feature_manifest = interval_artifact / "feature_manifest.csv"
    if interval_feature_manifest.exists():
        shutil.copy2(interval_feature_manifest, run_dir / "interval_feature_manifest.csv")
    point_feature_manifest = point_artifact / "feature_manifest.csv"
    if point_feature_manifest.exists():
        shutil.copy2(point_feature_manifest, run_dir / "point_feature_manifest.csv")

    manifest = {
        "config_path": str(Path(args.config).resolve()),
        "run_dir": str(run_dir.resolve()),
        "point_artifact": str(point_artifact),
        "interval_artifact": str(interval_artifact),
        "include_tail_flag": config.include_tail_flag,
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(run_dir))


if __name__ == "__main__":
    main()
