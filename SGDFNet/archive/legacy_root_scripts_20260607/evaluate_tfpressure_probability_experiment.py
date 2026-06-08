from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pandas as pd

from run_v2_continuous import _load_probability_summary, _score_predictions


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
TFP_DIR = PROJECT_ROOT / "reports" / "tfpressure_probability_family_cycle"
RESULTS_CSV = TFP_DIR / "tfpressure_probability_experiment_results.csv"
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
    "mean_interval_coverage",
    "mean_interval_width",
    "mean_spike_recall_topk",
    "mean_spike_average_precision",
    "mean_interval_brier_proxy",
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
    if state.get("current_stage") != "TFPRESSURE_PROBABILITY_EXPERIMENT_RAN" or state.get("current_branch") != "tfpressure_probability_experiment_run_complete":
        raise ValueError("TF+pressure probability family evaluation is only allowed from TFPRESSURE_PROBABILITY_EXPERIMENT_RAN.")

    registry = _load_json(REGISTRY_PATH)
    accepted_interval = registry.get("accepted_interval_module")
    if accepted_interval is None:
        raise ValueError("An accepted interval module is required as the comparison anchor for TF+pressure probability evaluation.")

    instance_dir = Path(state["active_tfpressure_probability_instance_dir"])
    manifest = _load_json(instance_dir / "manifest.json")
    frozen_baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    comparison_probability_artifact = PROJECT_ROOT.parent / Path(accepted_interval["artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    frozen_point = _score_predictions(frozen_baseline_artifact / "predictions.csv")
    candidate_point = _score_predictions(candidate_artifact / "predictions.csv")
    accepted_prob = _load_probability_summary(comparison_probability_artifact)
    candidate_prob = _load_probability_summary(candidate_artifact)

    point_overall_delta = candidate_point["full_year_rt_capped_smape"] - frozen_point["full_year_rt_capped_smape"]
    point_seg_delta = candidate_point["segment_9_16_rt_capped_smape"] - frozen_point["segment_9_16_rt_capped_smape"]
    coverage_gain = candidate_prob.get("mean_interval_coverage", float("nan")) - accepted_prob.get("mean_interval_coverage", float("nan"))
    ap_gain = candidate_prob.get("mean_spike_average_precision", float("nan")) - accepted_prob.get("mean_spike_average_precision", float("nan"))
    recall_gain = candidate_prob.get("mean_spike_recall_topk", float("nan")) - accepted_prob.get("mean_spike_recall_topk", float("nan"))
    brier_gain = accepted_prob.get("mean_interval_brier_proxy", float("nan")) - candidate_prob.get("mean_interval_brier_proxy", float("nan"))

    keep = (
        point_overall_delta <= 0.10
        and point_seg_delta <= 0.20
        and (
            coverage_gain >= 0.02
            or ap_gain >= 0.02
            or recall_gain >= 0.03
            or brier_gain >= 0.005
        )
    )
    decision = "KEEP" if keep else "REJECT"
    reason = (
        f"point_overall_capped_delta={point_overall_delta:.4f}; "
        f"point_seg916_capped_delta={point_seg_delta:.4f}; "
        f"coverage_gain_vs_accepted_interval={coverage_gain:.4f}; "
        f"ap_gain_vs_accepted_interval={ap_gain:.4f}; "
        f"recall_gain_vs_accepted_interval={recall_gain:.4f}; "
        f"brier_proxy_gain_vs_accepted_interval={brier_gain:.4f}"
    )
    next_action = (
        "try the next TF+pressure probability candidate if one remains, otherwise close this family and stop the current autonomous branch"
        if decision == "REJECT"
        else "package this TF+pressure probability candidate as the current best probability-side extension"
    )

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
        "frozen_point_baseline_metrics": frozen_point,
        "accepted_interval_summary": accepted_prob,
        "candidate_point_metrics": candidate_point,
        "candidate_probability_summary": candidate_prob,
    }
    decision_path = instance_dir / "decision.json"
    _write_json(decision_path, decision_payload)
    (instance_dir / "decision.md").write_text(
        "# TF+Pressure Probability Experiment Decision\n\n"
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
                "mean_interval_coverage": candidate_prob.get("mean_interval_coverage", pd.NA),
                "mean_interval_width": candidate_prob.get("mean_interval_width", pd.NA),
                "mean_spike_recall_topk": candidate_prob.get("mean_spike_recall_topk", pd.NA),
                "mean_spike_average_precision": candidate_prob.get("mean_spike_average_precision", pd.NA),
                "mean_interval_brier_proxy": candidate_prob.get("mean_interval_brier_proxy", pd.NA),
                "decision": decision,
                "reason": reason,
            }
        )

    summary_md = TFP_DIR / "tfpressure_probability_experiment_summary.md"
    summary_md.write_text(
        "# TF+Pressure Probability Experiment Summary\n\n"
        f"- Experiment: `{manifest['experiment_id']}`\n"
        f"- Candidate artifact: `{manifest['run_artifact']}`\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "TFPRESSURE_PROBABILITY_EXPERIMENT_EVALUATED"
    state["current_branch"] = "tfpressure_probability_experiment_decision_complete"
    state["last_tfpressure_probability_decision"] = decision
    state["allowed_next_actions"] = [
        "review the TF+pressure probability decision",
        "promote the family if it is KEEP",
        "or continue to the next candidate if it is REJECT",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `TFPRESSURE_PROBABILITY_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `tfpressure_probability_experiment_decision_complete`\n"
        f"- Active TF+pressure probability experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
