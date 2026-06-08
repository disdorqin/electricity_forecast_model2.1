from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
SIGNED_PROB_DIR = PROJECT_ROOT / "reports" / "signed_tail_probability_family_cycle"
SIGNED_PROB_RESULTS = SIGNED_PROB_DIR / "signed_tail_probability_experiment_results.csv"
CAL_DIR = PROJECT_ROOT / "reports" / "signed_tail_calibration_family_cycle"
MANIFEST_JSON = CAL_DIR / "signed_tail_calibration_family_manifest.json"
SUMMARY_MD = CAL_DIR / "signed_tail_calibration_family_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Signed-Tail Calibration Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "SIGNED_TAIL_PROBABILITY_FAMILY_COMPLETE" or state.get("current_branch") != "signed_tail_probability_family_candidate_pool_exhausted":
        raise ValueError("Signed-tail calibration family prep is only allowed from SIGNED_TAIL_PROBABILITY_FAMILY_COMPLETE / signed_tail_probability_family_candidate_pool_exhausted.")
    if not SIGNED_PROB_RESULTS.exists():
        raise FileNotFoundError("signed_tail_probability_experiment_results.csv is required before signed-tail calibration family prep.")

    results = pd.read_csv(SIGNED_PROB_RESULTS)
    best_signed = results.sort_values(
        ["mean_signed_average_precision", "mean_signed_recall_topk_9_16", "mean_signed_recall_topk"],
        ascending=[False, False, False],
    ).iloc[0].to_dict()

    CAL_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(CAL_DIR / "signed_tail_probability_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Signed-Tail Calibration Family Summary\n\n"
        "- Source state: `SIGNED_TAIL_PROBABILITY_FAMILY_COMPLETE / signed_tail_probability_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best signed-tail probability candidate remained rejected: `{best_signed['experiment_id']}` with "
        f"`mean_signed_average_precision={best_signed['mean_signed_average_precision']:.4f}` and "
        f"`mean_signed_recall_topk_9_16={best_signed['mean_signed_recall_topk_9_16']:.4f}`.\n"
        "- New family decision: convert the signed-tail ranking signal into a leakage-safe point calibration branch.\n"
        "- Reason:\n"
        "  - signed-tail ranking improved relative to the accepted interval module\n"
        "  - the signal was still not strong enough to justify a standalone probability keep\n"
        "  - the next falsifiable step is to use signed-tail probability only as a trigger for val-learned bias correction\n"
        "- First candidates:\n"
        "  - `signed_tail_probability_triggered_bias`\n"
        "  - `signed_tail_probability_triggered_bias_9_16_seg_local`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(SIGNED_PROB_RESULTS.resolve()),
        "next_family": "signed_tail_calibration_family",
        "recommended_first_candidate": "signed_tail_probability_triggered_bias",
        "recommended_second_candidate": "signed_tail_probability_triggered_bias_9_16_seg_local",
        "outputs": [
            "signed_tail_calibration_family_summary.md",
            "signed_tail_probability_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Signed-Tail Calibration Family",
            "",
            "- Signed-tail probability showed the first real positive ranking signal, but not enough for an accepted standalone module.",
            "- The next automated family is `signed_tail_calibration_family`.",
            "- First candidate: `signed_tail_probability_triggered_bias`.",
            "- Second candidate: `signed_tail_probability_triggered_bias_9_16_seg_local`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "SIGNED_TAIL_CALIBRATION_FAMILY_PREPARED"
    state["current_branch"] = "signed_tail_calibration_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the signed-tail calibration family summary",
        "instantiate the first signed-tail calibration candidate",
        "continue automated execution in the signed-tail calibration branch",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `SIGNED_TAIL_CALIBRATION_FAMILY_PREPARED`\n"
        "- Current branch state: `signed_tail_calibration_family_manifest_ready`\n"
        f"- Signed-tail calibration family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
