from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
INSTANCE_DIR = PROJECT_ROOT / "reports" / "first_experiment_instance"
INSTANCE_MANIFEST = INSTANCE_DIR / "first_experiment_instance_manifest.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "FIRST_EXPERIMENT_READY" or state.get("current_branch") != "first_experiment_instance_complete":
        raise ValueError("First experiment execution is only allowed from FIRST_EXPERIMENT_READY / first_experiment_instance_complete.")
    if not INSTANCE_MANIFEST.exists():
        raise FileNotFoundError("first_experiment_instance_manifest.json is required before execution.")

    manifest = _load_json(INSTANCE_MANIFEST)
    config_name = manifest["planned_config_name"]
    config_path = INSTANCE_DIR / config_name
    if not config_path.exists():
        raise FileNotFoundError(f"Expected config does not exist: {config_path}")

    cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
    completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
    run_dir = completed.stdout.strip().splitlines()[-1].strip()

    manifest["instance_status"] = "executed"
    manifest["executed_on"] = str(date.today())
    manifest["run_artifact"] = run_dir
    _write_json(INSTANCE_MANIFEST, manifest)

    (INSTANCE_DIR / "FIRST_EXPERIMENT_RESULT.md").write_text(
        "# First Experiment Result\n\n"
        f"- Run artifact: `{run_dir}`\n"
        f"- Executed on: `{date.today()}`\n"
        "- This is the first concrete new-cycle experiment generated and executed by the automation pipeline.\n",
        encoding="utf-8",
    )

    state["current_stage"] = "FIRST_EXPERIMENT_RAN"
    state["current_branch"] = "first_experiment_run_complete"
    state["allowed_next_actions"] = [
        "review first experiment outputs",
        "compare the first experiment against the frozen landing baseline",
        "register the first new-cycle result in a fresh ledger",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FIRST_EXPERIMENT_RAN`\n"
        "- Current branch state: `first_experiment_run_complete`\n"
        f"- First experiment artifact: `{run_dir}`\n",
        encoding="utf-8",
    )

    print(run_dir)


if __name__ == "__main__":
    main()
