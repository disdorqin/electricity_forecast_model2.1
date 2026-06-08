from __future__ import annotations

import csv
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import yaml

from signed_tail_calibration_family_catalog import list_signed_tail_calibration_candidates


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
CAL_DIR = PROJECT_ROOT / "reports" / "signed_tail_calibration_family_cycle"
INSTANCES_DIR = CAL_DIR / "instances"
RESULTS_CSV = CAL_DIR / "signed_tail_calibration_experiment_results.csv"
BASE_CONFIG = PROJECT_ROOT / "configs" / "v2_signed_tail_calibration_base.yaml"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)


def _deep_update(base: dict, updates: dict) -> dict:
    merged = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_update(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_attempted_history() -> tuple[set[str], set[str]]:
    attempted_ids: set[str] = set()
    attempted_factors: set[str] = set()
    if RESULTS_CSV.exists():
        with RESULTS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        attempted_ids |= {row["experiment_id"] for row in rows if row.get("experiment_id")}
        attempted_factors |= {row["changed_factor"] for row in rows if row.get("changed_factor")}
    return attempted_ids, attempted_factors


def _select_next_candidate() -> dict | None:
    attempted_ids, attempted_factors = _load_attempted_history()
    for candidate in list_signed_tail_calibration_candidates():
        if candidate["experiment_id"] in attempted_ids:
            continue
        if candidate["changed_factor"] in attempted_factors:
            continue
        return candidate
    return None


def main() -> None:
    state = _load_json(STATE_PATH)
    allowed_states = {
        ("SIGNED_TAIL_CALIBRATION_FAMILY_PREPARED", "signed_tail_calibration_family_manifest_ready"),
        ("SIGNED_TAIL_CALIBRATION_EXPERIMENT_EVALUATED", "signed_tail_calibration_experiment_decision_complete"),
    }
    if (state.get("current_stage"), state.get("current_branch")) not in allowed_states:
        raise ValueError("Signed-tail calibration family instantiation is only allowed from the prepared or evaluated family states.")

    candidate = _select_next_candidate()
    if candidate is None:
        state["current_stage"] = "SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE"
        state["current_branch"] = "signed_tail_calibration_family_candidate_pool_exhausted"
        state["allowed_next_actions"] = [
            "review the signed-tail calibration family results",
            "package the signed-tail calibration evidence",
            "decide whether the automation should stop or open another mechanism family",
        ]
        _write_json(STATE_PATH, state)
        AUTO_SUMMARY_PATH.write_text(
            "# SGDFNet Auto Research Summary\n\n"
            f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
            "- Active stage: `SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE`\n"
            "- Current branch state: `signed_tail_calibration_family_candidate_pool_exhausted`\n"
            f"- Signed-tail calibration family results file: `{RESULTS_CSV.resolve()}`\n",
            encoding="utf-8",
        )
        print(str(RESULTS_CSV.resolve()))
        return

    base_config = _load_yaml(BASE_CONFIG)
    instantiated_config = _deep_update(base_config, candidate["config_updates"])
    instantiated_config["experiment_name"] = candidate["experiment_name"]
    instantiated_config["instance_id"] = candidate["experiment_id"]
    instantiated_config["status"] = "runnable"
    instantiated_config["frozen_execution_baseline_reference"] = state["frozen_execution_baseline_artifact"].replace("\\", "/")
    instantiated_config["changed_factor_label"] = candidate["changed_factor"]

    instance_dir = INSTANCES_DIR / candidate["instance_slug"]
    instance_dir.mkdir(parents=True, exist_ok=True)
    config_path = instance_dir / "experiment_config.yaml"
    _write_yaml(config_path, instantiated_config)

    manifest = {
        "generated_on": str(date.today()),
        "experiment_id": candidate["experiment_id"],
        "sequence_id": candidate["sequence_id"],
        "stage": candidate["stage"],
        "branch": candidate["branch"],
        "hypothesis": candidate["hypothesis"],
        "changed_factor": candidate["changed_factor"],
        "frozen_execution_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "point_probability_baseline_artifact": instantiated_config["baseline_artifact"],
        "config_path": str(config_path.resolve()),
        "instance_dir": str(instance_dir.resolve()),
        "instance_slug": candidate["instance_slug"],
        "instance_status": "runnable",
        "outputs": [
            "experiment_config.yaml",
            "manifest.json",
        ],
    }
    _write_json(instance_dir / "manifest.json", manifest)

    state["current_stage"] = "SIGNED_TAIL_CALIBRATION_EXPERIMENT_READY"
    state["current_branch"] = "signed_tail_calibration_experiment_instance_complete"
    state["active_signed_tail_calibration_experiment_id"] = candidate["experiment_id"]
    state["active_signed_tail_calibration_instance_dir"] = str(instance_dir.resolve())
    state["allowed_next_actions"] = [
        "run the instantiated signed-tail calibration experiment",
        "compare it against the frozen execution baseline",
        "decide whether this signed-tail calibration family should keep expanding",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `SIGNED_TAIL_CALIBRATION_EXPERIMENT_READY`\n"
        "- Current branch state: `signed_tail_calibration_experiment_instance_complete`\n"
        f"- Active signed-tail calibration experiment: `{candidate['experiment_id']}`\n"
        f"- Instance dir: `{instance_dir.resolve()}`\n",
        encoding="utf-8",
    )

    print(str((instance_dir / "manifest.json").resolve()))


if __name__ == "__main__":
    main()
