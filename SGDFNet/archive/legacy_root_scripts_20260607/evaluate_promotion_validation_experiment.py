from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.sgdfnet.metrics import capped_smape, smape, mae


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
PROMO_DIR = PROJECT_ROOT / "reports" / "promotion_validation_family_cycle"
RESULTS_CSV = PROMO_DIR / "promotion_validation_experiment_results.csv"
RESULTS_FIELDS = [
    "experiment_id",
    "changed_factor",
    "candidate_artifact",
    "month",
    "rt_capped_smape",
    "segment_9_16_rt_capped_smape",
    "rt_smape",
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


def _load_results_rows() -> list[dict[str, str]]:
    if not RESULTS_CSV.exists():
        return []
    with RESULTS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {(k.lstrip("\ufeff") if isinstance(k, str) else k): v for k, v in row.items()}
            rows.append(cleaned)
        return rows


def _write_results_rows(rows: list[dict[str, object]]) -> None:
    with RESULTS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _score(df: pd.DataFrame) -> dict[str, float]:
    rt_true = df["rt_actual"].to_numpy(dtype=float)
    rt_pred = df["rt_hat"].to_numpy(dtype=float)
    top10_threshold = float(df["delta_target"].abs().quantile(0.9))
    top10 = df[df["delta_target"].abs() >= top10_threshold].copy()
    seg916 = df[df["segment"] == "9_16"].copy()
    return {
        "rt_capped_smape": capped_smape(rt_true, rt_pred),
        "segment_9_16_rt_capped_smape": capped_smape(seg916["rt_actual"].to_numpy(dtype=float), seg916["rt_hat"].to_numpy(dtype=float)) if not seg916.empty else float("nan"),
        "rt_smape": smape(rt_true, rt_pred),
        "segment_9_16_rt_smape": smape(seg916["rt_actual"].to_numpy(dtype=float), seg916["rt_hat"].to_numpy(dtype=float)) if not seg916.empty else float("nan"),
        "top10_tail_rt_capped_smape": capped_smape(top10["rt_actual"].to_numpy(dtype=float), top10["rt_hat"].to_numpy(dtype=float)) if not top10.empty else float("nan"),
        "rt_mae": mae(rt_true, rt_pred),
    }


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "PROMOTION_VALIDATION_EXPERIMENT_RAN" or state.get("current_branch") != "promotion_validation_experiment_run_complete":
        raise ValueError("Promotion validation evaluation is only allowed from PROMOTION_VALIDATION_EXPERIMENT_RAN.")

    instance_dir = Path(state["active_promotion_validation_instance_dir"])
    manifest = _load_json(instance_dir / "manifest.json")
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))
    pred = pd.read_csv(candidate_artifact / "predictions.csv")

    month = pred["target_month"].iloc[0]
    metrics = _score(pred)
    keep = (
        metrics["rt_capped_smape"] <= 15.0
        and metrics["segment_9_16_rt_capped_smape"] <= 20.0
    )
    decision = "KEEP" if keep else "REJECT"
    reason = (
        f"month={month}; "
        f"rt_capped_smape={metrics['rt_capped_smape']:.4f}; "
        f"seg916_capped_smape={metrics['segment_9_16_rt_capped_smape']:.4f}; "
        f"rt_smape={metrics['rt_smape']:.4f}; "
        f"top10_tail_capped_smape={metrics['top10_tail_rt_capped_smape']:.4f}"
    )

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "metrics": metrics,
    }
    decision_path = instance_dir / "decision.json"
    _write_json(decision_path, decision_payload)
    (instance_dir / "decision.md").write_text(
        "# Promotion Validation Experiment Decision\n\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
        encoding="utf-8",
    )

    _ensure_results_csv()
    result_row = {
        "experiment_id": manifest["experiment_id"],
        "changed_factor": manifest["changed_factor"],
        "candidate_artifact": manifest["run_artifact"],
        "month": month,
        "rt_capped_smape": metrics["rt_capped_smape"],
        "segment_9_16_rt_capped_smape": metrics["segment_9_16_rt_capped_smape"],
        "rt_smape": metrics["rt_smape"],
        "segment_9_16_rt_smape": metrics["segment_9_16_rt_smape"],
        "top10_tail_rt_capped_smape": metrics["top10_tail_rt_capped_smape"],
        "decision": decision,
        "reason": reason,
    }
    rows = [
        row
        for row in _load_results_rows()
        if row.get("experiment_id") != manifest["experiment_id"]
        and row.get("changed_factor") != manifest["changed_factor"]
    ]
    rows.append(result_row)
    _write_results_rows(rows)

    state["current_stage"] = "PROMOTION_VALIDATION_EXPERIMENT_EVALUATED"
    state["current_branch"] = "promotion_validation_experiment_decision_complete"
    state["last_promotion_validation_decision"] = decision
    state["allowed_next_actions"] = [
        "review the promotion validation decision",
        "promote the candidate if it remains strong on 2026",
        "or continue to the next validation candidate if it is weak",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `PROMOTION_VALIDATION_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `promotion_validation_experiment_decision_complete`\n"
        f"- Active promotion validation experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
