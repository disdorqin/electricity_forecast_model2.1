from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
KSGATE_RESULTS = PROJECT_ROOT / "reports" / "kickoff_selective_gate_family_cycle" / "kickoff_selective_gate_experiment_results.csv"
KMHSEL_DIR = PROJECT_ROOT / "reports" / "kickoff_monthhour_selective_family_cycle"
MANIFEST_JSON = KMHSEL_DIR / "kickoff_monthhour_selective_family_manifest.json"
SUMMARY_MD = KMHSEL_DIR / "kickoff_monthhour_selective_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Kickoff MonthHour Selective Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if (state.get("current_stage"), state.get("current_branch")) != ("KICKOFF_SELECTIVE_GATE_FAMILY_COMPLETE", "kickoff_selective_gate_family_candidate_pool_exhausted"):
        raise ValueError("Kickoff month-hour selective family prep is only allowed after kickoff selective-gate exhaustion.")
    if not KSGATE_RESULTS.exists():
        raise FileNotFoundError("kickoff_selective_gate_experiment_results.csv is required before month-hour selective family prep.")

    results = pd.read_csv(KSGATE_RESULTS)
    best_nearmiss = results.sort_values(
        ["full_year_rt_capped_smape", "segment_9_16_rt_capped_smape", "top10_tail_rt_capped_smape"],
        ascending=[True, True, True],
    ).iloc[0].to_dict()

    KMHSEL_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(KMHSEL_DIR / "kickoff_selective_gate_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Kickoff MonthHour Selective Family Summary\n\n"
        "- Source state: `KICKOFF_SELECTIVE_GATE_FAMILY_COMPLETE / kickoff_selective_gate_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best selective-gate near-miss: `{best_nearmiss['experiment_id']}` with "
        f"`full_year_rt_capped_smape={best_nearmiss['full_year_rt_capped_smape']:.4f}`, "
        f"`segment_9_16_rt_capped_smape={best_nearmiss['segment_9_16_rt_capped_smape']:.4f}`, and "
        f"`top10_tail_rt_capped_smape={best_nearmiss['top10_tail_rt_capped_smape']:.4f}`.\n"
        "- New family decision: switch to a cleaner teacher driven by stable month-hour risk cells from the diagnosis, instead of tail-triggered residual medians.\n"
        "- First candidates:\n"
        "  - `kickoff_monthhour_selective_season_risk_hours`\n"
        "  - `kickoff_monthhour_selective_sign_consistent_risk_hours`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "kickoff_selective_gate_results": str(KSGATE_RESULTS.resolve()),
        "kickoff_nearmiss_baseline_artifact": best_nearmiss["point_baseline_artifact"],
        "next_family": "kickoff_monthhour_selective_family",
        "recommended_first_candidate": "kickoff_monthhour_selective_season_risk_hours",
        "recommended_second_candidate": "kickoff_monthhour_selective_sign_consistent_risk_hours",
        "outputs": [
            "kickoff_monthhour_selective_family_summary.md",
            "kickoff_selective_gate_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Kickoff MonthHour Selective Family",
            "",
            "- Kickoff selective-gate reduced raw harm but still failed the acceptance gate.",
            "- The next automated family is `kickoff_monthhour_selective_family`.",
            "- First candidate: `kickoff_monthhour_selective_season_risk_hours`.",
            "- Second candidate: `kickoff_monthhour_selective_sign_consistent_risk_hours`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_PREPARED"
    state["current_branch"] = "kickoff_monthhour_selective_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the kickoff month-hour selective family summary",
        "instantiate the first kickoff month-hour selective experiment",
        "continue automated execution in the kickoff month-hour selective branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_PREPARED`\n"
        "- Current branch state: `kickoff_monthhour_selective_family_manifest_ready`\n"
        f"- Kickoff month-hour selective family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
