"""
EPF v1.0 LightGBM Adapter

Wraps the best-performing LightGBM implementation from the EPF v1.0
repository. The adapter adds `data_cutoff` enforcement and standardizes
output to the ledger-compatible format.

Usage:
    from runners.adapters.lightgbm_v1 import LightGBMV1Adapter
    adapter = LightGBMV1Adapter(epf_root="D:/.../epf")
    df = adapter.predict(target_date="2026-02-24", target="dayahead")
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from utils.business_day import standardize_business_columns

logger = logging.getLogger(__name__)


class LightGBMV1Adapter:
    """Adapter for EPF v1.0 LightGBM predictions."""

    def __init__(self, epf_root: str):
        self.epf_root = Path(epf_root)
        if not self.epf_root.exists():
            raise FileNotFoundError(
                f"EPF v1 root not found: {self.epf_root}. "
                f"Please provide --epf-v1-root."
            )
        self._ensure_epf_on_path()

    def _ensure_epf_on_path(self):
        """Add EPF v1.0 root to sys.path for imports."""
        epf_str = str(self.epf_root.resolve())
        if epf_str not in sys.path:
            sys.path.insert(0, epf_str)

    def predict(
        self,
        target_date: str,
        target: str = "dayahead",
        data_path: Optional[str] = None,
        cutoff_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Run LightGBM prediction for a single target day.

        Parameters
        ----------
        target_date : str
            Target business day (YYYY-MM-DD).
        target : str
            "dayahead" → 日前电价; "realtime" → 实时电价.
        data_path : str, optional
            Path to the data file (xlsx or csv).
        cutoff_date : str, optional
            Latest date allowed in training data (YYYY-MM-DD).
            Default: target_date - 1 day.

        Returns
        -------
        pd.DataFrame with standardized prediction columns.
        """
        # Map target to EPF v1.0 convention
        target_map = {"dayahead": "日前电价", "realtime": "实时电价"}
        epf_target = target_map.get(target, target)

        # Resolve data path
        if data_path is None:
            data_path = self._find_data_file()

        # Resolve cutoff
        if cutoff_date is None:
            cutoff_date = (pd.Timestamp(target_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        logger.info(
            f"LightGBM v1: predicting {target_date} ({target}), "
            f"cutoff={cutoff_date}"
        )

        try:
            # Try direct function call first
            from lightGBM.lightGBM_oneday import predict_single_day_price

            df = predict_single_day_price(
                data_path=data_path,
                target_date=target_date,
                target=epf_target,
            )
        except (ImportError, AttributeError):
            # Fallback: use main_fix pipeline
            logger.info("Falling back to lightGBM.main_fix.run_lgbm_pipeline")
            from lightGBM.main_fix import run_lgbm_pipeline

            df = run_lgbm_pipeline(
                data_path=data_path,
                forecast_start=target_date,
                forecast_end=target_date,
                target=epf_target,
                use_predicted_temp=False,
            )

        # Standardize output
        task_label = "dayahead" if target == "dayahead" else "realtime"
        df = standardize_business_columns(
            df,
            ds_col="ds",
            y_pred_col=None,  # auto-detect
            task_label=task_label,
            model_name="lightgbm",
            forecast_date=target_date,
            target_day=target_date,
            data_cutoff=cutoff_date,
            run_id=f"lgbm_v1_{target_date}",
            model_version="epf_v1",
        )

        # Keep only the required columns
        keep_cols = [
            "task", "model_name", "forecast_date", "target_day",
            "business_day", "ds", "hour_business", "period", "y_pred",
            "data_cutoff", "run_id", "model_version",
        ]
        df = df[[c for c in keep_cols if c in df.columns]]

        return df

    def _find_data_file(self) -> str:
        """Auto-locate data file in EPF v1.0 repo."""
        candidates = [
            self.epf_root / "data" / "shandong_pmos_hourly.xlsx",
            self.epf_root / "data" / "shandong_pmos_hourly.csv",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        raise FileNotFoundError(
            f"No data file found in {self.epf_root / 'data'}"
        )
