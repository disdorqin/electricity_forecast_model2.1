from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
INSTANCE_MANIFEST = PROJECT_ROOT / "reports" / "first_experiment_instance" / "first_experiment_instance_manifest.json"
FRESH_LEDGER_DIR = PROJECT_ROOT / "reports" / "fresh_cycle"
FRESH_LEDGER_PATH = FRESH_LEDGER_DIR / "fresh_cycle_ledger.csv"
DECISION_PATH = FRESH_LEDGER_DIR / "first_experiment_decision.json"
DECISION_MD_PATH = FRESH_LEDGER_DIR / "first_experiment_decision.md"
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
    FRESH_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    if not FRESH_LEDGER_PATH.exists():
        with FRESH_LEDGER_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
            writer.writeheader()


def _load_ledger_rows() -> list[dict[str, str]]:
    if not FRESH_LEDGER_PATH.exists():
        return []
    with FRESH_LEDGER_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {(k.lstrip("\ufeff") if isinstance(k, str) else k): v for k, v in row.items()}
            rows.append(cleaned)
        return rows


def _write_ledger_rows(rows: list[dict[str, object]]) -> None:
    with FRESH_LEDGER_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "FIRST_EXPERIMENT_RAN" or state.get("current_branch") != "first_experiment_run_complete":
        raise ValueError("First experiment evaluation is only allowed from FIRST_EXPERIMENT_RAN / first_experiment_run_complete.")
    manifest = _load_json(INSTANCE_MANIFEST)
    if manifest.get("instance_status") != "executed":
        raise ValueError("First experiment instance must be executed before evaluation.")

    baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    baseline_summary = _load_json(baseline_artifact / "full_year_summary.json")
    candidate_summary = _load_json(candidate_artifact / "full_year_summary.json")

    overall_delta = candidate_summary["rt_smape"] - baseline_summary["rt_smape"]
    seg916_delta = candidate_summary["segment_9_16_rt_smape"] - baseline_summary["segment_9_16_rt_smape"]
    capped_delta = candidate_summary["rt_capped_smape"] - baseline_summary["rt_capped_smape"]
    seg916_capped_delta = candidate_summary["segment_9_16_rt_capped_smape"] - baseline_summary["segment_9_16_rt_capped_smape"]
    top10_delta = candidate_summary["top10_tail_delta_mae"] - baseline_summary["top10_tail_delta_mae"]

    if overall_delta < -0.02 and seg916_delta <= 0.0:
        decision = "KEEP"
        next_action = "use this first experiment as the new fresh-cycle reference and schedule a second one-main-factor variant"
    elif overall_delta > 0.15 or seg916_delta > 0.20:
        decision = "REJECT"
        next_action = "switch to a different fresh-cycle factor and do not micro-tune this exact variant"
    else:
        decision = "SWITCH"
        next_action = "treat this as weak evidence and move to a different one-main-factor branch in the fresh cycle"

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
        "hypothesis": "stronger point-signal redesign for 9_16 raw error",
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
    rows = [
        existing
        for existing in _load_ledger_rows()
        if existing.get("experiment_id") != manifest["experiment_id"]
    ]
    rows.append(row)
    _write_ledger_rows(rows)

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "baseline_summary": baseline_summary,
        "candidate_summary": candidate_summary,
        "next_action": next_action,
    }
    _write_json(DECISION_PATH, decision_payload)
    DECISION_MD_PATH.write_text(
        "# First Experiment Decision\n\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n"
        f"- Next action: `{next_action}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "FIRST_EXPERIMENT_EVALUATED"
    state["current_branch"] = "first_experiment_decision_complete"
    state["allowed_next_actions"] = [
        "review fresh-cycle ledger and first decision",
        "launch the next one-main-factor experiment according to the decision",
        "promote the result if it is a KEEP",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FIRST_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `first_experiment_decision_complete`\n"
        f"- Decision: `{decision}`\n"
        f"- Fresh-cycle ledger: `{FRESH_LEDGER_PATH.resolve()}`\n",
        encoding="utf-8",
    )

    print(str(DECISION_PATH.resolve()))


if __name__ == "__main__":
    main()
