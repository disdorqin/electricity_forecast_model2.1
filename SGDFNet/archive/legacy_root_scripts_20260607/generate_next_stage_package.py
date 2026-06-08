from __future__ import annotations

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
NEXT_ACTION_MD = PROJECT_ROOT / "reports" / "v2_continuous" / "v2_next_action.md"
PACKAGE_DIR = PROJECT_ROOT / "reports" / "next_stage_package"
PACKAGE_JSON = PACKAGE_DIR / "next_stage_package.json"
PACKAGE_MD = PACKAGE_DIR / "NEXT_STAGE_PACKAGE.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_rel(path_like: str) -> str:
    return path_like.replace("/", "\\")


def _determine_package(state: dict, registry: dict) -> dict:
    current_branch = state.get("current_branch", "")
    final_candidate = registry.get("final_candidate")
    accepted_interval = registry.get("accepted_interval_module")
    baseline_artifact = _repo_rel(state["frozen_execution_baseline_artifact"])
    baseline_config = state["frozen_execution_baseline_config"]

    if current_branch == "v2_complete_baseline_plus_interval_module" and final_candidate is not None:
        return {
            "package_type": "paper_package_prep",
            "status": "ready",
            "trigger_state": current_branch,
            "recommended_stage": "J8",
            "recommended_action": "prepare robustness and paper package for frozen landing baseline plus accepted interval module",
            "point_baseline_artifact": baseline_artifact,
            "point_baseline_config": baseline_config,
            "accepted_interval_module": accepted_interval,
            "must_produce": [
                "full 2025 point + interval summary table",
                "coverage/calibration summary",
                "negative-results summary for rejected V2 branches",
                "best model card",
            ],
            "blocked_actions": [
                "reopening rejected V2 branches without a new stage decision",
                "overwriting frozen landing artifact",
                "claiming point-metric improvement from interval-only module",
            ],
        }

    if current_branch == "v2_complete_frozen_landing_remains_final":
        return {
            "package_type": "new_research_branch_prep",
            "status": "ready",
            "trigger_state": current_branch,
            "recommended_stage": "J1_or_new_model_line",
            "recommended_action": "start a new baseline redesign line rather than further V2 branch tuning",
            "point_baseline_artifact": baseline_artifact,
            "point_baseline_config": baseline_config,
            "must_produce": [
                "new hypothesis memo",
                "feature/task redesign package",
                "fresh branch ledger seed",
            ],
            "blocked_actions": [
                "repeating exhausted V2 branches",
                "test-driven threshold micro-tuning",
            ],
        }

    return {
        "package_type": "continue_current_loop",
        "status": "not_ready",
        "trigger_state": current_branch,
        "recommended_stage": "V2_CONTINUOUS",
        "recommended_action": "continue current loop from state machine",
        "point_baseline_artifact": baseline_artifact,
        "point_baseline_config": baseline_config,
        "must_produce": [],
        "blocked_actions": [],
    }


def main() -> None:
    state = _load_json(STATE_PATH)
    registry = _load_json(REGISTRY_PATH)
    package = _determine_package(state, registry)
    package["generated_on"] = str(date.today())
    package["state_path"] = str(STATE_PATH.resolve())
    package["registry_path"] = str(REGISTRY_PATH.resolve())
    package["next_action_note"] = NEXT_ACTION_MD.read_text(encoding="utf-8").strip() if NEXT_ACTION_MD.exists() else ""

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_JSON.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Next Stage Package",
        "",
        f"- Status: `{package['status']}`",
        f"- Trigger state: `{package['trigger_state']}`",
        f"- Recommended stage: `{package['recommended_stage']}`",
        f"- Recommended action: `{package['recommended_action']}`",
        f"- Point baseline artifact: `{package['point_baseline_artifact']}`",
        f"- Point baseline config: `{package['point_baseline_config']}`",
    ]
    if package.get("accepted_interval_module"):
        interval = package["accepted_interval_module"]
        md_lines.extend(
            [
                f"- Accepted interval module: `{interval['variant']}`",
                f"- Interval artifact: `{interval['artifact']}`",
                f"- Interval config: `{interval['config']}`",
            ]
        )
    if package["must_produce"]:
        md_lines.append("- Must produce:")
        for item in package["must_produce"]:
            md_lines.append(f"  - {item}")
    if package["blocked_actions"]:
        md_lines.append("- Blocked actions:")
        for item in package["blocked_actions"]:
            md_lines.append(f"  - {item}")
    if package["next_action_note"]:
        md_lines.extend(["", "## Current Next-Action Note", "", package["next_action_note"]])

    PACKAGE_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(str(PACKAGE_JSON.resolve()))


if __name__ == "__main__":
    main()
