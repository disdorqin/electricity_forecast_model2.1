from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
KTCAL_RESULTS = PROJECT_ROOT / "reports" / "kickoff_tailcal_family_cycle" / "kickoff_tailcal_experiment_results.csv"
KCTCAL_DIR = PROJECT_ROOT / "reports" / "kickoff_conservative_tailcal_family_cycle"
MANIFEST_JSON = KCTCAL_DIR / "kickoff_conservative_tailcal_family_manifest.json"
SUMMARY_MD = KCTCAL_DIR / "kickoff_conservative_tailcal_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Kickoff Conservative Tail Calibration Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if (state.get("current_stage"), state.get("current_branch")) != ("KICKOFF_TAILCAL_FAMILY_COMPLETE", "kickoff_tailcal_family_candidate_pool_exhausted"):
        raise ValueError("Kickoff conservative tail-cal family prep is only allowed after kickoff tail-cal exhaustion.")
    if not KTCAL_RESULTS.exists():
        raise FileNotFoundError("kickoff_tailcal_experiment_results.csv is required before conservative tail-cal family prep.")

    results = pd.read_csv(KTCAL_RESULTS)
    best_nearmiss = results.sort_values(
        ["full_year_rt_capped_smape", "segment_9_16_rt_capped_smape", "top10_tail_rt_capped_smape"],
        ascending=[True, True, True],
    ).iloc[0].to_dict()

    KCTCAL_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(KCTCAL_DIR / "kickoff_tailcal_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Kickoff Conservative Tail Calibration Family Summary\n\n"
        "- Source state: `KICKOFF_TAILCAL_FAMILY_COMPLETE / kickoff_tailcal_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best kickoff tail-cal near-miss: `{best_nearmiss['experiment_id']}` with "
        f"`full_year_rt_capped_smape={best_nearmiss['full_year_rt_capped_smape']:.4f}`, "
        f"`segment_9_16_rt_capped_smape={best_nearmiss['segment_9_16_rt_capped_smape']:.4f}`, and "
        f"`top10_tail_rt_capped_smape={best_nearmiss['top10_tail_rt_capped_smape']:.4f}`.\n"
        "- New family decision: keep the same kickoff near-miss baseline, but force a stricter trigger and shrunken bias to test whether raw damage came from over-correction rather than wrong direction.\n"
        "- First candidates:\n"
        "  - `kickoff_conservative_signed_tail_global_shrinked`\n"
        "  - `kickoff_conservative_signed_tail_916_shrinked`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "kickoff_tailcal_results": str(KTCAL_RESULTS.resolve()),
        "kickoff_nearmiss_baseline_artifact": best_nearmiss["point_baseline_artifact"],
        "next_family": "kickoff_conservative_signed_tail_calibration_family",
        "recommended_first_candidate": "kickoff_conservative_signed_tail_global_shrinked",
        "recommended_second_candidate": "kickoff_conservative_signed_tail_916_shrinked",
        "outputs": [
            "kickoff_conservative_tailcal_family_summary.md",
            "kickoff_tailcal_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Kickoff Conservative Tail Calibration Family",
            "",
            "- Kickoff tail-calibration still improved capped and tail metrics, but the raw damage suggests over-correction.",
            "- The next automated family is `kickoff_conservative_signed_tail_calibration_family`.",
            "- First candidate: `kickoff_conservative_signed_tail_global_shrinked`.",
            "- Second candidate: `kickoff_conservative_signed_tail_916_shrinked`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "KICKOFF_CONSERVATIVE_TAILCAL_FAMILY_PREPARED"
    state["current_branch"] = "kickoff_conservative_tailcal_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the kickoff conservative tail-calibration family summary",
        "instantiate the first conservative kickoff tail-calibration experiment",
        "continue automated execution in the conservative kickoff tail-calibration branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_CONSERVATIVE_TAILCAL_FAMILY_PREPARED`\n"
        "- Current branch state: `kickoff_conservative_tailcal_family_manifest_ready`\n"
        f"- Kickoff conservative tail-cal family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
