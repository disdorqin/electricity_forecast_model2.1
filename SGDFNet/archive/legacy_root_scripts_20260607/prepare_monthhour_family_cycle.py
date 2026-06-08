from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
NEXT_FAMILY_DIR = PROJECT_ROOT / "reports" / "next_family_cycle"
NEXT_FAMILY_RESULTS = NEXT_FAMILY_DIR / "next_family_experiment_results.csv"
MONTHHOUR_DIR = PROJECT_ROOT / "reports" / "monthhour_family_cycle"
MANIFEST_JSON = MONTHHOUR_DIR / "monthhour_family_cycle_manifest.json"
SUMMARY_MD = MONTHHOUR_DIR / "monthhour_family_cycle_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_memory(section: str) -> None:
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    marker = "## Month-Hour Family"
    if marker in memory:
        prefix = memory.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "NEXT_FAMILY_CYCLE_COMPLETE" or state.get("current_branch") != "next_family_candidate_pool_exhausted":
        raise ValueError("Month-hour family prep is only allowed from NEXT_FAMILY_CYCLE_COMPLETE / next_family_candidate_pool_exhausted.")
    if not NEXT_FAMILY_RESULTS.exists():
        raise FileNotFoundError("next_family_experiment_results.csv is required before month-hour family prep.")

    results = pd.read_csv(NEXT_FAMILY_RESULTS)
    best_row = results.sort_values(["segment_9_16_rt_capped_smape", "top10_tail_delta_mae"]).iloc[0].to_dict()

    MONTHHOUR_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(MONTHHOUR_DIR / "next_family_results_snapshot.csv", index=False, encoding="utf-8-sig")

    summary = (
        "# Month-Hour Family Cycle Summary\n\n"
        "- Source state: `NEXT_FAMILY_CYCLE_COMPLETE / next_family_candidate_pool_exhausted`\n"
        f"- Frozen baseline artifact: `{state['frozen_execution_baseline_artifact']}`\n"
        f"- Best previous localized-calibration candidate by capped/tail balance: `{best_row['experiment_id']}` with "
        f"`segment_9_16_rt_capped_smape={best_row['segment_9_16_rt_capped_smape']:.4f}`, "
        f"`top10_tail_delta_mae={best_row['top10_tail_delta_mae']:.4f}`.\n"
        "- New family decision: move from pure hour-level repair to month-hour structured repair on top of TF+pressure.\n"
        "- Reason:\n"
        "  - previous hour-level and segment-hour-level variants were effectively equivalent on the restricted 9_16 calibration scope\n"
        "  - the next non-isomorphic question is whether season/month-bucket hour structure captures unresolved month-hour concentration\n"
        "  - this stays leakage-safe and still fits the one-main-factor discipline\n"
        "- First candidates:\n"
        "  - `month_hour_bias_risk_extended_on_tf_pressure`\n"
        "  - `month_hour_bias_risk_extended_on_tf_pressure_recent14`\n"
    )
    SUMMARY_MD.write_text(summary, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "source_stage": state["current_stage"],
        "source_branch": state["current_branch"],
        "frozen_baseline_artifact": state["frozen_execution_baseline_artifact"],
        "previous_family_results": str(NEXT_FAMILY_RESULTS.resolve()),
        "next_family": "tf_pressure_month_hour_calibration",
        "recommended_first_candidate": "month_hour_bias_risk_extended_on_tf_pressure",
        "recommended_second_candidate": "month_hour_bias_risk_extended_on_tf_pressure_recent14",
        "outputs": [
            "monthhour_family_cycle_summary.md",
            "next_family_results_snapshot.csv",
        ],
    }
    _write_json(MANIFEST_JSON, manifest)

    section = "\n".join(
        [
            "## Month-Hour Family",
            "",
            "- The localized hour family is exhausted and structurally degenerate under 9_16-only calibration.",
            "- The next automated family is `tf_pressure_month_hour_calibration`.",
            "- First candidate: `month_hour_bias_risk_extended_on_tf_pressure`.",
            "- Second candidate: `month_hour_bias_risk_extended_on_tf_pressure_recent14`.",
            "",
        ]
    )
    _append_memory(section)

    state["current_stage"] = "MONTHHOUR_FAMILY_PREPARED"
    state["current_branch"] = "monthhour_family_manifest_ready"
    state["allowed_next_actions"] = [
        "review the month-hour family summary",
        "instantiate the first month-hour candidate",
        "continue automated execution in the new family",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `MONTHHOUR_FAMILY_PREPARED`\n"
        "- Current branch state: `monthhour_family_manifest_ready`\n"
        f"- Month-hour family manifest: `{MANIFEST_JSON.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(MANIFEST_JSON.resolve()))


if __name__ == "__main__":
    main()
