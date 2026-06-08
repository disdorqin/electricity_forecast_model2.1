from __future__ import annotations

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
J8_MANIFEST_PATH = PROJECT_ROOT / "reports" / "j8_package" / "j8_package_manifest.json"
INIT_DIR = PROJECT_ROOT / "reports" / "new_branch_init"
INIT_JSON = INIT_DIR / "new_branch_init.json"
INIT_MD = INIT_DIR / "NEW_BRANCH_INIT.md"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    registry = _load_json(REGISTRY_PATH)
    if state.get("current_stage") != "J8" or state.get("current_branch") != "j8_package_complete":
        raise ValueError("New branch initialization is only allowed after J8 package completion.")
    if not J8_MANIFEST_PATH.exists():
        raise FileNotFoundError("J8 manifest is required before new branch initialization.")

    j8_manifest = _load_json(J8_MANIFEST_PATH)
    final_candidate = registry.get("final_candidate", {})
    init_payload = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "new_branch_type": "fresh_research_cycle",
        "recommended_stage": "J1_or_new_model_line",
        "baseline_artifact": state["current_best_artifact"],
        "baseline_config": state["current_best_config"],
        "carry_forward_assets": {
            "j8_manifest": str(J8_MANIFEST_PATH.resolve()),
            "landing_artifact": state["frozen_landing_artifact"],
            "interval_extension": final_candidate.get("interval_module"),
        },
        "must_start_with": [
            "new hypothesis memo",
            "fresh feature/task redesign note",
            "new experiment ledger seed",
            "explicit reason for not repeating exhausted V2 branches",
        ],
        "blocked_actions": [
            "reopening V2 rejected branches as default next step",
            "claiming the interval module solved point forecasting",
            "editing frozen landing artifact",
        ],
        "suggested_first_moves": [
            "summarize failure concentration from J8 package into a new hypothesis memo",
            "open a fresh J1-style branch for stronger point-signal redesign",
            "keep Protocol B and floor-50 business metric fixed",
        ],
    }

    INIT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(INIT_JSON, init_payload)

    INIT_MD.write_text(
        "# New Branch Init\n\n"
        f"- Generated on: `{init_payload['generated_on']}`\n"
        f"- Source stage: `{init_payload['source_stage']}`\n"
        f"- Source branch: `{init_payload['source_branch']}`\n"
        f"- Recommended stage: `{init_payload['recommended_stage']}`\n"
        f"- Baseline artifact: `{init_payload['baseline_artifact']}`\n"
        f"- Baseline config: `{init_payload['baseline_config']}`\n"
        "- Must start with:\n"
        + "\n".join([f"  - {item}" for item in init_payload["must_start_with"]])
        + "\n- Blocked actions:\n"
        + "\n".join([f"  - {item}" for item in init_payload["blocked_actions"]])
        + "\n- Suggested first moves:\n"
        + "\n".join([f"  - {item}" for item in init_payload["suggested_first_moves"]])
        + "\n",
        encoding="utf-8",
    )

    state["current_stage"] = "NEW_BRANCH_PREP"
    state["current_branch"] = "new_branch_init_ready"
    state["allowed_next_actions"] = [
        "review new branch init package",
        "draft new hypothesis memo",
        "start the next research cycle from the new branch init package",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `NEW_BRANCH_PREP`\n"
        "- Current branch state: `new_branch_init_ready`\n"
        f"- New branch init package: `{INIT_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(INIT_JSON.resolve()))


if __name__ == "__main__":
    main()
