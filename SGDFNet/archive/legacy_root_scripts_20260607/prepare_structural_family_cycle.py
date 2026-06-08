from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
ERRORGATE_DIR = PROJECT_ROOT / "reports" / "errorgate_family_cycle"
ERRORGATE_RESULTS = ERRORGATE_DIR / "errorgate_family_experiment_results.csv"
STRUCTURAL_DIR = PROJECT_ROOT / "reports" / "structural_family_cycle"
MANIFEST_JSON = STRUCTURAL_DIR / "structural_family_cycle_manifest.json"
SUMMARY_MD = STRUCTURAL_DIR / "structural_family_cycle_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Structural Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "ERRORGATE_FAMILY_COMPLETE" or state.get("current_branch") != "errorgate_family_candidate_pool_exhausted":
        raise ValueError("Structural family prep is only allowed from ERRORGATE_FAMILY_COMPLETE / errorgate_family_candidate_pool_exhausted.")
    if not ERRORGATE_RESULTS.exists():
        raise FileNotFoundError("errorgate_family_experiment_results.csv is required before structural family prep.")

    results = pd.read_csv(ERRORGATE_RESULTS)
    best_tail = results.sort_values(["top10_tail_delta_mae", "overall_rt_smape"]).iloc[0].to_dict()

    STRUCTURAL_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(STRUCTURAL_DIR / "errorgate_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Structural Family Cycle Summary\n\n"
        "- Source state: `ERRORGATE_FAMILY_COMPLETE / errorgate_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best prior tail specialist (still rejected as main model): `{best_tail['experiment_id']}` with "
        f"`top10_tail_delta_mae={best_tail['top10_tail_delta_mae']:.4f}` and `overall_rt_smape={best_tail['overall_rt_smape']:.4f}`.\n"
        "- New family decision: stop adding lightweight calibration patches and return to the point-signal core with structural feature fusion on top of TF+pressure.\n"
        "- Reason:\n"
        "  - TF+pressure remains the strongest near-miss base for the main objective\n"
        "  - graph-like structural features were negative on the old base, but were never tested on the stronger TF+pressure base\n"
        "  - the next main-model question is whether structural feature interactions improve raw 9_16 without depending on post-fit patching\n"
        "- First candidates:\n"
        "  - `tf_pressure_static_group_graph`\n"
        "  - `tf_pressure_static_group_graph_plus_segment_local`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(ERRORGATE_RESULTS.resolve()),
        "next_family": "tf_pressure_structural_features",
        "recommended_first_candidate": "tf_pressure_static_group_graph",
        "recommended_second_candidate": "tf_pressure_static_group_graph_plus_segment_local",
        "outputs": [
            "structural_family_cycle_summary.md",
            "errorgate_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Structural Family",
            "",
            "- Error-gate patching is exhausted and too destructive for the main objective.",
            "- The next automated family is `tf_pressure_structural_features`.",
            "- First candidate: `tf_pressure_static_group_graph`.",
            "- Second candidate: `tf_pressure_static_group_graph_plus_segment_local`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "STRUCTURAL_FAMILY_PREPARED"
    state["current_branch"] = "structural_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the structural family summary",
        "instantiate the first structural-feature candidate",
        "continue automated execution in the new main-model family",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `STRUCTURAL_FAMILY_PREPARED`\n"
        "- Current branch state: `structural_family_manifest_ready`\n"
        f"- Structural family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
