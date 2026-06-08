from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
FOLLOWUP_DIR = PROJECT_ROOT / "reports" / "followup_cycle"
FOLLOWUP_RESULTS = FOLLOWUP_DIR / "followup_experiment_results.csv"
NEXT_FAMILY_DIR = PROJECT_ROOT / "reports" / "next_family_cycle"
MANIFEST_JSON = NEXT_FAMILY_DIR / "next_family_cycle_manifest.json"
SUMMARY_MD = NEXT_FAMILY_DIR / "next_family_cycle_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Next Family Cycle"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "FOLLOWUP_CYCLE_COMPLETE" or state.get("current_branch") != "followup_candidate_pool_exhausted":
        raise ValueError("Next-family prep is only allowed from FOLLOWUP_CYCLE_COMPLETE / followup_candidate_pool_exhausted.")
    if not FOLLOWUP_RESULTS.exists():
        raise FileNotFoundError("followup_experiment_results.csv is required before next-family prep.")

    followup = pd.read_csv(FOLLOWUP_RESULTS)
    best_raw = followup.sort_values(["segment_9_16_rt_smape", "overall_rt_smape"]).iloc[0].to_dict()
    best_capped = followup.sort_values(["segment_9_16_rt_capped_smape", "overall_rt_capped_smape"]).iloc[0].to_dict()

    NEXT_FAMILY_DIR.mkdir(parents=True, exist_ok=True)
    followup.to_csv(NEXT_FAMILY_DIR / "followup_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Next Family Cycle Summary\n\n"
        "- Source state: `FOLLOWUP_CYCLE_COMPLETE / followup_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Follow-up TF family conclusion:\n"
        f"  - best raw-near-miss candidate: `{best_raw['experiment_id']}` with `segment_9_16_rt_smape={best_raw['segment_9_16_rt_smape']:.4f}`, `overall_rt_smape={best_raw['overall_rt_smape']:.4f}`\n"
        f"  - best capped/tail candidate: `{best_capped['experiment_id']}` with `segment_9_16_rt_capped_smape={best_capped['segment_9_16_rt_capped_smape']:.4f}`, `overall_rt_capped_smape={best_capped['overall_rt_capped_smape']:.4f}`\n"
        "- New family decision: keep the strongest TF+pressure point-signal base and add leakage-safe risk-hour localized calibration.\n"
        "- Reason:\n"
        "  - pure TF improved tails/capped but not enough on raw 9_16\n"
        "  - TF+pressure moved closer to the raw baseline while keeping capped/tail gains\n"
        "  - the next falsifiable question is whether localized risk-hour calibration can convert that near-miss into a raw 9_16 win\n"
        "- First candidates:\n"
        "  - `hour_bias_risk_extended_on_tf_pressure`\n"
        "  - `segment_hour_bias_risk_extended_on_tf_pressure`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "followup_results": str(FOLLOWUP_RESULTS.resolve()),
        "next_family": "tf_pressure_risk_hour_localized_calibration",
        "recommended_first_candidate": "hour_bias_risk_extended_on_tf_pressure",
        "recommended_second_candidate": "segment_hour_bias_risk_extended_on_tf_pressure",
        "outputs": [
            "next_family_cycle_summary.md",
            "followup_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Next Family Cycle",
            "",
            "- The TF follow-up family is exhausted but not useless: `TF + pressure` is the closest raw near-miss and keeps capped/tail gains.",
            "- The next automated family is `tf_pressure_risk_hour_localized_calibration`.",
            "- First candidate: `hour_bias_risk_extended_on_tf_pressure`.",
            "- Second candidate: `segment_hour_bias_risk_extended_on_tf_pressure`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "NEXT_FAMILY_CYCLE_PREPARED"
    state["current_branch"] = "next_family_cycle_manifest_ready"
    state["allowed_next_actions"] = [
        "review the next-family cycle summary",
        "instantiate the first localized-calibration candidate",
        "continue automated execution in the new family",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `NEXT_FAMILY_CYCLE_PREPARED`\n"
        "- Current branch state: `next_family_cycle_manifest_ready`\n"
        f"- Next-family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
