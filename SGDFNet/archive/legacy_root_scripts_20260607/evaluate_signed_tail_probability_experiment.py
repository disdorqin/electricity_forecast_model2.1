from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pandas as pd

from run_v2_continuous import _load_probability_summary, _score_predictions
from run_signed_tail_probability import SignedTailConfig, _load_config, _thresholds

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
import sys
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sgdfnet.data_contract import load_dataset, preprocess_dataframe
from sgdfnet.protocol_b import _month_starts, _prepare_splits


STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
SIGNED_DIR = PROJECT_ROOT / "reports" / "signed_tail_probability_family_cycle"
RESULTS_CSV = SIGNED_DIR / "signed_tail_probability_experiment_results.csv"
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
    "mean_signed_recall_topk",
    "mean_signed_average_precision",
    "mean_signed_recall_topk_9_16",
    "mean_signed_average_precision_9_16",
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


def _safe_ap(labels: pd.Series, scores: pd.Series) -> float:
    if labels.sum() <= 0:
        return float("nan")
    if labels.nunique() < 2:
        return 1.0
    from sklearn.metrics import average_precision_score
    return float(average_precision_score(labels, scores))


def _rank_recall(labels: pd.Series, scores: pd.Series) -> float:
    positives = int(labels.sum())
    if positives <= 0:
        return float("nan")
    top_idx = scores.rank(method="first", ascending=False) <= positives
    return float(labels[top_idx].sum() / positives)


def _signed_scores_for_artifact(
    pred_path: Path,
    raw_frame: pd.DataFrame,
    config: SignedTailConfig,
    mode: str,
) -> dict[str, float]:
    pred_df = pd.read_csv(pred_path)
    pred_df["timestamp"] = pd.to_datetime(pred_df["timestamp"])
    test_df = pred_df[pred_df["split"] == "test"].copy()

    rows = []
    for month_start in _month_starts(config.target_year):
        month_label = month_start.strftime("%Y-%m")
        train_df, _, _ = _prepare_splits(raw_frame, month_start, config.val_days)
        if len(train_df) < config.train_min_rows:
            continue
        pos_threshold, neg_threshold = _thresholds(train_df["delta_target"], config.tail_quantile, config.min_tail_count)
        month_pred = test_df[test_df["target_month"] == month_label].copy()
        if month_pred.empty:
            continue

        if mode == "accepted_interval":
            if "spike_probability" not in month_pred.columns:
                continue
            pos_score = month_pred["spike_probability"] * (month_pred["delta_hat"] > 0).astype(float)
            neg_score = month_pred["spike_probability"] * (month_pred["delta_hat"] < 0).astype(float)
        else:
            pos_score = month_pred["positive_tail_probability"]
            neg_score = month_pred["negative_tail_probability"]

        pos_truth = (month_pred["delta_target"] >= pos_threshold).astype(int)
        neg_truth = (month_pred["delta_target"] <= neg_threshold).astype(int)
        month_pred_916 = month_pred[month_pred["segment"] == "9_16"].copy()
        pos_truth_916 = (month_pred_916["delta_target"] >= pos_threshold).astype(int)
        neg_truth_916 = (month_pred_916["delta_target"] <= neg_threshold).astype(int)

        rows.append(
            {
                "month": month_label,
                "positive_ap": _safe_ap(pos_truth, pos_score),
                "negative_ap": _safe_ap(neg_truth, neg_score),
                "positive_recall_topk": _rank_recall(pos_truth, pos_score),
                "negative_recall_topk": _rank_recall(neg_truth, neg_score),
                "positive_ap_9_16": _safe_ap(pos_truth_916, month_pred_916["positive_tail_probability"] if mode != "accepted_interval" else pos_score.loc[month_pred_916.index]),
                "negative_ap_9_16": _safe_ap(neg_truth_916, month_pred_916["negative_tail_probability"] if mode != "accepted_interval" else neg_score.loc[month_pred_916.index]),
                "positive_recall_topk_9_16": _rank_recall(pos_truth_916, month_pred_916["positive_tail_probability"] if mode != "accepted_interval" else pos_score.loc[month_pred_916.index]),
                "negative_recall_topk_9_16": _rank_recall(neg_truth_916, month_pred_916["negative_tail_probability"] if mode != "accepted_interval" else neg_score.loc[month_pred_916.index]),
            }
        )

    monthly = pd.DataFrame(rows)
    return {
        "mean_signed_average_precision": float(monthly[["positive_ap", "negative_ap"]].mean(axis=1).mean()),
        "mean_signed_recall_topk": float(monthly[["positive_recall_topk", "negative_recall_topk"]].mean(axis=1).mean()),
        "mean_signed_average_precision_9_16": float(monthly[["positive_ap_9_16", "negative_ap_9_16"]].mean(axis=1).mean()),
        "mean_signed_recall_topk_9_16": float(monthly[["positive_recall_topk_9_16", "negative_recall_topk_9_16"]].mean(axis=1).mean()),
    }


def main() -> None:
    state = _load_json(STATE_PATH)
    if state.get("current_stage") != "SIGNED_TAIL_PROBABILITY_EXPERIMENT_RAN" or state.get("current_branch") != "signed_tail_probability_experiment_run_complete":
        raise ValueError("Signed-tail probability family evaluation is only allowed from SIGNED_TAIL_PROBABILITY_EXPERIMENT_RAN.")

    registry = _load_json(REGISTRY_PATH)
    accepted_interval = registry.get("accepted_interval_module")
    if accepted_interval is None:
        raise ValueError("An accepted interval module is required as the comparison anchor for signed-tail probability evaluation.")

    instance_dir = Path(state["active_signed_tail_probability_instance_dir"])
    manifest = _load_json(instance_dir / "manifest.json")
    config = _load_config(manifest["config_path"])
    raw_df = load_dataset(PROJECT_ROOT.parent / config.data_path)
    raw_frame, _ = preprocess_dataframe(raw_df, config.feature_config)

    frozen_baseline_artifact = PROJECT_ROOT.parent / Path(state["frozen_execution_baseline_artifact"].replace("\\", "/"))
    accepted_interval_artifact = PROJECT_ROOT.parent / Path(accepted_interval["artifact"].replace("\\", "/"))
    candidate_artifact = PROJECT_ROOT.parent / Path(manifest["run_artifact"].replace("\\", "/"))

    frozen_point = _score_predictions(frozen_baseline_artifact / "predictions.csv")
    candidate_point = _score_predictions(candidate_artifact / "predictions.csv")
    accepted_signed = _signed_scores_for_artifact(accepted_interval_artifact / "predictions.csv", raw_frame, config, "accepted_interval")
    candidate_signed = _signed_scores_for_artifact(candidate_artifact / "predictions.csv", raw_frame, config, "candidate")

    point_overall_delta = candidate_point["full_year_rt_capped_smape"] - frozen_point["full_year_rt_capped_smape"]
    point_seg_delta = candidate_point["segment_9_16_rt_capped_smape"] - frozen_point["segment_9_16_rt_capped_smape"]
    signed_ap_gain = candidate_signed["mean_signed_average_precision"] - accepted_signed["mean_signed_average_precision"]
    signed_recall_gain = candidate_signed["mean_signed_recall_topk"] - accepted_signed["mean_signed_recall_topk"]
    signed_ap_916_gain = candidate_signed["mean_signed_average_precision_9_16"] - accepted_signed["mean_signed_average_precision_9_16"]
    signed_recall_916_gain = candidate_signed["mean_signed_recall_topk_9_16"] - accepted_signed["mean_signed_recall_topk_9_16"]

    keep = (
        point_overall_delta <= 0.10
        and point_seg_delta <= 0.20
        and (
            signed_ap_gain >= 0.03
            or signed_recall_gain >= 0.04
            or signed_ap_916_gain >= 0.03
            or signed_recall_916_gain >= 0.04
        )
    )
    decision = "KEEP" if keep else "REJECT"
    reason = (
        f"point_overall_capped_delta={point_overall_delta:.4f}; "
        f"point_seg916_capped_delta={point_seg_delta:.4f}; "
        f"signed_ap_gain_vs_interval={signed_ap_gain:.4f}; "
        f"signed_recall_gain_vs_interval={signed_recall_gain:.4f}; "
        f"signed_ap_9_16_gain_vs_interval={signed_ap_916_gain:.4f}; "
        f"signed_recall_9_16_gain_vs_interval={signed_recall_916_gain:.4f}"
    )
    next_action = (
        "try the next signed-tail candidate if one remains, otherwise close this family and stop the current autonomous branch"
        if decision == "REJECT"
        else "package this signed-tail candidate as the current best probability-side tail specialist"
    )

    decision_payload = {
        "generated_on": str(date.today()),
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
        "frozen_point_baseline_metrics": frozen_point,
        "accepted_interval_signed_metrics": accepted_signed,
        "candidate_point_metrics": candidate_point,
        "candidate_signed_tail_metrics": candidate_signed,
    }
    decision_path = instance_dir / "decision.json"
    _write_json(decision_path, decision_payload)
    (instance_dir / "decision.md").write_text(
        "# Signed-Tail Probability Experiment Decision\n\n"
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
                "mean_signed_recall_topk": candidate_signed["mean_signed_recall_topk"],
                "mean_signed_average_precision": candidate_signed["mean_signed_average_precision"],
                "mean_signed_recall_topk_9_16": candidate_signed["mean_signed_recall_topk_9_16"],
                "mean_signed_average_precision_9_16": candidate_signed["mean_signed_average_precision_9_16"],
                "decision": decision,
                "reason": reason,
            }
        )

    summary_md = SIGNED_DIR / "signed_tail_probability_experiment_summary.md"
    summary_md.write_text(
        "# Signed-Tail Probability Experiment Summary\n\n"
        f"- Experiment: `{manifest['experiment_id']}`\n"
        f"- Candidate artifact: `{manifest['run_artifact']}`\n"
        f"- Decision: `{decision}`\n"
        f"- Reason: `{reason}`\n",
        encoding="utf-8",
    )

    state["current_stage"] = "SIGNED_TAIL_PROBABILITY_EXPERIMENT_EVALUATED"
    state["current_branch"] = "signed_tail_probability_experiment_decision_complete"
    state["last_signed_tail_probability_decision"] = decision
    state["allowed_next_actions"] = [
        "review the signed-tail probability decision",
        "promote the family if it is KEEP",
        "or continue to the next candidate if it is REJECT",
    ]
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `SIGNED_TAIL_PROBABILITY_EXPERIMENT_EVALUATED`\n"
        "- Current branch state: `signed_tail_probability_experiment_decision_complete`\n"
        f"- Active signed-tail probability experiment: `{manifest['experiment_id']}`\n"
        f"- Decision: `{decision}`\n",
        encoding="utf-8",
    )

    print(str(decision_path.resolve()))


if __name__ == "__main__":
    main()
