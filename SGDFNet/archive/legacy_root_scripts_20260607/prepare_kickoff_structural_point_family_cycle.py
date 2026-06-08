from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
KMHSEL_RESULTS = PROJECT_ROOT / "reports" / "kickoff_monthhour_selective_family_cycle" / "kickoff_monthhour_selective_experiment_results.csv"
KSPOINT_DIR = PROJECT_ROOT / "reports" / "kickoff_structural_point_family_cycle"
MANIFEST_JSON = KSPOINT_DIR / "kickoff_structural_point_family_manifest.json"
SUMMARY_MD = KSPOINT_DIR / "kickoff_structural_point_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Kickoff Structural Point Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if (state.get("current_stage"), state.get("current_branch")) != ("KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_COMPLETE", "kickoff_monthhour_selective_family_candidate_pool_exhausted"):
        raise ValueError("Kickoff structural-point family prep is only allowed after kickoff month-hour selective exhaustion.")
    if not KMHSEL_RESULTS.exists():
        raise FileNotFoundError("kickoff_monthhour_selective_experiment_results.csv is required before structural-point family prep.")

    results = pd.read_csv(KMHSEL_RESULTS)

    KSPOINT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(KSPOINT_DIR / "kickoff_monthhour_selective_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Kickoff Structural Point Family Summary\n\n"
        "- Source state: `KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_COMPLETE / kickoff_monthhour_selective_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Conclusion from the kickoff post-hoc families: capped and tail gains are easy to buy locally, but raw 9_16 remains stubborn.\n"
        "- New family decision: stop local post-fit repair and return to point-signal trunk enhancement.\n"
        "- Chosen base idea:\n"
        "  - reuse the strongest structural near-miss pattern: TF + pressure + static graph + segment-local stats\n"
        "  - add risk-hour weighting inside training instead of outside-model bias repair\n"
        "- First candidates:\n"
        "  - `structural_graph_seglocal_plus_risk_weight`\n"
        "  - `structural_graph_seglocal_plus_risk_and_mild_tail_weight`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "kickoff_monthhour_selective_results": str(KMHSEL_RESULTS.resolve()),
        "next_family": "kickoff_structural_point_family",
        "recommended_first_candidate": "structural_graph_seglocal_plus_risk_weight",
        "recommended_second_candidate": "structural_graph_seglocal_plus_risk_and_mild_tail_weight",
        "outputs": [
            "kickoff_structural_point_family_summary.md",
            "kickoff_monthhour_selective_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Kickoff Structural Point Family",
            "",
            "- The kickoff post-hoc families were exhausted with repeated capped gains but persistent raw regressions.",
            "- The next automated family is `kickoff_structural_point_family`.",
            "- First candidate: `structural_graph_seglocal_plus_risk_weight`.",
            "- Second candidate: `structural_graph_seglocal_plus_risk_and_mild_tail_weight`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "KICKOFF_STRUCTURAL_POINT_FAMILY_PREPARED"
    state["current_branch"] = "kickoff_structural_point_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the kickoff structural-point family summary",
        "instantiate the first kickoff structural-point experiment",
        "continue automated execution in the kickoff structural-point branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_STRUCTURAL_POINT_FAMILY_PREPARED`\n"
        "- Current branch state: `kickoff_structural_point_family_manifest_ready`\n"
        f"- Kickoff structural-point family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
