from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "PROMOTION_VALIDATION_EXPERIMENT_READY" or state.get("current_branch") != "promotion_validation_experiment_instance_complete":
        raise ValueError("Promotion validation experiment run is only allowed from PROMOTION_VALIDATION_EXPERIMENT_READY.")

    instance_dir = Path(state["active_promotion_validation_instance_dir"])
    manifest_path = instance_dir / "manifest.json"
    manifest = _load_json(manifest_path)
    config_path = Path(manifest["config_path"])

    cmd = [sys.executable, str(PROJECT_ROOT / "run_promotion_validation.py"), "--config", str(config_path)]
    completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
    run_artifact = completed.stdout.strip().splitlines()[-1].strip()

    manifest["run_artifact"] = run_artifact.replace("/", "\\")
    manifest["run_completed_on"] = str(date.today())
    manifest["run_status"] = "completed"
    _write_json(manifest_path, manifest)

    state["current_stage"] = "PROMOTION_VALIDATION_EXPERIMENT_RAN"
    state["current_branch"] = "promotion_validation_experiment_run_complete"
    state["last_candidate_artifact"] = manifest["run_artifact"]
    state["allowed_next_actions"] = [
        "evaluate the promotion validation experiment",
        "compare it against the promoted unified candidate",
        "either keep expanding or stop this family",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `PROMOTION_VALIDATION_EXPERIMENT_RAN`\n"
        "- Current branch state: `promotion_validation_experiment_run_complete`\n"
        f"- Active promotion validation experiment: `{manifest['experiment_id']}`\n"
        f"- Run artifact: `{manifest['run_artifact']}`\n",
        encoding="utf-8",
    )

    print(manifest["run_artifact"])


if __name__ == "__main__":
    main()
