from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from pipelines.base import BaseModelPipeline, PredictionResult
from utils.io import ensure_prediction_frame, ensure_runtime_dirs

from .repro_pipeline import RunConfig, run_monthly_reproduction


# Relative paths computed from project layout — works on any machine
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_XLSX = str(_PROJECT_ROOT / "data" / "shandong_pmos_hourly.xlsx")
DEFAULT_TIMEMIXER_CSV = str(_PROJECT_ROOT.parent / "epf" / "data" / "shandong_pmos_hourly.csv")


class ModelPipeline(BaseModelPipeline):
    model_name = "timemixer"
    device_type = "gpu"

    def train(self, **kwargs):
        raise NotImplementedError("TimeMixer unified train() is not wired yet; use predict_range or legacy pipeline.")

    def predict(self, **kwargs) -> PredictionResult:
        return self.predict_range(**kwargs)

    def predict_range(self, target: str, **kwargs) -> PredictionResult:
        output_root = ensure_runtime_dirs(Path(kwargs.get("output_root", "outputs/unified_runs")) / self.model_name / target)
        predict_date = pd.Timestamp(kwargs.get("predict_date"))
        month = predict_date.strftime("%Y-%m")

        start_date = kwargs.get("start") or predict_date.strftime("%Y-%m-%d")
        end_date = kwargs.get("end") or predict_date.strftime("%Y-%m-%d")
        # TimeMixer 的 run_monthly_reproduction 使用半开区间 [test_start, test_end_exclusive)。
        # 当调用方传入 start == end 时（单日预测），应将 end 视为包含该日，
        # 因此 test_end_exclusive = end + 1 天，否则 test_days 为空。
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        # test_end_exclusive is a half-open bound: always add 1 day to end
        # so the range [start, end_exclusive) includes the full end date
        end_exclusive = (end_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        run_cfg = RunConfig(
            data_path=self._prepare_data_path(kwargs.get("data_path")),
            output_dir=str(output_root),
            month=month,
            test_start=start_date,
            test_end_exclusive=end_exclusive,
            append_leaderboard=False,
            train_months=int(kwargs.get("training_months", 12)),
            val_ratio=float(kwargs.get("val_ratio", 0.2)),
            cutoff_hour_rt=int(kwargs.get("realtime_cutoff_hour", 14)),
            epochs=int(kwargs.get("timemixer_epochs", 80)),
            patience=int(kwargs.get("timemixer_patience", 15)),
            batch_size=int(kwargs.get("timemixer_batch_size", 16)),
            seed=int(kwargs.get("seed", kwargs.get("timemixer_seeds", 42))),
            deterministic=bool(kwargs.get("deterministic", False)),
        )
        result = run_monthly_reproduction(run_cfg)
        raw = pd.read_csv(Path(result["output_dir"]) / "predictions_raw.csv", encoding="utf-8-sig")
        if raw.empty:
            raise ValueError(f"TimeMixer produced empty predictions_raw for {predict_date.date()}")
        # predictions_raw uses 'y_pred' for both DA and RT tasks
        # 'pred_day_ahead_price' is only populated in RT rows (as DA injection reference)
        prediction_col = "y_pred"
        task_filter = "da" if target == "dayahead" else "rt"
        if "task" in raw.columns:
            filtered = raw[raw["task"] == task_filter].copy()
        else:
            filtered = raw.copy()
        if filtered.empty:
            raise ValueError(f"TimeMixer task={task_filter} filter yielded 0 rows for {predict_date.date()}")
        normalized = ensure_prediction_frame(filtered.rename(columns={"ds": "时刻"}), prediction_col)

        # ---- TimeMixer output validation: 24 rows, hour_business 1..24 ----
        _validate_timemixer_output(normalized, predict_date, target)

        output_path = output_root / "predictions.csv"
        normalized.to_csv(output_path, index=False, encoding="utf-8-sig")
        return PredictionResult(model_name=self.model_name, target=target, output_path=output_path, frame=normalized)

    @staticmethod
    def _prepare_data_path(data_path: str | None) -> str:
        if not data_path:
            # Prefer the xlsx in the project data/ folder
            if Path(DEFAULT_DATA_XLSX).exists():
                data_path = DEFAULT_DATA_XLSX
            elif Path(DEFAULT_TIMEMIXER_CSV).exists():
                return DEFAULT_TIMEMIXER_CSV
            else:
                return DEFAULT_DATA_XLSX  # let it error clearly if missing
        path = Path(data_path)
        if path.suffix.lower() != ".xlsx":
            return str(path)
        # Convert xlsx -> csv with explicit engine and encoding
        df = pd.read_excel(path, engine="openpyxl")
        tmp_dir = Path(tempfile.gettempdir()) / "timemixer_unified_cache"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        csv_path = tmp_dir / f"{path.stem}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        return str(csv_path)


def _validate_timemixer_output(df: pd.DataFrame, predict_date: pd.Timestamp, target: str) -> None:
    """Validate TimeMixer output: 24 rows, hour_business 1..24, no D 00:00."""
    issues: list[str] = []

    if len(df) != 24:
        issues.append(f"expected 24 rows, got {len(df)}")

    if "hour_business" in df.columns:
        hours = sorted(df["hour_business"].dropna().astype(int).unique())
        expected_hours = list(range(1, 25))
        if hours != expected_hours:
            missing = set(expected_hours) - set(hours)
            extra = set(hours) - set(expected_hours)
            if missing:
                issues.append(f"missing hour_business: {sorted(missing)}")
            if extra:
                issues.append(f"extra hour_business: {sorted(extra)}")

        # hour 24 must not map to predict_date 00:00
        if "ds" in df.columns:
            h24_rows = df[df["hour_business"] == 24]
            if not h24_rows.empty:
                ds_vals = pd.to_datetime(h24_rows["ds"]).dropna().unique()
                target_dt = pd.Timestamp(predict_date.date())
                for ds in ds_vals:
                    if ds.hour == 0 and ds.date() == target_dt.date():
                        issues.append(
                            f"hour_business=24 ds={ds}: should be D+1 00:00, not D 00:00"
                        )

    if "hour_business" in df.columns and 0 in df["hour_business"].values:
        issues.append("hour_business=0 found; should be 1..24 (with 24=mapping to 00:00 of D+1)")

    if issues:
        raise ValueError(
            f"TimeMixer output validation FAILED for {target} {predict_date.date()}: "
            f"{' | '.join(issues)}"
        )
