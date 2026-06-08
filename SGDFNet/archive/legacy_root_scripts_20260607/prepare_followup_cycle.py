from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
FRESH_LEDGER_PATH = PROJECT_ROOT / "reports" / "fresh_cycle" / "fresh_cycle_ledger.csv"
FOLLOWUP_DIR = PROJECT_ROOT / "reports" / "followup_cycle"
SUMMARY_MD = FOLLOWUP_DIR / "followup_cycle_summary.md"
MANIFEST_JSON = FOLLOWUP_DIR / "followup_cycle_manifest.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_memory(summary_lines: list[str]) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    section = "\n".join(summary_lines)
    marker = "## Follow-Up Cycle"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    registry = _load_json(REGISTRY_PATH)
    if state.get("current_stage") != "FRESH_CYCLE_COMPLETE" or state.get("current_branch") != "fresh_cycle_candidate_pool_exhausted":
        raise ValueError("Follow-up cycle prep is only allowed from FRESH_CYCLE_COMPLETE / fresh_cycle_candidate_pool_exhausted.")
    if not FRESH_LEDGER_PATH.exists():
        raise FileNotFoundError("fresh_cycle_ledger.csv is required before follow-up cycle prep.")

    ledger = pd.read_csv(FRESH_LEDGER_PATH)
    ledger = ledger.copy()
    ledger["overall_rt_smape_delta"] = ledger["overall_rt_smape"] - 20.79251599092717
    ledger["segment_9_16_rt_smape_delta"] = ledger["segment_9_16_rt_smape"] - 36.343056642225086
    ledger["overall_rt_capped_smape_delta"] = ledger["overall_rt_capped_smape"] - 10.906743313696468
    ledger["segment_9_16_rt_capped_smape_delta"] = ledger["segment_9_16_rt_capped_smape"] - 15.504180616043215

    best_row = ledger.sort_values(["segment_9_16_rt_smape", "overall_rt_smape"]).iloc[0].to_dict()
    worst_row = ledger.sort_values(["segment_9_16_rt_smape", "overall_rt_smape"], ascending=False).iloc[0].to_dict()

    FOLLOWUP_DIR.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(FOLLOWUP_DIR / "fresh_cycle_ledger_snapshot.csv", index=False, encoding="utf-8-sig")

    summary_text = (
        "# Follow-Up Cycle Summary\n\n"
        "- Source state: `FRESH_CYCLE_COMPLETE / fresh_cycle_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Fresh-cycle conclusion: all tried one-main-factor point-signal variants were rejected under the raw-metric hierarchy.\n"
        f"- Best rejected fresh-cycle candidate by 9_16 raw SMAPE: `{best_row['experiment_id']}` with `segment_9_16_rt_smape={best_row['segment_9_16_rt_smape']:.4f}` and `overall_rt_smape={best_row['overall_rt_smape']:.4f}`.\n"
        f"- Worst rejected fresh-cycle candidate by 9_16 raw SMAPE: `{worst_row['experiment_id']}` with `segment_9_16_rt_smape={worst_row['segment_9_16_rt_smape']:.4f}` and `overall_rt_smape={worst_row['overall_rt_smape']:.4f}`.\n"
        "- Follow-up family decision: move to a new point-signal family centered on time-frequency moving-average residual features.\n"
        "- Rationale:\n"
        "  - segment-local stats family already failed\n"
        "  - forecast-pressure interaction family already failed\n"
        "  - naive weekly-history family already failed\n"
        "  - time-frequency moving-average features exist in the SGDFNet feature contract but have not yet been run in this post-landing autonomous point line\n"
        "- Guardrails:\n"
        "  - keep Protocol B fixed\n"
        "  - keep floor-50 business metric reporting fixed\n"
        "  - keep frozen landing artifact unchanged\n"
        "  - change one mechanism family only\n"
    )
    SUMMARY_MD.write_text(summary_text, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "fresh_cycle_ledger": str(FRESH_LEDGER_PATH.resolve()),
        "next_family": "time_frequency_point_signal",
        "recommended_first_candidate": "tf_moving_average_features_enabled",
        "accepted_interval_module": registry.get("accepted_interval_module"),
        "outputs": [
            "followup_cycle_summary.md",
            "fresh_cycle_ledger_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    memory_lines = [
        "## Follow-Up Cycle",
        "",
        "- Fresh-cycle point-signal candidate pool has been exhausted with all candidates rejected.",
        "- The next automated family is `time_frequency_point_signal`.",
        "- First follow-up candidate: `tf_moving_average_features_enabled`.",
        "- Interval extension remains accepted for uncertainty, but point-search must continue separately.",
        "",
    ]
    _update_memory(memory_lines)

    state["current_stage"] = "FOLLOWUP_CYCLE_PREPARED"
    state["current_branch"] = "followup_cycle_manifest_ready"
    state["allowed_next_actions"] = [
        "review the follow-up cycle summary",
        "instantiate the first follow-up point-signal experiment",
        "continue automated experiment execution in the new family",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FOLLOWUP_CYCLE_PREPARED`\n"
        "- Current branch state: `followup_cycle_manifest_ready`\n"
        f"- Follow-up cycle manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
