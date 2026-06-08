from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib


def save_checkpoint(payload: dict[str, Any], output_dir: str | Path, filename: str = "checkpoint.joblib") -> Path:
    path = Path(output_dir) / filename
    joblib.dump(payload, path)
    return path


def load_checkpoint(path: str | Path) -> dict[str, Any]:
    return joblib.load(Path(path))
