from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from run_v2_continuous import _score_predictions


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
KCTCAL_DIR = PROJECT_ROOT / "reports" / "kickoff_conservative_tailcal_family_cycle"
RESULTS_CSV = KCTCAL_DIR / "kickoff_conservative_tailcal_experiment_results.csv"
RESULTS_FIELDS = [
    "experiment_id",
    "changed_factor",
    "candidate_artifact",
    "point_baseline_artifact",
    "full_year_rt_capped_smape",
    "segment_9_16_rt_capped_smape",
    "full_year_rt_smape",
    "segment_9_16_rt_smape",
    "top10_tail_rt_capped_smape",
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
    if state.get("current_stage") != "KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_RAN" or state.get("current_branch") != "kickoff_conservative_tailcal_experiment_run_complete":
        raise ValueError("Kickoff conservative tail-calibration evaluation is only allowed from KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_RAN.")

    instance_dir = Path(state["active_kickoff_conservative_tailcal_instance_dir"])
    manifest = _load_json(instance_dir / "manifest.json")
    frozen_baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    frozen_point = _score_predictions(frozen_baseline_artifact / "predictions.csv")
    candidate_point = _score_predictions(candidate_artifact / "predictions.csv")

    overall_gain = frozen_point["full_year_rt_capped_smape"] - candidate_point["full_year_rt_capped_smape"]
    seg_gain = frozen_point["segment_9_16_rt_capped_smape"] - candidate_point["segment_9_16_rt_capped_smape"]
    raw_overall_delta = candidate_point["full_year_rt_smape"] - frozen_point["full_year_rt_smape"]
    raw_seg_delta = candidate_point["segment_9_16_rt_smape"] - frozen_point["segment_9_16_rt_smape"]
    tail_gain = frozen_point["top10_tail_rt_capped_smape"] - candidate_point["top10_tail_rt_capped_smape"]

    keep = (
        overall_gain >= 0.02
        and (seg_gain >= 0.08 or tail_gain >= 0.60)
        and raw_overall_delta <= 0.12
        and raw_seg_delta <= 0.20
    )
    decision = "KEEP" if keep else "REJECT"
    reason = (
        f"overall_capped_gain={overall_gain:.4f}; "
        f"seg916_capped_gain={seg_gain:.4f}; "
        f"top10_tail_capped_gain={tail_gain:.4f}; "
        f"raw_overall_delta={raw_overall_delta:.4f}; "
        f"raw_seg916_delta={raw_seg_delta:.4f}"
    )
    next_action = (
        "try the next conservative kickoff tail-calibration candidate if one remains, otherwise close this family and decide whether to package the near-miss evidence"
        if decision == "REJECT"
        else "package this conservative kickoff tail-calibration candidate as the current best kickoff continuation"
    )

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
        "frozen_point_baseline_metrics": frozen_point,
        "candidate_point_metrics": candidate_point,
    }
    decision_path = instance_dir / "decision.json"
    _write_json(decision_path, decision_payload)
    (instance_dir / "decision.md").write_text(
        "# Conservative Kickoff Tail Calibration Experiment Decision\n\n"
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
                "point_baseline_artifact": manifest["point_probability_baseline_artifact"],
                "full_year_rt_capped_smape": candidate_point["full_year_rt_capped_smape"],
                "segment_9_16_rt_capped_smape": candidate_point["segment_9_16_rt_capped_smape"],
                "full_year_rt_smape": candidate_point["full_year_rt_smape"],
                "segment_9_16_rt_smape": candidate_point["segment_9_16_rt_smape"],
                "top10_tail_rt_capped_smape": candidate_point["top10_tail_rt_capped_smape"],
                "decision": decision,
                "reason": reason,
            }
        )

    summary_md = KCTCAL_DIR / "kickoff_conservative_tailcal_experiment_summary.md"
    summary_md.write_text(
        "# Conservative Kickoff Tail Calibration Experiment Summary\n\n"
        f"- Experiment: `{manifest['experiment_id']}`\n"
        f"- Candidate artifact: `{manifest['run_artifact']}`\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_EVALUATED"
    state["current_branch"] = "kickoff_conservative_tailcal_experiment_decision_complete"
    state["last_kickoff_conservative_tailcal_decision"] = decision
    state["allowed_next_actions"] = [
        "review the conservative kickoff tail-calibration decision",
        "promote the family if it is KEEP",
        "or continue to the next candidate if it is REJECT",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `kickoff_conservative_tailcal_experiment_decision_complete`\n"
        f"- Active conservative kickoff tail-calibration experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
