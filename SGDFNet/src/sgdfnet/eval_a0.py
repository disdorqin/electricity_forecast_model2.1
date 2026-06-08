from __future__ import annotations

from pathlib import Path

import pandas as pd

from .metrics import build_metrics_frame, build_segment_metrics


def build_hourly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for hour, hour_df in df.groupby("hour"):
        row = {"hour": int(hour), "count": len(hour_df)}
        row.update(build_metrics_frame(hour_df))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("hour").reset_index(drop=True)


def evaluate_predictions(predictions_path: str | Path, output_dir: str | Path) -> dict[str, object]:
    df = pd.read_csv(predictions_path)
    if "rt_actual" not in df.columns or df["rt_actual"].isna().all():
        return {"metrics_available": False}
    metrics = build_metrics_frame(df)
    segment_metrics = build_segment_metrics(df)
    hourly_metrics = build_hourly_metrics(df)
    segment_metrics.to_csv(Path(output_dir) / "segment_metrics.csv", index=False, encoding="utf-8-sig")
    hourly_metrics.to_csv(Path(output_dir) / "hourly_metrics.csv", index=False, encoding="utf-8-sig")
    return {
        "metrics_available": True,
        "metrics": metrics,
        "segment_metrics_path": str(Path(output_dir) / "segment_metrics.csv"),
        "hourly_metrics_path": str(Path(output_dir) / "hourly_metrics.csv"),
    }
