from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
MONTHHOUR_DIR = PROJECT_ROOT / "reports" / "monthhour_family_cycle"
MONTHHOUR_RESULTS = MONTHHOUR_DIR / "monthhour_family_experiment_results.csv"
ERRORGATE_DIR = PROJECT_ROOT / "reports" / "errorgate_family_cycle"
MANIFEST_JSON = ERRORGATE_DIR / "errorgate_family_cycle_manifest.json"
SUMMARY_MD = ERRORGATE_DIR / "errorgate_family_cycle_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Error-Gate Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "MONTHHOUR_FAMILY_COMPLETE" or state.get("current_branch") != "monthhour_family_candidate_pool_exhausted":
        raise ValueError("Error-gate family prep is only allowed from MONTHHOUR_FAMILY_COMPLETE / monthhour_family_candidate_pool_exhausted.")
    if not MONTHHOUR_RESULTS.exists():
        raise FileNotFoundError("monthhour_family_experiment_results.csv is required before error-gate family prep.")

    results = pd.read_csv(MONTHHOUR_RESULTS)
    best_row = results.sort_values(["segment_9_16_rt_capped_smape", "top10_tail_delta_mae"]).iloc[0].to_dict()

    ERRORGATE_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(ERRORGATE_DIR / "monthhour_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Error-Gate Family Cycle Summary\n\n"
        "- Source state: `MONTHHOUR_FAMILY_COMPLETE / monthhour_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best previous month-hour candidate by capped/tail balance: `{best_row['experiment_id']}` with "
        f"`segment_9_16_rt_capped_smape={best_row['segment_9_16_rt_capped_smape']:.4f}`, "
        f"`top10_tail_delta_mae={best_row['top10_tail_delta_mae']:.4f}`.\n"
        "- New family decision: move from hour/month bucket repairs to validation residual error-gated correction on top of TF+pressure.\n"
        "- Reason:\n"
        "  - hour and month-hour structure improved some capped/tail behavior but did not repair raw 9_16 enough\n"
        "  - the next non-isomorphic lightweight question is whether predicted hard-error windows are a better control signal than time buckets\n"
        "  - this stays release-safe because the gate is learned only from pre-target validation residuals\n"
        "- First candidates:\n"
        "  - `error_gate_bias_on_tf_pressure`\n"
        "  - `combo_error_sign_gate_bias_on_tf_pressure`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(MONTHHOUR_RESULTS.resolve()),
        "next_family": "tf_pressure_error_gate_calibration",
        "recommended_first_candidate": "error_gate_bias_on_tf_pressure",
        "recommended_second_candidate": "combo_error_sign_gate_bias_on_tf_pressure",
        "outputs": [
            "errorgate_family_cycle_summary.md",
            "monthhour_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Error-Gate Family",
            "",
            "- The month-hour family is exhausted and still fails to rescue raw 9_16.",
            "- The next automated family is `tf_pressure_error_gate_calibration`.",
            "- First candidate: `error_gate_bias_on_tf_pressure`.",
            "- Second candidate: `combo_error_sign_gate_bias_on_tf_pressure`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "ERRORGATE_FAMILY_PREPARED"
    state["current_branch"] = "errorgate_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the error-gate family summary",
        "instantiate the first error-gate candidate",
        "continue automated execution in the new family",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `ERRORGATE_FAMILY_PREPARED`\n"
        "- Current branch state: `errorgate_family_manifest_ready`\n"
        f"- Error-gate family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
