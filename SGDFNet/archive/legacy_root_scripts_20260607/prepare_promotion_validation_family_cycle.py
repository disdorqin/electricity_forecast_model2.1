from __future__ import annotations

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
FUSION_RESULTS = PROJECT_ROOT / "reports" / "fusion_family_cycle" / "fusion_family_experiment_results.csv"
PROMO_DIR = PROJECT_ROOT / "reports" / "promotion_validation_family_cycle"
MANIFEST_JSON = PROMO_DIR / "promotion_validation_family_manifest.json"
SUMMARY_MD = PROMO_DIR / "promotion_validation_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Promotion Validation Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "FUSION_FAMILY_COMPLETE" or state.get("current_branch") != "fusion_family_candidate_pool_exhausted":
        raise ValueError("Promotion validation family prep is only allowed from FUSION_FAMILY_COMPLETE / fusion_family_candidate_pool_exhausted.")
    if not FUSION_RESULTS.exists():
        raise FileNotFoundError("fusion_family_experiment_results.csv is required before promotion validation prep.")

    PROMO_DIR.mkdir(parents=True, exist_ok=True)
    summary = (
        "# Promotion Validation Family Summary\n\n"
        "- Source state: `FUSION_FAMILY_COMPLETE / fusion_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        "- New family decision: validate the current best unified candidate on fresh 2026 data windows.\n"
        "- Reason:\n"
        "  - `ffam_002` is now the strongest unified candidate under 2025 rolling evaluation\n"
        "  - the next highest-value autonomous step is promotion-style validation, not another mechanism family\n"
        "  - 2026-04 incremental data is available locally and matches the project schema\n"
        "- First candidates:\n"
        "  - `promotion_validation_2026_04_fusion_bundle`\n"
        "  - `promotion_validation_2026_04_point_only_control`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(FUSION_RESULTS.resolve()),
        "next_family": "promotion_validation_family",
        "recommended_first_candidate": "promotion_validation_2026_04_fusion_bundle",
        "recommended_second_candidate": "promotion_validation_2026_04_point_only_control",
        "outputs": [
            "promotion_validation_family_summary.md",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Promotion Validation Family",
            "",
            "- The unified fusion candidate `ffam_002` is ready for fresh-window validation.",
            "- The next automated family is `promotion_validation_family`.",
            "- First candidate: `promotion_validation_2026_04_fusion_bundle`.",
            "- Second candidate: `promotion_validation_2026_04_point_only_control`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "PROMOTION_VALIDATION_FAMILY_PREPARED"
    state["current_branch"] = "promotion_validation_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the promotion validation family summary",
        "instantiate the first promotion validation candidate",
        "continue automated execution in the promotion-validation branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `PROMOTION_VALIDATION_FAMILY_PREPARED`\n"
        "- Current branch state: `promotion_validation_family_manifest_ready`\n"
        f"- Promotion validation family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
