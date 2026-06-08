from __future__ import annotations

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
PREP_MANIFEST_PATH = PROJECT_ROOT / "reports" / "new_cycle_prep" / "new_cycle_prep_manifest.json"
PREP_DIR = PROJECT_ROOT / "reports" / "new_cycle_prep"
KICKOFF_DIR = PROJECT_ROOT / "reports" / "cycle_kickoff"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "NEW_CYCLE_READY" or state.get("current_branch") != "new_cycle_prep_complete":
        raise ValueError("Cycle kickoff is only allowed from NEW_CYCLE_READY / new_cycle_prep_complete.")
    if not PREP_MANIFEST_PATH.exists():
        raise FileNotFoundError("new_cycle_prep_manifest.json is required before cycle kickoff.")

    hypothesis = (PREP_DIR / "hypothesis_memo.md").read_text(encoding="utf-8")
    redesign = (PREP_DIR / "feature_task_redesign_note.md").read_text(encoding="utf-8")

    KICKOFF_DIR.mkdir(parents=True, exist_ok=True)

    kickoff_plan = (
        "# Cycle Kickoff Plan\n\n"
        "## Goal\n\n"
        "- Launch the next fresh research cycle for stronger point forecasting under the fixed Protocol B contract.\n\n"
        "## First Execution Wave\n\n"
        "1. Build a fresh hypothesis-driven J1/J2 point-signal branch.\n"
        "2. Keep the accepted landing baseline as the comparison anchor.\n"
        "3. Start with one changed factor: stronger raw-error-oriented feature redesign.\n"
        "4. Do not reopen exhausted V2 branches as the default path.\n\n"
        "## Inputs\n\n"
        "- hypothesis memo\n"
        "- feature/task redesign note\n"
        "- experiment ledger seed\n"
    )
    (KICKOFF_DIR / "cycle_kickoff_plan.md").write_text(kickoff_plan, encoding="utf-8")

    experiment_seed = (
        "experiment_id,stage,branch,hypothesis,changed_factor,baseline_artifact,planned_config_name,expected_outputs\n"
        f"kickoff_001,J1_or_new_model_line,point_signal_redesign,\"stronger point-signal redesign for 9_16 raw error\",\"feature/task redesign\",\"{state['current_best_artifact']}\",\"kickoff_feature_redesign_v1.yaml\",\"predictions.csv;monthly_summary.csv;leakage_audit.md\"\n"
    )
    (KICKOFF_DIR / "kickoff_experiment_seed.csv").write_text(experiment_seed, encoding="utf-8")

    config_seed = (
        "experiment_name: SGDFNet_Kickoff_FeatureRedesign_V1\n"
        "protocol: Protocol B rolling monthly 2025\n"
        "baseline_artifact: " + state["current_best_artifact"].replace("\\", "/") + "\n"
        "objective:\n"
        "  primary_overall_metric: rt_smape\n"
        "  primary_segment_metric: segment_9_16_rt_smape\n"
        "  secondary_business_metric: rt_capped_smape_floor_50\n"
        "changed_factor: stronger raw-error-oriented feature redesign\n"
        "notes:\n"
        "  - keep frozen landing artifact fixed\n"
        "  - one main factor only\n"
        "  - no probability-only claims for point improvement\n"
    )
    (KICKOFF_DIR / "kickoff_config_seed.yaml").write_text(config_seed, encoding="utf-8")

    kickoff_manifest = {
        "generated_on": str(date.today()),
        "source_prep_manifest": str(PREP_MANIFEST_PATH.resolve()),
        "outputs": [
            "cycle_kickoff_plan.md",
            "kickoff_experiment_seed.csv",
            "kickoff_config_seed.yaml",
        ],
        "kickoff_status": "ready",
    }
    _write_json(KICKOFF_DIR / "cycle_kickoff_manifest.json", kickoff_manifest)

    state["current_stage"] = "KICKOFF_READY"
    state["current_branch"] = "cycle_kickoff_complete"
    state["allowed_next_actions"] = [
        "review kickoff plan",
        "instantiate the first new-cycle experiment from the kickoff config seed",
        "begin the next implementation branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_READY`\n"
        "- Current branch state: `cycle_kickoff_complete`\n"
        f"- Cycle kickoff dir: `{KICKOFF_DIR.resolve()}`\n",
        encoding="utf-8",
    )

    print(str((KICKOFF_DIR / "cycle_kickoff_manifest.json").resolve()))


if __name__ == "__main__":
    main()
