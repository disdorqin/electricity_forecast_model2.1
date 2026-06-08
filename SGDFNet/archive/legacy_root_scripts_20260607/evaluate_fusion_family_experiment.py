from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from run_v2_continuous import _score_predictions, _load_probability_summary


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
FUSION_DIR = PROJECT_ROOT / "reports" / "fusion_family_cycle"
RESULTS_CSV = FUSION_DIR / "fusion_family_experiment_results.csv"
RESULTS_FIELDS = [
    "experiment_id",
    "changed_factor",
    "candidate_artifact",
    "full_year_rt_capped_smape",
    "segment_9_16_rt_capped_smape",
    "full_year_rt_smape",
    "segment_9_16_rt_smape",
    "top10_tail_rt_capped_smape",
    "mean_interval_coverage",
    "mean_spike_average_precision",
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
    if state.get("current_stage") != "FUSION_FAMILY_EXPERIMENT_RAN" or state.get("current_branch") != "fusion_family_experiment_run_complete":
        raise ValueError("Fusion family evaluation is only allowed from FUSION_FAMILY_EXPERIMENT_RAN.")

    registry = _load_json(REGISTRY_PATH)
    accepted_interval = registry.get("accepted_interval_module")
    accepted_signed = registry.get("accepted_signed_tail_calibration")
    if accepted_interval is None or accepted_signed is None:
        raise ValueError("Accepted interval and signed-tail calibration modules are required before fusion evaluation.")

    instance_dir = Path(state["active_fusion_instance_dir"])
    manifest = _load_json(instance_dir / "manifest.json")
    frozen_baseline = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    accepted_interval_artifact = PROJECT_ROOT.parent / Path(accepted_interval["artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    frozen_point = _score_predictions(frozen_baseline / "predictions.csv")
    candidate_point = _score_predictions(candidate_artifact / "predictions.csv")
    accepted_prob = _load_probability_summary(accepted_interval_artifact)
    candidate_prob = _load_probability_summary(candidate_artifact)

    overall_gain = frozen_point["full_year_rt_capped_smape"] - candidate_point["full_year_rt_capped_smape"]
    seg_gain = frozen_point["segment_9_16_rt_capped_smape"] - candidate_point["segment_9_16_rt_capped_smape"]
    tail_gain = frozen_point["top10_tail_rt_capped_smape"] - candidate_point["top10_tail_rt_capped_smape"]
    coverage = candidate_prob.get("mean_interval_coverage", float("nan"))
    spike_ap = candidate_prob.get("mean_spike_average_precision", float("nan"))
    accepted_coverage = accepted_prob.get("mean_interval_coverage", float("nan"))
    accepted_spike_ap = accepted_prob.get("mean_spike_average_precision", float("nan"))

    keep = (
        overall_gain >= 0.03
        and seg_gain >= 0.15
        and tail_gain >= 0.60
        and abs(coverage - accepted_coverage) <= 0.01
        and abs(spike_ap - accepted_spike_ap) <= 0.02
    )
    decision = "KEEP" if keep else "REJECT"
    reason = (
        f"overall_capped_gain={overall_gain:.4f}; "
        f"seg916_capped_gain={seg_gain:.4f}; "
        f"top10_tail_capped_gain={tail_gain:.4f}; "
        f"interval_coverage_delta={coverage - accepted_coverage:.4f}; "
        f"spike_ap_delta={spike_ap - accepted_spike_ap:.4f}"
    )

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "frozen_point_baseline_metrics": frozen_point,
        "candidate_point_metrics": candidate_point,
        "accepted_interval_summary": accepted_prob,
        "candidate_interval_summary": candidate_prob,
    }
    decision_path = instance_dir / "decision.json"
    _write_json(decision_path, decision_payload)
    (instance_dir / "decision.md").write_text(
        "# Fusion Family Experiment Decision\n\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
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
                "full_year_rt_capped_smape": candidate_point["full_year_rt_capped_smape"],
                "segment_9_16_rt_capped_smape": candidate_point["segment_9_16_rt_capped_smape"],
                "full_year_rt_smape": candidate_point["full_year_rt_smape"],
                "segment_9_16_rt_smape": candidate_point["segment_9_16_rt_smape"],
                "top10_tail_rt_capped_smape": candidate_point["top10_tail_rt_capped_smape"],
                "mean_interval_coverage": candidate_prob.get("mean_interval_coverage", ""),
                "mean_spike_average_precision": candidate_prob.get("mean_spike_average_precision", ""),
                "decision": decision,
                "reason": reason,
            }
        )

    summary_md = FUSION_DIR / "fusion_family_experiment_summary.md"
    summary_md.write_text(
        "# Fusion Family Experiment Summary\n\n"
        f"- Experiment: `{manifest['experiment_id']}`\n"
        f"- Candidate artifact: `{manifest['run_artifact']}`\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "FUSION_FAMILY_EXPERIMENT_EVALUATED"
    state["current_branch"] = "fusion_family_experiment_decision_complete"
    state["last_fusion_decision"] = decision
    state["allowed_next_actions"] = [
        "review the fusion family decision",
        "promote the family if it is KEEP",
        "or continue to the next candidate if it is REJECT",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FUSION_FAMILY_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `fusion_family_experiment_decision_complete`\n"
        f"- Active fusion experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
