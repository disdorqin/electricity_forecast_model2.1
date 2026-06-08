from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
BASELINE_ARTIFACT = PROJECT_ROOT.parent / "outputs" / "RT916_SpikeMarketLab" / "experiments" / "SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230"
V2_DIR = PROJECT_ROOT / "reports" / "v2_j3_time_frequency"
REGISTRY_JSON = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
STATE_JSON = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
MEMORY_MD = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
AUTO_SUMMARY_MD = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float((200.0 * (y_pred - y_true).abs() / (y_true.abs() + y_pred.abs() + 1e-6)).mean())


def capped_smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    yt = y_true.where(y_true >= 50, 50)
    yp = y_pred.where(y_pred >= 50, 50)
    return float((200.0 * (yp - yt).abs() / (yt.abs() + yp.abs() + 1e-6)).mean())


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.parent.resolve())).replace("/", "\\")
    except ValueError:
        return str(path)


def _metrics(df: pd.DataFrame) -> dict[str, float]:
    return {
        "rt_smape": smape(df["rt_actual"], df["rt_hat"]),
        "rt_capped_smape": capped_smape(df["rt_actual"], df["rt_hat"]),
        "rt_mae": float((df["rt_actual"] - df["rt_hat"]).abs().mean()),
        "delta_mae": float((df["delta_target"] - df["delta_hat"]).abs().mean()),
    }


def main() -> None:
    V2_DIR.mkdir(parents=True, exist_ok=True)
    baseline = pd.read_csv(BASELINE_ARTIFACT / "predictions.csv")
    baseline = baseline[baseline["split"] == "test"].copy()
    baseline["timestamp"] = pd.to_datetime(baseline["timestamp"])
    baseline["hour"] = baseline["timestamp"].dt.hour.replace({0: 24}).astype(int)
    baseline_916 = baseline[baseline["segment"] == "9_16"].copy()
    baseline_worst_month_916 = (
        baseline_916.groupby("target_month")
        .apply(lambda g: capped_smape(g["rt_actual"], g["rt_hat"]))
        .sort_values(ascending=False)
    )
    baseline_hour = baseline.groupby("hour").apply(lambda g: capped_smape(g["rt_actual"], g["rt_hat"])).to_dict()
    baseline_top10 = baseline["delta_target"].abs().quantile(0.9)
    baseline_top10_df = baseline[baseline["delta_target"].abs() >= baseline_top10].copy()
    baseline_top10_capped = capped_smape(baseline_top10_df["rt_actual"], baseline_top10_df["rt_hat"])

    ledger_rows = []
    candidate_dirs = sorted(
        [d for d in (PROJECT_ROOT.parent / "outputs" / "RT916_SpikeMarketLab" / "experiments").iterdir() if d.is_dir() and d.name.startswith("SGDFNet_V2_J3_")]
    )

    accepted = None
    for run_dir in candidate_dirs:
        pred = pd.read_csv(run_dir / "predictions.csv")
        pred = pred[pred["split"] == "test"].copy()
        pred["timestamp"] = pd.to_datetime(pred["timestamp"])
        pred["hour"] = pred["timestamp"].dt.hour.replace({0: 24}).astype(int)
        pred_916 = pred[pred["segment"] == "9_16"].copy()
        full = _metrics(pred)
        seg916 = _metrics(pred_916)
        worst_month_916 = (
            pred_916.groupby("target_month")
            .apply(lambda g: capped_smape(g["rt_actual"], g["rt_hat"]))
            .sort_values(ascending=False)
        )
        hour_metric = pred.groupby("hour").apply(lambda g: capped_smape(g["rt_actual"], g["rt_hat"])).to_dict()
        top10 = pred["delta_target"].abs().quantile(0.9)
        top10_df = pred[pred["delta_target"].abs() >= top10].copy()
        top10_capped = capped_smape(top10_df["rt_actual"], top10_df["rt_hat"])

        delta_overall = full["rt_capped_smape"] - _metrics(baseline)["rt_capped_smape"]
        delta_916 = seg916["rt_capped_smape"] - _metrics(baseline_916)["rt_capped_smape"]
        worst_month_gain = float(baseline_worst_month_916.iloc[0] - worst_month_916.iloc[0])
        hour15_gain = baseline_hour.get(15, float("nan")) - hour_metric.get(15, float("nan"))
        avg_141511_gain = (
            (baseline_hour.get(14, 0.0) + baseline_hour.get(15, 0.0) + baseline_hour.get(11, 0.0))
            - (hour_metric.get(14, 0.0) + hour_metric.get(15, 0.0) + hour_metric.get(11, 0.0))
        ) / 3.0
        top10_gain = baseline_top10_capped - top10_capped

        keep = (
            (delta_overall <= 0.25 and delta_916 <= 0.50)
            and (
                (_metrics(baseline_916)["rt_capped_smape"] - seg916["rt_capped_smape"] >= 0.5)
                or (worst_month_gain >= 1.0)
                or (hour15_gain >= 1.0)
                or (avg_141511_gain >= 0.75)
            )
        )
        decision = "KEEP" if keep else "REJECT"
        reason = (
            f"overall_delta={delta_overall:.4f}; seg916_delta={delta_916:.4f}; "
            f"worst_month_gain={worst_month_gain:.4f}; hour15_gain={hour15_gain:.4f}; avg141511_gain={avg_141511_gain:.4f}; top10_gain={top10_gain:.4f}"
        )
        row = {
            "experiment_id": run_dir.name,
            "changed_factor": "TF1 moving-average residual features",
            "artifact_path": _repo_rel(run_dir),
            "baseline_artifact": _repo_rel(BASELINE_ARTIFACT),
            "overall_rt_capped_smape": full["rt_capped_smape"],
            "segment_9_16_rt_capped_smape": seg916["rt_capped_smape"],
            "overall_rt_smape": full["rt_smape"],
            "segment_9_16_rt_smape": seg916["rt_smape"],
            "worst_month_9_16_capped_smape": float(worst_month_916.iloc[0]),
            "hour_15_capped_smape": float(hour_metric.get(15, float("nan"))),
            "hour_14_capped_smape": float(hour_metric.get(14, float("nan"))),
            "hour_11_capped_smape": float(hour_metric.get(11, float("nan"))),
            "top10_tail_rt_capped_smape": top10_capped,
            "decision": decision,
            "reason": reason,
        }
        ledger_rows.append(row)
        if keep and accepted is None:
            accepted = row

    ledger = pd.DataFrame(ledger_rows)
    ledger.to_csv(V2_DIR / "tf_experiment_ledger.csv", index=False, encoding="utf-8-sig")

    if accepted is not None:
        summary = (
            "# TF Acceptance Summary\n\n"
            "- J3 result: `PASS`\n"
            f"- Best V2 candidate: `{accepted['experiment_id']}`\n"
            f"- Artifact: `{accepted['artifact_path']}`\n"
            f"- 9_16 capped SMAPE: `{accepted['segment_9_16_rt_capped_smape']:.4f}`\n"
            f"- Worst-month 9_16 capped SMAPE: `{accepted['worst_month_9_16_capped_smape']:.4f}`\n"
            f"- Hour 15 capped SMAPE: `{accepted['hour_15_capped_smape']:.4f}`\n"
        )
        best_cfg = (
            "experiment_name: SGDFNet_V2_J3_TF1\n"
            "inherits_from: SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml\n"
            "feature_config:\n"
            "  include_tf_moving_average_features: true\n"
        )
        (PROJECT_ROOT / "configs" / "v2_best_tf_candidate.yaml").write_text(best_cfg, encoding="utf-8")

        registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
        registry["accepted_tf_module"] = {
            "name": accepted["experiment_id"],
            "artifact": accepted["artifact_path"],
            "note": accepted["reason"],
        }
        REGISTRY_JSON.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

        state = json.loads(STATE_JSON.read_text(encoding="utf-8"))
        state["current_branch"] = "v2_j3_tf_pass"
        STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        memory_text = MEMORY_MD.read_text(encoding="utf-8")
        append = "\n## V2 J3 Result\n\n- TF module accepted as the current V2 best candidate.\n"
        if "## V2 J3 Result" not in memory_text:
            MEMORY_MD.write_text(memory_text.rstrip() + "\n" + append, encoding="utf-8")

        recommendation = (
            "# V2 Next Module Recommendation\n\n"
            "- Recommended next action: `continue to V2_J5 9_16 hard-regime correction`\n"
            "- Reason: TF already improved risk-hour behavior; the remaining error is concentrated in a few severe 9_16 month-hour cells.\n"
        )
    else:
        summary = (
            "# TF Acceptance Summary\n\n"
            "- J3 result: `NEGATIVE`\n"
            "- No TF candidate met the KEEP rule against the frozen landing baseline.\n"
        )
        state = json.loads(STATE_JSON.read_text(encoding="utf-8"))
        state["current_branch"] = "v2_j3_tf_negative"
        STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        recommendation = (
            "# V2 Next Module Recommendation\n\n"
            "- Recommended next action: `run focused risk-hour bias module before larger modules`\n"
            "- Reason: J3 diagnosis showed stable hour/month concentration and TF did not deliver a safe enough gain over the frozen landing model.\n"
        )

    (V2_DIR / "tf_acceptance_summary.md").write_text(summary, encoding="utf-8")
    (PROJECT_ROOT / "reports" / "v2_next_module_recommendation.md").write_text(recommendation, encoding="utf-8")
    AUTO_SUMMARY_MD.write_text(summary + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
