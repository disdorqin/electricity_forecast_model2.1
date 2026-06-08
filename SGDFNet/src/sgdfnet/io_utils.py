from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def resolve_output_dir(output_dir: str | Path, overwrite: bool = False) -> Path:
    path = Path(output_dir)
    if path.exists() and any(path.iterdir()) and not overwrite:
        raise FileExistsError(f"Output directory already exists and is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def write_json(path: str | Path, payload: Any) -> None:
    out = Path(path)
    out.write_text(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def snapshot_run_config(config: Any, cli_args: dict[str, Any], data_path: str | Path, output_dir: str | Path) -> None:
    payload = {
        "config": _to_jsonable(config),
        "cli_args": _to_jsonable(cli_args),
        "data_path": str(Path(data_path)),
        "output_dir": str(Path(output_dir)),
    }
    write_json(Path(output_dir) / "config_snapshot.json", payload)
