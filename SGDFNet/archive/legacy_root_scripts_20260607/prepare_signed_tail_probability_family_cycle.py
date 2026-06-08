from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
TFP_DIR = PROJECT_ROOT / "reports" / "tfpressure_probability_family_cycle"
TFP_RESULTS = TFP_DIR / "tfpressure_probability_experiment_results.csv"
SIGNED_DIR = PROJECT_ROOT / "reports" / "signed_tail_probability_family_cycle"
MANIFEST_JSON = SIGNED_DIR / "signed_tail_probability_family_manifest.json"
SUMMARY_MD = SIGNED_DIR / "signed_tail_probability_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Signed-Tail Probability Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "TFPRESSURE_PROBABILITY_FAMILY_COMPLETE" or state.get("current_branch") != "tfpressure_probability_family_candidate_pool_exhausted":
        raise ValueError("Signed-tail probability family prep is only allowed from TFPRESSURE_PROBABILITY_FAMILY_COMPLETE / tfpressure_probability_family_candidate_pool_exhausted.")
    if not TFP_RESULTS.exists():
        raise FileNotFoundError("tfpressure_probability_experiment_results.csv is required before signed-tail probability family prep.")

    results = pd.read_csv(TFP_RESULTS)
    best_prob = results.sort_values(["mean_spike_average_precision", "mean_spike_recall_topk"], ascending=[False, False]).iloc[0].to_dict()

    SIGNED_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(SIGNED_DIR / "tfpressure_probability_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Signed-Tail Probability Family Summary\n\n"
        "- Source state: `TFPRESSURE_PROBABILITY_FAMILY_COMPLETE / tfpressure_probability_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best TF+pressure probability candidate remained rejected: `{best_prob['experiment_id']}` with "
        f"`mean_spike_average_precision={best_prob['mean_spike_average_precision']:.4f}` and "
        f"`mean_spike_recall_topk={best_prob['mean_spike_recall_topk']:.4f}`.\n"
        "- New family decision: stop reusing unsigned spike probability and test whether sign-aware tail probabilities can exploit the tail-specialist clue from the error-gate branch.\n"
        "- Reason:\n"
        "  - `egfam_002` was bad as a main model but unusually strong on top-tail delta error\n"
        "  - unsigned probability on top of TF+pressure did not beat the accepted interval module\n"
        "  - the next falsifiable question is whether positive/negative tail ranking is the missing probability signal\n"
        "- First candidates:\n"
        "  - `signed_tail_dual_probability`\n"
        "  - `signed_tail_dual_probability_plus_segment_local`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(TFP_RESULTS.resolve()),
        "next_family": "signed_tail_probability_family",
        "recommended_first_candidate": "signed_tail_dual_probability",
        "recommended_second_candidate": "signed_tail_dual_probability_plus_segment_local",
        "outputs": [
            "signed_tail_probability_family_summary.md",
            "tfpressure_probability_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Signed-Tail Probability Family",
            "",
            "- Unsigned TF+pressure probability variants did not beat the accepted interval module.",
            "- The next automated family is `signed_tail_probability_family`.",
            "- First candidate: `signed_tail_dual_probability`.",
            "- Second candidate: `signed_tail_dual_probability_plus_segment_local`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "SIGNED_TAIL_PROBABILITY_FAMILY_PREPARED"
    state["current_branch"] = "signed_tail_probability_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the signed-tail probability family summary",
        "instantiate the first signed-tail candidate",
        "continue automated execution in the signed-tail probability branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `SIGNED_TAIL_PROBABILITY_FAMILY_PREPARED`\n"
        "- Current branch state: `signed_tail_probability_family_manifest_ready`\n"
        f"- Signed-tail probability family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
