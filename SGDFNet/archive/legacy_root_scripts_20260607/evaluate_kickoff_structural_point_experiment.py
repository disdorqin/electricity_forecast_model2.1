from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
KSPOINT_DIR = PROJECT_ROOT / "reports" / "kickoff_structural_point_family_cycle"
RESULTS_CSV = KSPOINT_DIR / "kickoff_structural_point_experiment_results.csv"
RESULTS_FIELDS = [
    "experiment_id",
    "changed_factor",
    "candidate_artifact",
    "overall_rt_smape",
    "segment_9_16_rt_smape",
    "overall_rt_capped_smape",
    "segment_9_16_rt_capped_smape",
    "top10_tail_delta_mae",
    "top10_tail_rt_smape",
    "direction_accuracy",
    "decision",
    "reason",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_results_csv() -> None:
    if not RESULTS_CSV.exists():
        with RESULTS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDS)
            writer.writeheader()


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "KICKOFF_STRUCTURAL_POINT_EXPERIMENT_RAN" or state.get("current_branch") != "kickoff_structural_point_experiment_run_complete":
        raise ValueError("Kickoff structural-point evaluation is only allowed from KICKOFF_STRUCTURAL_POINT_EXPERIMENT_RAN.")

    instance_dir = Path(state["active_kickoff_structural_point_instance_dir"])
    manifest = _load_json(instance_dir / "manifest.json")
    frozen_baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    baseline_summary = _load_json(frozen_baseline_artifact / "full_year_summary.json")
    candidate_summary = _load_json(candidate_artifact / "full_year_summary.json")

    overall_rt_smape_delta = float(candidate_summary["rt_smape"] - baseline_summary["rt_smape"])
    segment_9_16_rt_smape_delta = float(candidate_summary["segment_9_16_rt_smape"] - baseline_summary["segment_9_16_rt_smape"])
    overall_rt_capped_smape_delta = float(candidate_summary["rt_capped_smape"] - baseline_summary["rt_capped_smape"])
    segment_9_16_rt_capped_smape_delta = float(candidate_summary["segment_9_16_rt_capped_smape"] - baseline_summary["segment_9_16_rt_capped_smape"])
    top10_tail_delta_mae_delta = float(candidate_summary["top10_tail_delta_mae"] - baseline_summary["top10_tail_delta_mae"])

    keep = (
        overall_rt_smape_delta <= 0.10
        and segment_9_16_rt_smape_delta <= 0.00
        and overall_rt_capped_smape_delta <= 0.05
        and segment_9_16_rt_capped_smape_delta <= 0.00
    ) or (
        overall_rt_smape_delta <= 0.15
        and segment_9_16_rt_smape_delta <= 0.10
        and overall_rt_capped_smape_delta <= 0.00
        and segment_9_16_rt_capped_smape_delta <= -0.10
        and top10_tail_delta_mae_delta <= 0.0
    )
    decision = "KEEP" if keep else "REJECT"
    reason = (
        f"overall_rt_smape_delta={overall_rt_smape_delta:.4f}; "
        f"segment_9_16_rt_smape_delta={segment_9_16_rt_smape_delta:.4f}; "
        f"overall_rt_capped_smape_delta={overall_rt_capped_smape_delta:.4f}; "
        f"segment_9_16_rt_capped_smape_delta={segment_9_16_rt_capped_smape_delta:.4f}; "
        f"top10_tail_delta_mae_delta={top10_tail_delta_mae_delta:.4f}"
    )
    next_action = (
        "try the next kickoff structural-point candidate if one remains, otherwise close this family and decide whether to package the evidence"
        if decision == "REJECT"
        else "package this kickoff structural-point candidate as the current best point-signal continuation"
    )

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "baseline_summary_recomputed_from_predictions": baseline_summary,
        "candidate_summary_recomputed_from_predictions": candidate_summary,
        "next_action": next_action,
    }
    decision_path = instance_dir / "decision.json"
    _write_json(decision_path, decision_payload)
    (instance_dir / "decision.md").write_text(
        "# Kickoff Structural Point Experiment Decision\n\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n"
        f"- Next action: `{next_action}`\n",
        encoding="utf-8",
    )

    _ensure_results_csv()
    with RESULTS_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDS)
        writer.writerow(
            {
                "experiment_id": manifest["experiment_id"],
                "changed_factor": manifest["changed_factor"],
                "candidate_artifact": manifest["run_artifact"],
                "overall_rt_smape": candidate_summary["rt_smape"],
                "segment_9_16_rt_smape": candidate_summary["segment_9_16_rt_smape"],
                "overall_rt_capped_smape": candidate_summary["rt_capped_smape"],
                "segment_9_16_rt_capped_smape": candidate_summary["segment_9_16_rt_capped_smape"],
                "top10_tail_delta_mae": candidate_summary["top10_tail_delta_mae"],
                "top10_tail_rt_smape": candidate_summary["top10_tail_rt_smape"],
                "direction_accuracy": candidate_summary["direction_accuracy"],
                "decision": decision,
                "reason": reason,
            }
        )

    summary_md = KSPOINT_DIR / "kickoff_structural_point_experiment_summary.md"
    summary_md.write_text(
        "# Kickoff Structural Point Experiment Summary\n\n"
        f"- Experiment: `{manifest['experiment_id']}`\n"
        f"- Candidate artifact: `{manifest['run_artifact']}`\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "KICKOFF_STRUCTURAL_POINT_EXPERIMENT_EVALUATED"
    state["current_branch"] = "kickoff_structural_point_experiment_decision_complete"
    state["last_kickoff_structural_point_decision"] = decision
    state["allowed_next_actions"] = [
        "review the kickoff structural-point decision",
        "promote the family if it is KEEP",
        "or continue to the next candidate if it is REJECT",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_STRUCTURAL_POINT_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `kickoff_structural_point_experiment_decision_complete`\n"
        f"- Active kickoff structural-point experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
