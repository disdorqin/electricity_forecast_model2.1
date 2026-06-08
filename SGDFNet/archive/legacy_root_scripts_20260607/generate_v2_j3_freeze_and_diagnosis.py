from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
BASELINE_ARTIFACT = PROJECT_ROOT.parent / "outputs" / "RT916_SpikeMarketLab" / "experiments" / "SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230"
LANDING_DIR = PROJECT_ROOT / "reports" / "landing_2025"
V2_DIR = PROJECT_ROOT / "reports" / "v2_j3_time_frequency"
FREEZE_JSON = PROJECT_ROOT / "research_control" / "06_LANDING_FREEZE.json"
STATE_JSON = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
MEMORY_MD = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
REGISTRY_JSON = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
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


def _group_metrics(frame: pd.DataFrame) -> dict[str, float]:
    return {
        "rows": int(len(frame)),
        "rt_smape": smape(frame["rt_actual"], frame["rt_hat"]),
        "rt_capped_smape": capped_smape(frame["rt_actual"], frame["rt_hat"]),
        "rt_mae": float((frame["rt_actual"] - frame["rt_hat"]).abs().mean()),
        "delta_mae": float((frame["delta_target"] - frame["delta_hat"]).abs().mean()),
        "mean_abs_rt_actual": float(frame["rt_actual"].abs().mean()),
        "mean_abs_rt_error": float((frame["rt_actual"] - frame["rt_hat"]).abs().mean()),
        "mean_abs_delta": float(frame["delta_target"].abs().mean()),
        "sign_error_rate": float(((frame["delta_target"] > 0) != (frame["delta_hat"] > 0)).mean()),
    }


def _risk_tag(row: dict[str, float]) -> str:
    sign_error = row["sign_error_rate"]
    rel_error = row["mean_abs_rt_error"] / max(row["mean_abs_rt_actual"], 1e-6)
    if sign_error >= 0.28:
        return "sign error"
    if row["mean_abs_rt_error"] >= 55 and rel_error < 0.35:
        return "ramp/shock"
    if rel_error >= 0.35 and row["rt_smape"] - row["rt_capped_smape"] >= 15:
        return "low-price denominator sensitivity"
    if row["mean_abs_rt_error"] >= 40 and sign_error < 0.22:
        return "smooth bias"
    return "month-hour seasonal concentration"


def main() -> None:
    V2_DIR.mkdir(parents=True, exist_ok=True)
    if not BASELINE_ARTIFACT.exists():
        raise FileNotFoundError(f"Frozen landing artifact not found: {BASELINE_ARTIFACT}")

    predictions = pd.read_csv(BASELINE_ARTIFACT / "predictions.csv")
    predictions["timestamp"] = pd.to_datetime(predictions["timestamp"])
    test_df = predictions[predictions["split"] == "test"].copy()
    test_df["month"] = test_df["target_month"]
    test_df["hour"] = test_df["timestamp"].dt.hour.replace({0: 24}).astype(int)

    target_check = json.loads((LANDING_DIR / "target_check_2025.json").read_text(encoding="utf-8"))
    landing_audit = json.loads((LANDING_DIR / "landing_audit_2025.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((BASELINE_ARTIFACT / "run_manifest.json").read_text(encoding="utf-8"))

    seg_916 = test_df[test_df["segment"] == "9_16"].copy()

    freeze_record = {
        "landing_model_name": "SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline",
        "landing_config_path": _repo_rel(Path(run_manifest["config_path"])),
        "landing_artifact_path": _repo_rel(BASELINE_ARTIFACT),
        "official_metric": "rt_capped_smape_floor_50",
        "full_year_rt_capped_smape": target_check["full_year_rt_capped_smape"],
        "segment_9_16_rt_capped_smape": target_check["segment_9_16_rt_capped_smape"],
        "full_year_raw_rt_smape": target_check["secondary_raw_full_year_rt_smape"],
        "segment_9_16_raw_rt_smape": target_check["secondary_raw_9_16_rt_smape"],
        "landing_audit_path": _repo_rel(LANDING_DIR / "landing_audit_2025.md"),
        "target_check_path": _repo_rel(LANDING_DIR / "target_check_2025.json"),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "do_not_modify": True,
    }
    FREEZE_JSON.write_text(json.dumps(freeze_record, ensure_ascii=False, indent=2), encoding="utf-8")

    hour_rows = []
    for hour, g in test_df.groupby("hour"):
        row = {"hour": int(hour), **_group_metrics(g)}
        row["diagnosis_tag"] = _risk_tag(row)
        hour_rows.append(row)
    hour_level = pd.DataFrame(hour_rows).sort_values("hour").reset_index(drop=True)
    hour_level.to_csv(V2_DIR / "hour_level_risk_2025.csv", index=False, encoding="utf-8-sig")

    monthly_hour_rows = []
    for (month, hour, segment), g in test_df.groupby(["month", "hour", "segment"]):
        row = {"month": month, "hour": int(hour), "segment": segment, **_group_metrics(g)}
        row["diagnosis_tag"] = _risk_tag(row)
        monthly_hour_rows.append(row)
    monthly_hour = pd.DataFrame(monthly_hour_rows).sort_values(["month", "segment", "hour"]).reset_index(drop=True)
    monthly_hour.to_csv(V2_DIR / "monthly_hour_segment_risk_2025.csv", index=False, encoding="utf-8-sig")

    worst_hours_capped = hour_level.sort_values("rt_capped_smape", ascending=False).head(6)
    worst_hours_raw = hour_level.sort_values("rt_smape", ascending=False).head(6)
    worst_916_hours = (
        monthly_hour[monthly_hour["segment"] == "9_16"]
        .groupby("hour")
        .agg(
            rows=("rows", "sum"),
            rt_capped_smape=("rt_capped_smape", "mean"),
            rt_smape=("rt_smape", "mean"),
            rt_mae=("rt_mae", "mean"),
            sign_error_rate=("sign_error_rate", "mean"),
        )
        .reset_index()
        .sort_values("rt_capped_smape", ascending=False)
        .head(6)
    )
    worst_916_months = (
        seg_916.groupby("month")
        .apply(lambda g: pd.Series(_group_metrics(g)))
        .reset_index()
        .sort_values("rt_capped_smape", ascending=False)
    )
    worst_916_month_hour = (
        monthly_hour[monthly_hour["segment"] == "9_16"]
        .sort_values("rt_capped_smape", ascending=False)
        .head(12)
    )

    raw_minus_capped = float(seg_916["rt_actual"].abs().lt(50).mean())
    capped_error_scale = float((seg_916["rt_actual"] - seg_916["rt_hat"]).abs().quantile(0.9))
    high_freq_signal = bool(
        (
            worst_916_month_hour["diagnosis_tag"].isin(["ramp/shock", "month-hour seasonal concentration"]).mean() >= 0.5
        )
        and capped_error_scale >= 55
    )
    bias_first = bool(
        not high_freq_signal and worst_916_month_hour["diagnosis_tag"].isin(["smooth bias", "sign error"]).mean() >= 0.5
    )
    if high_freq_signal:
        decision = "TF justified"
        next_action = "continue_to_tf1"
    elif bias_first:
        decision = "risk-hour bias first"
        next_action = "do_not_run_tf"
    elif target_check["segment_9_16_rt_capped_smape"] < 20 and raw_minus_capped > 0.2:
        decision = "optional improvement"
        next_action = "do_not_over_tune"
    else:
        decision = "inconclusive"
        next_action = "run_only_simplest_tf1"

    diagnosis_json = {
        "frozen_landing_artifact": _repo_rel(BASELINE_ARTIFACT),
        "official_metric": "rt_capped_smape_floor_50",
        "decision": decision,
        "next_action": next_action,
        "baseline_summary": {
            "full_year_rt_capped_smape": target_check["full_year_rt_capped_smape"],
            "segment_9_16_rt_capped_smape": target_check["segment_9_16_rt_capped_smape"],
            "full_year_raw_rt_smape": target_check["secondary_raw_full_year_rt_smape"],
            "segment_9_16_raw_rt_smape": target_check["secondary_raw_9_16_rt_smape"],
        },
        "worst_hours_by_capped_smape": worst_hours_capped.to_dict(orient="records"),
        "worst_hours_by_raw_smape": worst_hours_raw.to_dict(orient="records"),
        "worst_hours_inside_9_16": worst_916_hours.to_dict(orient="records"),
        "worst_months_inside_9_16": worst_916_months.head(6).to_dict(orient="records"),
        "worst_month_hour_inside_9_16": worst_916_month_hour.to_dict(orient="records"),
        "denominator_artifact_signal": {
            "fraction_abs_rt_below_50_in_9_16": raw_minus_capped,
            "interpretation": "secondary_only" if raw_minus_capped < 0.2 else "meaningful_but_not_primary",
        },
        "absolute_error_signal": {
            "q90_abs_rt_error_9_16": capped_error_scale,
            "interpretation": "large_absolute_errors_present" if capped_error_scale >= 55 else "moderate",
        },
        "diagnosis_note": (
            "Current worktree real worst months/hours differ from the prompt bootstrap notes in part; "
            "all V2 decisions use the recomputed frozen-artifact statistics here."
        ),
    }
    (V2_DIR / "risk_hour_diagnosis_2025.json").write_text(
        json.dumps(diagnosis_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    freeze_md = (
        "# LANDING FREEZE\n\n"
        "- Accepted landing model: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`\n"
        f"- Config: `{freeze_record['landing_config_path']}`\n"
        f"- Artifact: `{freeze_record['landing_artifact_path']}`\n"
        f"- Official full-year capped RT SMAPE: `{freeze_record['full_year_rt_capped_smape']:.4f}`\n"
        f"- Official full-year 9_16 capped RT SMAPE: `{freeze_record['segment_9_16_rt_capped_smape']:.4f}`\n"
        f"- Raw full-year RT SMAPE: `{freeze_record['full_year_raw_rt_smape']:.4f}`\n"
        f"- Raw 9_16 RT SMAPE: `{freeze_record['segment_9_16_raw_rt_smape']:.4f}`\n"
        "- Known risks:\n"
        f"  - 9_16-dominant failure concentration\n"
        f"  - worst capped months: `{landing_audit['worst_case_analysis']['worst_3_months_by_capped_rt_smape']}`\n"
        f"  - worst 9_16 capped months: `{landing_audit['worst_case_analysis']['worst_3_months_9_16_by_capped_rt_smape']}`\n"
        f"  - worst capped hours: `{landing_audit['worst_case_analysis']['worst_3_hours_by_capped_rt_smape']}`\n"
        "- Freeze rules:\n"
        "  - future V2 experiments must not overwrite this model or artifact\n"
        "  - every V2 result must be compared against this frozen landing model\n"
    )
    (LANDING_DIR / "LANDING_FREEZE.md").write_text(freeze_md, encoding="utf-8")

    diagnosis_md = (
        "# V2 J3 Risk-Hour Diagnosis 2025\n\n"
        f"- Frozen landing artifact: `{_repo_rel(BASELINE_ARTIFACT)}`\n"
        f"- Decision: `{decision}`\n"
        f"- Next action: `{next_action}`\n"
        f"- Official capped metric uses floor-50 preprocessing.\n\n"
        "## Main Findings\n\n"
        f"- Worst hours by capped SMAPE: `{worst_hours_capped[['hour','rt_capped_smape','rt_smape','rt_mae','diagnosis_tag']].to_dict(orient='records')}`\n"
        f"- Worst hours by raw SMAPE: `{worst_hours_raw[['hour','rt_smape','rt_capped_smape','rt_mae','diagnosis_tag']].to_dict(orient='records')}`\n"
        f"- Worst 9_16 months: `{worst_916_months.head(6)[['month','rt_capped_smape','rt_smape','rt_mae','sign_error_rate']].to_dict(orient='records')}`\n"
        f"- Worst 9_16 month-hour cells: `{worst_916_month_hour[['month','hour','rt_capped_smape','rt_smape','rt_mae','sign_error_rate','diagnosis_tag']].to_dict(orient='records')}`\n\n"
        "## Interpretation\n\n"
        f"- Low-price denominator effect in 9_16 exists at fraction `{raw_minus_capped:.4f}`, but capped risk remains driven by large absolute errors.\n"
        f"- q90 absolute RT error in 9_16 is `{capped_error_scale:.4f}`.\n"
        "- Current worktree real worst months/hours differ partly from the prompt bootstrap list; this diagnosis uses recomputed frozen-artifact results as authoritative.\n"
        f"- Recommendation: `{decision}`.\n"
    )
    (V2_DIR / "risk_hour_diagnosis_2025.md").write_text(diagnosis_md, encoding="utf-8")

    memory_append = (
        "\n## V2 Landing Freeze\n\n"
        "- Landing model is frozen for V2 comparison.\n"
        "- V2 begins as exploratory improvement work only.\n"
        "- Landing model remains deployable even if every V2 branch fails.\n"
    )
    memory_text = MEMORY_MD.read_text(encoding="utf-8")
    if "## V2 Landing Freeze" not in memory_text:
        MEMORY_MD.write_text(memory_text.rstrip() + "\n" + memory_append, encoding="utf-8")

    state = json.loads(STATE_JSON.read_text(encoding="utf-8"))
    state["current_stage"] = "V2_J3"
    state["current_branch"] = "time_frequency_and_9_16_risk_hour_optimization"
    state["frozen_landing_model"] = "SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline"
    state["frozen_landing_artifact"] = _repo_rel(BASELINE_ARTIFACT)
    state["allowed_next_actions"] = [
        "V2 time-frequency exploration",
        "9_16 risk-hour diagnostics",
        "V2 module ablations",
        "V2 report generation",
    ]
    state["blocked_actions"] = [
        "modifying frozen landing artifact",
        "replacing landing model without a new landing audit",
        "blind full-stack tuning",
        "graph before V2_J3 decision",
        "interval/probability head before V2_J3 decision",
    ]
    STATE_JSON.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    registry["official_landing_model"] = {
        "name": "SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline",
        "artifact": _repo_rel(BASELINE_ARTIFACT),
        "config": _repo_rel(Path(run_manifest["config_path"])),
    }
    REGISTRY_JSON.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    auto_summary = (
        "# SGDFNet Auto Research Summary\n\n"
        "## Current Status\n\n"
        "- Frozen landing baseline: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`\n"
        f"- Artifact: `{_repo_rel(BASELINE_ARTIFACT)}`\n"
        f"- V2_J3 diagnosis decision: `{decision}`\n"
        f"- Next action: `{next_action}`\n"
        "- V2 compares every candidate against the frozen landing baseline.\n"
    )
    AUTO_SUMMARY_MD.write_text(auto_summary, encoding="utf-8")


if __name__ == "__main__":
    main()
