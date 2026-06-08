from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
import sys

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.metrics import build_metrics_frame, build_segment_metrics, build_tail_metrics


STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
FRESH_CYCLE_DIR = PROJECT_ROOT / "reports" / "fresh_cycle"
LEDGER_PATH = FRESH_CYCLE_DIR / "fresh_cycle_ledger.csv"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"

LEDGER_FIELDS = [
    "experiment_id",
    "timestamp",
    "stage",
    "branch",
    "hypothesis",
    "changed_factor",
    "baseline_artifact",
    "candidate_artifact",
    "protocol",
    "overall_rt_smape",
    "segment_9_16_rt_smape",
    "overall_rt_capped_smape",
    "segment_9_16_rt_capped_smape",
    "top10_tail_delta_mae",
    "top10_tail_rt_smape",
    "direction_accuracy",
    "primary_score_delta",
    "decision",
    "reason",
    "next_action",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_ledger() -> None:
    FRESH_CYCLE_DIR.mkdir(parents=True, exist_ok=True)
    if not LEDGER_PATH.exists():
        with LEDGER_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
            writer.writeheader()


def _load_prediction_summary(artifact_dir: Path) -> dict[str, float]:
    predictions_path = artifact_dir / "predictions.csv"
    if not predictions_path.exists():
        raise FileNotFoundError(f"Missing predictions.csv in {artifact_dir}")
    df = pd.read_csv(predictions_path)
    test_df = df[df["split"] == "test"].copy()
    if test_df.empty:
        raise RuntimeError(f"No test rows found in {predictions_path}")

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
    summary["test_row_count"] = int(len(test_df))
    return summary


def _decide(overall_delta: float, seg916_delta: float, capped_delta: float, seg916_capped_delta: float, tail_delta: float) -> tuple[str, str]:
    if (
        (overall_delta <= -0.05 and seg916_delta <= -0.05)
        or (overall_delta <= 0.0 and seg916_delta <= -0.25)
        or (overall_delta <= -0.10 and seg916_delta <= 0.0)
    ):
        return (
            "KEEP",
            "promote this fresh-cycle factor as the new retained candidate and schedule the next one-main-factor comparison only if needed",
        )
    if overall_delta > 0.15 or seg916_delta > 0.20 or tail_delta > 1.0:
        return (
            "REJECT",
            "switch to a different fresh-cycle factor and avoid micro-tuning this exact mechanism",
        )
    if capped_delta > 0.25 or seg916_capped_delta > 0.50:
        return (
            "REJECT",
            "business-safety capped metrics worsened beyond tolerance; move to a different factor family",
        )
    return (
        "SWITCH",
        "treat the evidence as inconclusive and move to the next one-main-factor candidate",
    )


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "FRESH_CYCLE_EXPERIMENT_RAN" or state.get("current_branch") != "fresh_cycle_experiment_run_complete":
        raise ValueError("Fresh-cycle experiment evaluation is only allowed from FRESH_CYCLE_EXPERIMENT_RAN.")

    instance_dir = Path(state["active_fresh_cycle_instance_dir"])
    manifest_path = instance_dir / "manifest.json"
    manifest = _load_json(manifest_path)
    if manifest.get("instance_status") != "executed":
        raise ValueError("Fresh-cycle instance must be executed before evaluation.")

    baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    baseline_summary = _load_prediction_summary(baseline_artifact)
    candidate_summary = _load_prediction_summary(candidate_artifact)

    overall_delta = candidate_summary["rt_smape"] - baseline_summary["rt_smape"]
    seg916_delta = candidate_summary["segment_9_16_rt_smape"] - baseline_summary["segment_9_16_rt_smape"]
    capped_delta = candidate_summary["rt_capped_smape"] - baseline_summary["rt_capped_smape"]
    seg916_capped_delta = candidate_summary["segment_9_16_rt_capped_smape"] - baseline_summary["segment_9_16_rt_capped_smape"]
    top10_delta = candidate_summary["top10_tail_delta_mae"] - baseline_summary["top10_tail_delta_mae"]

    decision, next_action = _decide(overall_delta, seg916_delta, capped_delta, seg916_capped_delta, top10_delta)
    reason = (
        f"overall_rt_smape_delta={overall_delta:.4f}; "
        f"segment_9_16_rt_smape_delta={seg916_delta:.4f}; "
        f"overall_rt_capped_smape_delta={capped_delta:.4f}; "
        f"segment_9_16_rt_capped_smape_delta={seg916_capped_delta:.4f}; "
        f"top10_tail_delta_mae_delta={top10_delta:.4f}"
    )

    _ensure_ledger()
    row = {
        "experiment_id": manifest["experiment_id"],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stage": manifest["stage"],
        "branch": manifest["branch"],
        "hypothesis": manifest["hypothesis"],
        "changed_factor": manifest["changed_factor"],
        "baseline_artifact": state["frozen_execution_baseline_artifact"],
        "candidate_artifact": manifest["run_artifact"],
        "protocol": state["protocol"],
        "overall_rt_smape": candidate_summary["rt_smape"],
        "segment_9_16_rt_smape": candidate_summary["segment_9_16_rt_smape"],
        "overall_rt_capped_smape": candidate_summary["rt_capped_smape"],
        "segment_9_16_rt_capped_smape": candidate_summary["segment_9_16_rt_capped_smape"],
        "top10_tail_delta_mae": candidate_summary["top10_tail_delta_mae"],
        "top10_tail_rt_smape": candidate_summary["top10_tail_rt_smape"],
        "direction_accuracy": candidate_summary["direction_accuracy"],
        "primary_score_delta": overall_delta,
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
    }
    with LEDGER_PATH.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writerow(row)

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
        "# Fresh-Cycle Experiment Decision\n\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n"
        f"- Next action: `{next_action}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "FRESH_CYCLE_EXPERIMENT_EVALUATED"
    state["current_branch"] = "fresh_cycle_experiment_decision_complete"
    state["last_fresh_cycle_decision"] = decision
    state["allowed_next_actions"] = [
        "review the updated fresh-cycle ledger",
        "instantiate the next candidate if the decision is REJECT or SWITCH",
        "stop and register the retained factor if the decision is KEEP",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FRESH_CYCLE_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `fresh_cycle_experiment_decision_complete`\n"
        f"- Active fresh-cycle experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n"
        f"- Fresh-cycle ledger: `{LEDGER_PATH.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
