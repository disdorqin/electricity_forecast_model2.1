from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
STRUCTURAL_DIR = PROJECT_ROOT / "reports" / "structural_family_cycle"
STRUCTURAL_RESULTS = STRUCTURAL_DIR / "structural_family_experiment_results.csv"
TFP_DIR = PROJECT_ROOT / "reports" / "tfpressure_probability_family_cycle"
MANIFEST_JSON = TFP_DIR / "tfpressure_probability_family_manifest.json"
SUMMARY_MD = TFP_DIR / "tfpressure_probability_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## TF+Pressure Probability Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "STRUCTURAL_FAMILY_COMPLETE" or state.get("current_branch") != "structural_family_candidate_pool_exhausted":
        raise ValueError("TF+pressure probability family prep is only allowed from STRUCTURAL_FAMILY_COMPLETE / structural_family_candidate_pool_exhausted.")
    if not STRUCTURAL_RESULTS.exists():
        raise FileNotFoundError("structural_family_experiment_results.csv is required before TF+pressure probability family prep.")

    results = pd.read_csv(STRUCTURAL_RESULTS)
    best_structural = results.sort_values(["overall_rt_smape", "segment_9_16_rt_smape"]).iloc[0].to_dict()

    TFP_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(TFP_DIR / "structural_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# TF+Pressure Probability Family Summary\n\n"
        "- Source state: `STRUCTURAL_FAMILY_COMPLETE / structural_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best structural candidate remained rejected: `{best_structural['experiment_id']}` with "
        f"`overall_rt_smape={best_structural['overall_rt_smape']:.4f}` and "
        f"`segment_9_16_rt_smape={best_structural['segment_9_16_rt_smape']:.4f}`.\n"
        "- New family decision: stop extending negative point-structure branches and test whether the strongest TF+pressure near-miss base improves probability outputs.\n"
        "- Reason:\n"
        "  - TF+pressure is still the strongest lightweight near-miss for point metrics\n"
        "  - structural fusion stayed negative for the raw 9_16 objective\n"
        "  - the next falsifiable question is whether better uncertainty / spike-ranking emerges on the stronger near-miss base\n"
        "- First candidates:\n"
        "  - `tfpressure_quantile_interval`\n"
        "  - `tfpressure_spike_probability`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(STRUCTURAL_RESULTS.resolve()),
        "next_family": "tfpressure_probability_family",
        "recommended_first_candidate": "tfpressure_quantile_interval",
        "recommended_second_candidate": "tfpressure_spike_probability",
        "outputs": [
            "tfpressure_probability_family_summary.md",
            "structural_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## TF+Pressure Probability Family",
            "",
            "- Structural feature fusion stayed negative for the main raw 9-16 objective.",
            "- The next automated family is `tfpressure_probability_family`.",
            "- First candidate: `tfpressure_quantile_interval`.",
            "- Second candidate: `tfpressure_spike_probability`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "TFPRESSURE_PROBABILITY_FAMILY_PREPARED"
    state["current_branch"] = "tfpressure_probability_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the TF+pressure probability family summary",
        "instantiate the first TF+pressure probability candidate",
        "continue automated execution in the probability-family branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `TFPRESSURE_PROBABILITY_FAMILY_PREPARED`\n"
        "- Current branch state: `tfpressure_probability_family_manifest_ready`\n"
        f"- TF+pressure probability family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
