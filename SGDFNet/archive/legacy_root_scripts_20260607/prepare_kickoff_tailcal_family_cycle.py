from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
KFOLLOW_RESULTS = PROJECT_ROOT / "reports" / "kickoff_followup_cycle" / "kickoff_followup_experiment_results.csv"
KTCAL_DIR = PROJECT_ROOT / "reports" / "kickoff_tailcal_family_cycle"
MANIFEST_JSON = KTCAL_DIR / "kickoff_tailcal_family_manifest.json"
SUMMARY_MD = KTCAL_DIR / "kickoff_tailcal_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Kickoff Tail Calibration Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    allowed = {
        ("KICKOFF_FOLLOWUP_CYCLE_COMPLETE", "kickoff_followup_candidate_pool_exhausted"),
        ("KICKOFF_TAILCAL_FAMILY_COMPLETE", "kickoff_tailcal_family_candidate_pool_exhausted"),
    }
    if (state.get("current_stage"), state.get("current_branch")) not in allowed:
        raise ValueError("Kickoff tail-cal family prep is only allowed after kickoff follow-up exhaustion.")
    if not KFOLLOW_RESULTS.exists():
        raise FileNotFoundError("kickoff_followup_experiment_results.csv is required before kickoff tail-cal family prep.")

    results = pd.read_csv(KFOLLOW_RESULTS)
    best_nearmiss = results.sort_values(
        ["overall_rt_capped_smape", "segment_9_16_rt_capped_smape", "top10_tail_delta_mae"],
        ascending=[True, True, True],
    ).iloc[0].to_dict()

    KTCAL_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(KTCAL_DIR / "kickoff_followup_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Kickoff Tail Calibration Family Summary\n\n"
        "- Source state: `KICKOFF_FOLLOWUP_CYCLE_COMPLETE / kickoff_followup_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best kickoff follow-up near-miss: `{best_nearmiss['experiment_id']}` with "
        f"`overall_rt_capped_smape={best_nearmiss['overall_rt_capped_smape']:.4f}`, "
        f"`segment_9_16_rt_capped_smape={best_nearmiss['segment_9_16_rt_capped_smape']:.4f}`, and "
        f"`top10_tail_delta_mae={best_nearmiss['top10_tail_delta_mae']:.4f}`.\n"
        "- New family decision: attach a kickoff-specific signed-tail calibration branch on top of the best kickoff near-miss instead of reopening the legacy signed-tail family.\n"
        "- Reason:\n"
        "  - the kickoff TF+pressure+segment-local branch still regressed raw metrics\n"
        "  - but it preserved a small capped and tail signal worth testing with a lighter post-fit correction\n"
        "  - a fresh kickoff-specific family avoids historical ID collisions and keeps the automation chain moving forward\n"
        "- First candidates:\n"
        "  - `kickoff_signed_tail_probability_triggered_bias_global`\n"
        "  - `kickoff_signed_tail_probability_triggered_bias_9_16_seg_local`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "kickoff_followup_results": str(KFOLLOW_RESULTS.resolve()),
        "kickoff_nearmiss_baseline_artifact": best_nearmiss["candidate_artifact"],
        "next_family": "kickoff_signed_tail_calibration_family",
        "recommended_first_candidate": "kickoff_signed_tail_probability_triggered_bias_global",
        "recommended_second_candidate": "kickoff_signed_tail_probability_triggered_bias_9_16_seg_local",
        "outputs": [
            "kickoff_tailcal_family_summary.md",
            "kickoff_followup_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Kickoff Tail Calibration Family",
            "",
            "- Kickoff follow-up point-signal candidates were exhausted with no KEEP, but `kfollow_002` preserved a small capped and tail near-miss signal.",
            "- The next automated family is `kickoff_signed_tail_calibration_family`.",
            "- First candidate: `kickoff_signed_tail_probability_triggered_bias_global`.",
            "- Second candidate: `kickoff_signed_tail_probability_triggered_bias_9_16_seg_local`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "KICKOFF_TAILCAL_FAMILY_PREPARED"
    state["current_branch"] = "kickoff_tailcal_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the kickoff tail-calibration family summary",
        "instantiate the first kickoff tail-calibration experiment",
        "continue automated execution in the kickoff tail-calibration branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_TAILCAL_FAMILY_PREPARED`\n"
        "- Current branch state: `kickoff_tailcal_family_manifest_ready`\n"
        f"- Kickoff tail-cal family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
