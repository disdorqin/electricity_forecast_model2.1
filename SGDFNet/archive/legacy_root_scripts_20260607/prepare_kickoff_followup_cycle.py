from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
FRESH_LEDGER_PATH = PROJECT_ROOT / "reports" / "fresh_cycle" / "fresh_cycle_ledger.csv"
KFOLLOW_DIR = PROJECT_ROOT / "reports" / "kickoff_followup_cycle"
SUMMARY_MD = KFOLLOW_DIR / "kickoff_followup_cycle_summary.md"
MANIFEST_JSON = KFOLLOW_DIR / "kickoff_followup_cycle_manifest.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Kickoff Follow-Up Cycle"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "FRESH_CYCLE_COMPLETE" or state.get("current_branch") != "fresh_cycle_candidate_pool_exhausted":
        raise ValueError("Kickoff follow-up prep is only allowed from FRESH_CYCLE_COMPLETE / fresh_cycle_candidate_pool_exhausted.")
    if not FRESH_LEDGER_PATH.exists():
        raise FileNotFoundError("fresh_cycle_ledger.csv is required before kickoff follow-up prep.")

    ledger = pd.read_csv(FRESH_LEDGER_PATH)
    latest = ledger[ledger["experiment_id"] == "kickoff_001"].copy()
    latest_row = latest.iloc[-1].to_dict() if not latest.empty else None

    KFOLLOW_DIR.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(KFOLLOW_DIR / "fresh_cycle_ledger_snapshot.csv", index=False, encoding="utf-8-sig")

    summary_text = (
        "# Kickoff Follow-Up Cycle Summary\n\n"
        "- Source state: `FRESH_CYCLE_COMPLETE / fresh_cycle_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Kickoff fresh-cycle conclusion: the first new-cycle feature-redesign attempt was rejected and the historical fresh-cycle pool is already exhausted.\n"
        + (
            f"- Kickoff rejection reference: `{latest_row['experiment_id']}` with `overall_rt_smape={latest_row['overall_rt_smape']:.4f}` and `segment_9_16_rt_smape={latest_row['segment_9_16_rt_smape']:.4f}`.\n"
            if latest_row is not None
            else ""
        )
        + "- New family decision: open a kickoff-specific time-frequency follow-up family with fresh candidate IDs so automation can continue without colliding with the legacy follow-up pool.\n"
        "- Rationale:\n"
        "  - the first kickoff feature redesign worsened raw 9_16 noticeably\n"
        "  - legacy follow-up candidates were already consumed in a previous autonomous cycle\n"
        "  - we still need a fresh post-kickoff point-signal family rather than stopping at one rejected attempt\n"
        "- Guardrails:\n"
        "  - keep Protocol B fixed\n"
        "  - keep floor-50 business metric reporting fixed\n"
        "  - keep frozen landing artifact unchanged\n"
        "  - use fresh candidate IDs and one main factor per experiment\n"
    )
    SUMMARY_MD.write_text(summary_text, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "fresh_cycle_ledger": str(FRESH_LEDGER_PATH.resolve()),
        "next_family": "kickoff_time_frequency_point_signal",
        "recommended_first_candidate": "tf_moving_average_plus_segment_local_enabled",
        "outputs": [
            "kickoff_followup_cycle_summary.md",
            "fresh_cycle_ledger_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    _update_memory(
        "\n".join(
            [
                "## Kickoff Follow-Up Cycle",
                "",
                "- The kickoff fresh-cycle attempt `kickoff_001` was rejected.",
                "- Legacy follow-up candidates are already exhausted, so a fresh kickoff-specific family is required.",
                "- The next automated family is `kickoff_time_frequency_point_signal`.",
                "- First kickoff follow-up candidate: `tf_moving_average_plus_segment_local_enabled`.",
                "",
            ]
        )
    )

    state["current_stage"] = "KICKOFF_FOLLOWUP_CYCLE_PREPARED"
    state["current_branch"] = "kickoff_followup_cycle_manifest_ready"
    state["allowed_next_actions"] = [
        "review the kickoff follow-up summary",
        "instantiate the first kickoff follow-up experiment",
        "continue automated execution in the new kickoff follow-up family",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_FOLLOWUP_CYCLE_PREPARED`\n"
        "- Current branch state: `kickoff_followup_cycle_manifest_ready`\n"
        f"- Kickoff follow-up manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
