from __future__ import annotations

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
INIT_PATH = PROJECT_ROOT / "reports" / "new_branch_init" / "new_branch_init.json"
PREP_DIR = PROJECT_ROOT / "reports" / "new_cycle_prep"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "NEW_BRANCH_PREP" or state.get("current_branch") != "new_branch_init_ready":
        raise ValueError("New cycle prep is only allowed from NEW_BRANCH_PREP / new_branch_init_ready.")
    if not INIT_PATH.exists():
        raise FileNotFoundError("new_branch_init.json is required before new cycle prep.")

    init_payload = _load_json(INIT_PATH)
    PREP_DIR.mkdir(parents=True, exist_ok=True)

    hypothesis_memo = (
        "# Hypothesis Memo\n\n"
        "- New cycle type: `fresh_research_cycle`\n"
        "- Baseline artifact remains the frozen SGDFNet landing baseline.\n"
        "- Core problem: point forecasting still leaves strong raw-SMAPE concentration in `9_16`, especially around risk hours and hard months.\n"
        "- Main hypothesis for the next cycle: stronger point-signal redesign is needed; interval extension helped uncertainty but did not solve the point-error bottleneck.\n"
        "- First constraint: keep Protocol B and floor-50 capped business metric fixed.\n"
        "- Do not reopen exhausted V2 branches as the default next move.\n"
    )
    (PREP_DIR / "hypothesis_memo.md").write_text(hypothesis_memo, encoding="utf-8")

    feature_note = (
        "# Feature Redesign Note\n\n"
        "- Carry forward the accepted point baseline feature contract as the control reference.\n"
        "- Use the J8 package to summarize which months, segments, and hours remain hard under raw point metrics.\n"
        "- Start the next cycle with fresh point-signal feature/task redesign rather than probability-only extensions.\n"
        "- Candidate emphasis: DA-relative residual signal, segment-local hard-hour descriptors, and stronger raw-error-oriented redesign.\n"
    )
    (PREP_DIR / "feature_task_redesign_note.md").write_text(feature_note, encoding="utf-8")

    ledger_seed = (
        "experiment_id,timestamp,stage,branch,hypothesis,changed_factor,baseline_artifact,candidate_artifact,protocol,decision,reason,next_action\n"
    )
    (PREP_DIR / "experiment_ledger_seed.csv").write_text(ledger_seed, encoding="utf-8")

    prep_manifest = {
        "generated_on": str(date.today()),
        "source_init_package": str(INIT_PATH.resolve()),
        "outputs": [
            "hypothesis_memo.md",
            "feature_task_redesign_note.md",
            "experiment_ledger_seed.csv",
        ],
        "prep_status": "complete",
    }
    _write_json(PREP_DIR / "new_cycle_prep_manifest.json", prep_manifest)

    state["current_stage"] = "NEW_CYCLE_READY"
    state["current_branch"] = "new_cycle_prep_complete"
    state["allowed_next_actions"] = [
        "review new cycle prep artifacts",
        "start the next experiment cycle from the hypothesis memo and ledger seed",
        "open a new J1 or new-model-line implementation branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `NEW_CYCLE_READY`\n"
        "- Current branch state: `new_cycle_prep_complete`\n"
        f"- New cycle prep dir: `{PREP_DIR.resolve()}`\n",
        encoding="utf-8",
    )

    print(str((PREP_DIR / "new_cycle_prep_manifest.json").resolve()))


if __name__ == "__main__":
    main()
