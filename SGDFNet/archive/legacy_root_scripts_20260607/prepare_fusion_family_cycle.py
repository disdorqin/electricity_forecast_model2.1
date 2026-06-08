from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
CAL_DIR = PROJECT_ROOT / "reports" / "signed_tail_calibration_family_cycle"
CAL_RESULTS = CAL_DIR / "signed_tail_calibration_experiment_results.csv"
FUSION_DIR = PROJECT_ROOT / "reports" / "fusion_family_cycle"
MANIFEST_JSON = FUSION_DIR / "fusion_family_manifest.json"
SUMMARY_MD = FUSION_DIR / "fusion_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Fusion Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE" or state.get("current_branch") != "signed_tail_calibration_family_candidate_pool_exhausted":
        raise ValueError("Fusion family prep is only allowed from SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE / signed_tail_calibration_family_candidate_pool_exhausted.")
    if not CAL_RESULTS.exists():
        raise FileNotFoundError("signed_tail_calibration_experiment_results.csv is required before fusion family prep.")

    results = pd.read_csv(CAL_RESULTS)
    best_cal = results.sort_values(["full_year_rt_capped_smape", "segment_9_16_rt_capped_smape"]).iloc[0].to_dict()

    FUSION_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(FUSION_DIR / "signed_tail_calibration_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Fusion Family Summary\n\n"
        "- Source state: `SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE / signed_tail_calibration_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best accepted point-repair branch: `{best_cal['experiment_id']}` with "
        f"`full_year_rt_capped_smape={best_cal['full_year_rt_capped_smape']:.4f}` and "
        f"`segment_9_16_rt_capped_smape={best_cal['segment_9_16_rt_capped_smape']:.4f}`.\n"
        "- New family decision: unify the accepted signed-tail point repair with the accepted interval module into a release-style fusion package.\n"
        "- Reason:\n"
        "  - the current automation has produced one accepted point-repair branch and one accepted interval branch\n"
        "  - they should be evaluated as a unified candidate rather than left as disconnected artifacts\n"
        "  - the next falsifiable step is whether the bundle preserves both the point gains and uncertainty outputs cleanly\n"
        "- First candidates:\n"
        "  - `signed_tail_point_plus_interval_bundle`\n"
        "  - `signed_tail_point_plus_interval_bundle_with_tailflag`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(CAL_RESULTS.resolve()),
        "next_family": "fusion_family",
        "recommended_first_candidate": "signed_tail_point_plus_interval_bundle",
        "recommended_second_candidate": "signed_tail_point_plus_interval_bundle_with_tailflag",
        "outputs": [
            "fusion_family_summary.md",
            "signed_tail_calibration_results_snapshot.csv"
        ]
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Fusion Family",
            "",
            "- Signed-tail calibration produced the first accepted post-landing autonomous point-repair branch.",
            "- The next automated family is `fusion_family`.",
            "- First candidate: `signed_tail_point_plus_interval_bundle`.",
            "- Second candidate: `signed_tail_point_plus_interval_bundle_with_tailflag`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "FUSION_FAMILY_PREPARED"
    state["current_branch"] = "fusion_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the fusion family summary",
        "instantiate the first fusion candidate",
        "continue automated execution in the fusion branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FUSION_FAMILY_PREPARED`\n"
        "- Current branch state: `fusion_family_manifest_ready`\n"
        f"- Fusion family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
