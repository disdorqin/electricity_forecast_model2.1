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
    if state.get("current_stage") != "STRUCTURAL_FAMILY_EXPERIMENT_READY" or state.get("current_branch") != "structural_family_experiment_instance_complete":
        raise ValueError("Structural family experiment execution is only allowed from STRUCTURAL_FAMILY_EXPERIMENT_READY.")

    instance_dir = Path(state["active_structural_instance_dir"])
    manifest_path = instance_dir / "manifest.json"
    manifest = _load_json(manifest_path)
    config_path = Path(manifest["config_path"])

    cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
    completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
    run_dir = completed.stdout.strip().splitlines()[-1].strip()

    manifest["instance_status"] = "executed"
    manifest["executed_on"] = str(date.today())
    manifest["run_artifact"] = run_dir
    _write_json(manifest_path, manifest)

    state["current_stage"] = "STRUCTURAL_FAMILY_EXPERIMENT_RAN"
    state["current_branch"] = "structural_family_experiment_run_complete"
    state["last_candidate_artifact"] = run_dir
    state["allowed_next_actions"] = [
        "evaluate the structural family experiment",
        "compare the new main-model family against the frozen baseline",
        "either keep expanding or stop this family",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `STRUCTURAL_FAMILY_EXPERIMENT_RAN`\n"
        "- Current branch state: `structural_family_experiment_run_complete`\n"
        f"- Active structural family experiment: `{manifest['experiment_id']}`\n"
        f"- Run artifact: `{run_dir}`\n",
        encoding="utf-8",
    )

    print(run_dir)


if __name__ == "__main__":
    main()
