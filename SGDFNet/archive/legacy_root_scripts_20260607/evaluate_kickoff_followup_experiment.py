from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
import sys

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.metrics import build_metrics_frame, build_segment_metrics, build_tail_metrics


STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
KFOLLOW_DIR = PROJECT_ROOT / "reports" / "kickoff_followup_cycle"
RESULTS_CSV = KFOLLOW_DIR / "kickoff_followup_experiment_results.csv"
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


def _load_prediction_summary(artifact_dir: Path) -> dict[str, float]:
    df = pd.read_csv(artifact_dir / "predictions.csv")
    test_df = df[df["split"] == "test"].copy()
    summary = build_metrics_frame(test_df)
    segment_metrics = build_segment_metrics(test_df)
    tail_metrics = build_tail_metrics(test_df)
    for _, row in segment_metrics.iterrows():
        segment = row["segment"]
        summary[f"segment_{segment}_rt_smape"] = float(row["rt_smape"])
        summary[f"segment_{segment}_rt_capped_smape"] = float(row["rt_capped_smape"])
    for _, row in tail_metrics.iterrows():
        key = int(round((1.0 - float(row["tail_quantile"])) * 100))
        summary[f"top{key}_tail_delta_mae"] = float(row["tail_delta_mae"])
        summary[f"top{key}_tail_rt_smape"] = float(row["tail_rt_smape"])
        summary[f"top{key}_tail_direction_accuracy"] = float(row["tail_direction_accuracy"])
    return summary


def _ensure_results_csv() -> None:
    if not RESULTS_CSV.exists():
        with RESULTS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDS)
            writer.writeheader()


def _load_rows() -> list[dict[str, str]]:
    if not RESULTS_CSV.exists():
        return []
    with RESULTS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {(k.lstrip("\ufeff") if isinstance(k, str) else k): v for k, v in row.items()}
            rows.append(cleaned)
        return rows


def _write_rows(rows: list[dict[str, object]]) -> None:
    with RESULTS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "KICKOFF_FOLLOWUP_EXPERIMENT_RAN" or state.get("current_branch") != "kickoff_followup_experiment_run_complete":
        raise ValueError("Kickoff follow-up evaluation is only allowed from KICKOFF_FOLLOWUP_EXPERIMENT_RAN.")

    instance_dir = Path(state["active_kickoff_followup_instance_dir"])
    manifest_path = instance_dir / "manifest.json"
    manifest = _load_json(manifest_path)
    baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    baseline_summary = _load_prediction_summary(baseline_artifact)
    candidate_summary = _load_prediction_summary(candidate_artifact)

    overall_delta = candidate_summary["rt_smape"] - baseline_summary["rt_smape"]
    seg916_delta = candidate_summary["segment_9_16_rt_smape"] - baseline_summary["segment_9_16_rt_smape"]
    capped_delta = candidate_summary["rt_capped_smape"] - baseline_summary["rt_capped_smape"]
    seg916_capped_delta = candidate_summary["segment_9_16_rt_capped_smape"] - baseline_summary["segment_9_16_rt_capped_smape"]
    top10_delta = candidate_summary["top10_tail_delta_mae"] - baseline_summary["top10_tail_delta_mae"]

    if (overall_delta <= -0.03 and seg916_delta <= -0.10) or (seg916_delta <= -0.25 and capped_delta <= 0.10):
        decision = "KEEP"
        next_action = "expand this kickoff follow-up family with the next controlled time-frequency variant"
    else:
        decision = "REJECT"
        next_action = "continue only if another fresh kickoff follow-up factor remains; otherwise package as negative evidence"

    reason = (
        f"overall_rt_smape_delta={overall_delta:.4f}; "
        f"segment_9_16_rt_smape_delta={seg916_delta:.4f}; "
        f"overall_rt_capped_smape_delta={capped_delta:.4f}; "
        f"segment_9_16_rt_capped_smape_delta={seg916_capped_delta:.4f}; "
        f"top10_tail_delta_mae_delta={top10_delta:.4f}"
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
        "# Kickoff Follow-Up Experiment Decision\n\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n"
        f"- Next action: `{next_action}`\n",
        encoding="utf-8",
    )

    _ensure_results_csv()
    row = {
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
    rows = [existing for existing in _load_rows() if existing.get("experiment_id") != manifest["experiment_id"]]
    rows.append(row)
    _write_rows(rows)

    state["current_stage"] = "KICKOFF_FOLLOWUP_EXPERIMENT_EVALUATED"
    state["current_branch"] = "kickoff_followup_experiment_decision_complete"
    state["last_kickoff_followup_decision"] = decision
    state["allowed_next_actions"] = [
        "review the kickoff follow-up decision",
        "instantiate the next kickoff follow-up candidate if needed",
        "or package the kickoff follow-up evidence if the family is exhausted",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `KICKOFF_FOLLOWUP_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `kickoff_followup_experiment_decision_complete`\n"
        f"- Active kickoff follow-up experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
