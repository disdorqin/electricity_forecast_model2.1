from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
MEMORY_PATH = PROJECT_ROOT / "research_control" / "02_RESEARCH_MEMORY.md"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"
V2_REPORT_DIR = PROJECT_ROOT / "reports" / "v2_continuous"
LEDGER_PATH = V2_REPORT_DIR / "v2_experiment_ledger.csv"
BRANCH_SUMMARY_PATH = V2_REPORT_DIR / "v2_branch_summary.md"
BEST_SUMMARY_PATH = V2_REPORT_DIR / "v2_best_candidate_summary.md"
NEGATIVE_RESULTS_PATH = V2_REPORT_DIR / "v2_negative_results.md"
NEXT_ACTION_PATH = V2_REPORT_DIR / "v2_next_action.md"
FINAL_COMPARISON_PATH = V2_REPORT_DIR / "v2_final_comparison_vs_landing.csv"
NEXT_STAGE_GENERATOR = PROJECT_ROOT / "generate_next_stage_package.py"

BRANCH1_VARIANTS = [
    {
        "branch": "risk_hour_bias",
        "variant": "RHB1_hour_bias",
        "hypothesis": "Validation-learned risk-hour bias can repair stable hour-level drift without touching test-month actuals.",
        "changed_factor": "hour bias calibration on risk hours 9/10/15",
        "config_path": "SGDFNet/configs/v2_branch1_rhb1_hour_bias.yaml",
    },
    {
        "branch": "risk_hour_bias",
        "variant": "RHB1_segment_hour_bias",
        "hypothesis": "9_16 segment-hour residual bias is more localized than plain hour bias.",
        "changed_factor": "segment-hour bias calibration on 9_16 risk hours 9/10/11/14/15",
        "config_path": "SGDFNet/configs/v2_branch1_rhb1_segment_hour_bias.yaml",
    },
    {
        "branch": "risk_hour_bias",
        "variant": "RHB2_month_hour_bias",
        "hypothesis": "Season-hour correction can absorb repeated month-hour concentration in 9_16.",
        "changed_factor": "season-hour bias calibration on extended risk hours",
        "config_path": "SGDFNet/configs/v2_branch1_rhb2_month_hour_bias.yaml",
    },
    {
        "branch": "risk_hour_bias",
        "variant": "RHB3_risk_weight",
        "hypothesis": "Mild risk-hour weighting can improve 9_16 risk cells while preserving full-year capped performance.",
        "changed_factor": "risk-hour weighted objective on 9_16 hours 9/10/15 with secondary 11/14",
        "config_path": "SGDFNet/configs/v2_branch1_rhb3_risk_weight.yaml",
    },
]

BRANCH2_VARIANTS = [
    {
        "branch": "feature_group_graph",
        "variant": "G1_static_graph",
        "hypothesis": "Static feature-group interactions can repair 9_16 risk-hour errors without a backbone swap.",
        "changed_factor": "static feature-group graph features",
        "config_path": "SGDFNet/configs/v2_branch2_g1_static_graph.yaml",
    },
]

BRANCH3_VARIANTS = [
    {
        "branch": "hard_regime_correction",
        "variant": "H1_error_gate_bias",
        "hypothesis": "High predicted-error windows can be corrected with a leakage-safe residual gate learned on validation only.",
        "changed_factor": "validation residual error-gate bias correction",
        "config_path": "SGDFNet/configs/v2_branch3_h1_error_gate_bias.yaml",
    },
    {
        "branch": "hard_regime_correction",
        "variant": "H2_combo_error_sign_gate_bias",
        "hypothesis": "Combining error-gate with predicted sign splits hard cases more cleanly than a single hard-bias map.",
        "changed_factor": "validation residual error-sign combo gate bias correction",
        "config_path": "SGDFNet/configs/v2_branch3_h2_combo_error_sign_gate_bias.yaml",
    },
]

BRANCH4_VARIANTS = [
    {
        "branch": "interval_probability",
        "variant": "P1_quantile_interval",
        "hypothesis": "Leakage-safe quantile intervals can improve uncertainty coverage and hard-sample ranking without breaking point capped performance.",
        "changed_factor": "quantile interval head on frozen baseline feature family",
        "config_path": "SGDFNet/configs/v2_branch4_p1_quantile_interval.yaml",
    },
    {
        "branch": "interval_probability",
        "variant": "P2_spike_probability",
        "hypothesis": "A lightweight spike-probability head can rank hard cases better than the frozen baseline even if point predictions stay fixed.",
        "changed_factor": "spike probability head on frozen baseline feature family",
        "config_path": "SGDFNet/configs/v2_branch4_p2_spike_probability.yaml",
    },
]

LEDGER_FIELDS = [
    "branch",
    "variant",
    "hypothesis",
    "changed_factor",
    "config_path",
    "artifact_path",
    "comparison_against_frozen_baseline",
    "segment_9_16_rt_capped_smape",
    "risk_hour_9_10_15_avg_capped_smape",
    "full_year_rt_capped_smape",
    "segment_9_16_rt_smape",
    "top10_tail_rt_capped_smape",
    "normal_hour_harm_capped_delta",
    "mean_interval_coverage",
    "mean_interval_width",
    "mean_spike_recall_topk",
    "mean_spike_average_precision",
    "mean_interval_brier_proxy",
    "decision",
    "reason",
]


def capped_smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    yt = y_true.where(y_true >= 50, 50)
    yp = y_pred.where(y_pred >= 50, 50)
    return float((200.0 * (yp - yt).abs() / (yt.abs() + yp.abs() + 1e-6)).mean())


def smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float((200.0 * (y_pred - y_true).abs() / (y_true.abs() + y_pred.abs() + 1e-6)).mean())


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.parent.resolve())).replace("/", "\\")
    except ValueError:
        return str(path)


def _normalize_branch_name(branch: str) -> str:
    if branch.startswith("v2_branch_1") or branch == "risk_hour_bias":
        return "risk_hour_bias"
    if branch.startswith("v2_branch_2") or branch == "feature_group_graph":
        return "feature_group_graph"
    if branch.startswith("v2_branch_3") or branch == "hard_regime_correction":
        return "hard_regime_correction"
    if branch.startswith("v2_branch_4") or branch == "interval_probability":
        return "interval_probability"
    if branch.startswith("v2_branch_5") or branch == "fusion_tuning":
        return "fusion_tuning"
    if branch.startswith("v2_complete_"):
        return "complete"
    return branch


def _ensure_report_dir() -> None:
    V2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if not LEDGER_PATH.exists():
        with LEDGER_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=LEDGER_FIELDS,
            )
            writer.writeheader()
    else:
        existing = pd.read_csv(LEDGER_PATH)
        missing = [field for field in LEDGER_FIELDS if field not in existing.columns]
        if missing:
            for field in missing:
                existing[field] = pd.NA
            existing = existing[LEDGER_FIELDS]
            existing.to_csv(LEDGER_PATH, index=False, encoding="utf-8-sig")


def _score_predictions(pred_path: Path) -> dict[str, float]:
    df = pd.read_csv(pred_path)
    df = df[df["split"] == "test"].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour.replace({0: 24}).astype(int)

    seg916 = df[df["segment"] == "9_16"].copy()
    risk = seg916[seg916["hour"].isin([9, 10, 15])].copy()
    non_risk = df[~df["hour"].isin([9, 10, 15])].copy()
    hour_agg = seg916.groupby("hour").apply(lambda g: capped_smape(g["rt_actual"], g["rt_hat"]))
    month_agg = seg916.groupby("target_month").apply(lambda g: capped_smape(g["rt_actual"], g["rt_hat"]))
    top10_threshold = df["delta_target"].abs().quantile(0.9)
    top10 = df[df["delta_target"].abs() >= top10_threshold].copy()

    return {
        "full_year_rt_capped_smape": capped_smape(df["rt_actual"], df["rt_hat"]),
        "segment_9_16_rt_capped_smape": capped_smape(seg916["rt_actual"], seg916["rt_hat"]),
        "full_year_rt_smape": smape(df["rt_actual"], df["rt_hat"]),
        "segment_9_16_rt_smape": smape(seg916["rt_actual"], seg916["rt_hat"]),
        "risk_hour_9_10_15_avg_capped_smape": float(hour_agg.reindex([9, 10, 15]).mean()),
        "hour_9_capped_smape": float(hour_agg.get(9, float("nan"))),
        "hour_10_capped_smape": float(hour_agg.get(10, float("nan"))),
        "hour_15_capped_smape": float(hour_agg.get(15, float("nan"))),
        "worst_month_9_16_capped_smape": float(month_agg.max()),
        "top10_tail_rt_capped_smape": capped_smape(top10["rt_actual"], top10["rt_hat"]),
        "rt_mae": float((df["rt_actual"] - df["rt_hat"]).abs().mean()),
        "delta_mae": float((df["delta_target"] - df["delta_hat"]).abs().mean()),
        "normal_hour_capped_smape": capped_smape(non_risk["rt_actual"], non_risk["rt_hat"]),
    }


def _append_ledger_row(row: dict[str, object]) -> None:
    with LEDGER_PATH.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        normalized = {field: row.get(field, "") for field in LEDGER_FIELDS}
        writer.writerow(normalized)


def _run_variant(config_rel: str) -> Path:
    cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(PROJECT_ROOT.parent / config_rel)]
    completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
    return Path(completed.stdout.strip().splitlines()[-1].strip())


def _run_probability_variant(config_rel: str) -> Path:
    cmd = [sys.executable, str(PROJECT_ROOT / "run_v2_probability.py"), "--config", str(PROJECT_ROOT.parent / config_rel)]
    completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
    return Path(completed.stdout.strip().splitlines()[-1].strip())


def _load_probability_summary(artifact_abs: Path) -> dict[str, float]:
    summary_path = artifact_abs / "probability_summary.json"
    if not summary_path.exists():
        return {}
    raw = _load_json(summary_path)
    return {
        "mean_spike_recall_topk": float(raw.get("mean_spike_recall_topk", float("nan"))),
        "mean_spike_average_precision": float(raw.get("mean_spike_average_precision", float("nan"))),
        "mean_interval_coverage": float(raw.get("mean_interval_coverage", float("nan"))),
        "mean_interval_width": float(raw.get("mean_interval_width", float("nan"))),
        "mean_interval_brier_proxy": float(raw.get("mean_interval_brier_proxy", float("nan"))),
    }


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _update_research_memory(state: dict, registry: dict, baseline_artifact: Path) -> None:
    memory_text = MEMORY_PATH.read_text(encoding="utf-8")
    new_section = [
        "## V2 Continuous Loop",
        "",
        f"- Current V2 branch state: `{state['current_branch']}`.",
        f"- Frozen execution baseline: `{_repo_rel(baseline_artifact)}`.",
    ]
    accepted_interval = registry.get("accepted_interval_module")
    final_candidate = registry.get("final_candidate")
    if accepted_interval is not None:
        new_section.append(
            f"- Accepted interval module: `{accepted_interval['variant']}` at `{accepted_interval['artifact']}`."
        )
    else:
        new_section.append("- Accepted interval module: `none`.")
    if final_candidate is not None:
        new_section.append(f"- Final V2 package decision: `{final_candidate['type']}`.")
    else:
        new_section.append("- Final V2 package decision: `not locked`.")
    new_section.extend(
        [
            "- Branch outcomes under the frozen baseline:",
            "  - `risk_hour_bias`: negative",
            "  - `feature_group_graph`: negative",
            "  - `hard_regime_correction`: negative",
            f"  - `interval_probability`: {'accepted' if accepted_interval is not None else 'not accepted'}",
            "",
        ]
    )
    replacement = "\n".join(new_section)
    marker = "## V2 Continuous Loop"
    if marker in memory_text:
        prefix = memory_text.split(marker, 1)[0].rstrip()
        MEMORY_PATH.write_text(prefix + "\n\n" + replacement + "\n", encoding="utf-8")
    else:
        MEMORY_PATH.write_text(memory_text.rstrip() + "\n\n" + replacement + "\n", encoding="utf-8")


def _evaluate_keep(branch: str, baseline_metrics: dict[str, float], cand: dict[str, float], normal_hour_harm: float) -> tuple[bool, str]:
    delta_overall = cand["full_year_rt_capped_smape"] - baseline_metrics["full_year_rt_capped_smape"]
    delta_916 = cand["segment_9_16_rt_capped_smape"] - baseline_metrics["segment_9_16_rt_capped_smape"]
    improvement = {
        "seg916": baseline_metrics["segment_9_16_rt_capped_smape"] - cand["segment_9_16_rt_capped_smape"],
        "worst_month": baseline_metrics["worst_month_9_16_capped_smape"] - cand["worst_month_9_16_capped_smape"],
        "hour9": baseline_metrics["hour_9_capped_smape"] - cand["hour_9_capped_smape"],
        "hour10": baseline_metrics["hour_10_capped_smape"] - cand["hour_10_capped_smape"],
        "hour15": baseline_metrics["hour_15_capped_smape"] - cand["hour_15_capped_smape"],
        "risk_avg": baseline_metrics["risk_hour_9_10_15_avg_capped_smape"] - cand["risk_hour_9_10_15_avg_capped_smape"],
        "top10": baseline_metrics["top10_tail_rt_capped_smape"] - cand["top10_tail_rt_capped_smape"],
    }
    reason = (
        f"overall_delta={delta_overall:.4f}; seg916_delta={delta_916:.4f}; "
        f"risk_avg_gain={improvement['risk_avg']:.4f}; hour9_gain={improvement['hour9']:.4f}; "
        f"hour10_gain={improvement['hour10']:.4f}; hour15_gain={improvement['hour15']:.4f}; "
        f"worst_month_gain={improvement['worst_month']:.4f}; top10_gain={improvement['top10']:.4f}; "
        f"normal_hour_harm={normal_hour_harm:.4f}"
    )
    base_guard = delta_overall <= 0.25 and delta_916 <= 0.50
    if branch == "risk_hour_bias":
        keep = base_guard and normal_hour_harm <= 0.35 and (
            improvement["seg916"] >= 0.50
            or improvement["worst_month"] >= 1.00
            or improvement["hour9"] >= 1.00
            or improvement["hour10"] >= 1.00
            or improvement["hour15"] >= 1.00
            or improvement["risk_avg"] >= 0.75
        )
    elif branch == "feature_group_graph":
        keep = base_guard and (
            improvement["seg916"] >= 0.50
            or improvement["risk_avg"] >= 0.75
            or improvement["top10"] >= 1.00
        )
    elif branch == "hard_regime_correction":
        keep = base_guard and normal_hour_harm <= 0.35 and (
            improvement["top10"] >= 1.00
            or improvement["seg916"] >= 0.50
            or improvement["worst_month"] >= 1.00
            or improvement["risk_avg"] >= 0.75
        )
    elif branch == "interval_probability":
        keep = False
    else:
        keep = False
    return keep, reason


def _evaluate_probability_keep(
    baseline_metrics: dict[str, float],
    cand_metrics: dict[str, float],
    prob_metrics: dict[str, float],
    normal_hour_harm: float,
) -> tuple[bool, str]:
    delta_overall = cand_metrics["full_year_rt_capped_smape"] - baseline_metrics["full_year_rt_capped_smape"]
    delta_916 = cand_metrics["segment_9_16_rt_capped_smape"] - baseline_metrics["segment_9_16_rt_capped_smape"]
    coverage = prob_metrics.get("mean_interval_coverage", float("nan"))
    ap = prob_metrics.get("mean_spike_average_precision", float("nan"))
    recall_topk = prob_metrics.get("mean_spike_recall_topk", float("nan"))
    brier = prob_metrics.get("mean_interval_brier_proxy", float("nan"))
    width = prob_metrics.get("mean_interval_width", float("nan"))
    keep = (
        delta_overall <= 0.25
        and delta_916 <= 0.50
        and normal_hour_harm <= 0.35
        and (
            (0.72 <= coverage <= 0.92)
            or recall_topk >= 0.45
            or ap >= 0.18
        )
    )
    reason = (
        f"overall_delta={delta_overall:.4f}; seg916_delta={delta_916:.4f}; "
        f"coverage={coverage:.4f}; interval_width={width:.4f}; "
        f"spike_recall_topk={recall_topk:.4f}; spike_average_precision={ap:.4f}; "
        f"interval_brier_proxy={brier:.4f}; normal_hour_harm={normal_hour_harm:.4f}"
    )
    return keep, reason


def _finalize_fusion_stop(state: dict, registry: dict, baseline_artifact: Path) -> None:
    accepted_modules = {
        "accepted_risk_hour_module": registry.get("accepted_risk_hour_module"),
        "accepted_graph_module": registry.get("accepted_graph_module"),
        "accepted_hard_correction": registry.get("accepted_hard_correction"),
        "accepted_interval_module": registry.get("accepted_interval_module"),
    }
    accepted_count = sum(value is not None for value in accepted_modules.values())
    point_module_count = sum(
        value is not None
        for key, value in accepted_modules.items()
        if key != "accepted_interval_module"
    )
    if accepted_count == 0:
        state["current_branch"] = "v2_complete_frozen_landing_remains_final"
        NEXT_ACTION_PATH.write_text(
            "# V2 Next Action\n\n- Final action: `stop V2 continuous loop; all allowed branches were exhausted with no accepted module, so frozen landing remains the final official baseline.`\n",
            encoding="utf-8",
        )
        BRANCH_SUMMARY_PATH.write_text(
            "# V2 Branch Summary\n\n## Branch 5: Fusion and controlled tuning\n\n- No accepted upstream modules were available for fusion. Frozen landing remains final.\n",
            encoding="utf-8",
        )
        BEST_SUMMARY_PATH.write_text(
            "# V2 Best Candidate Summary\n\n- No V2 branch produced an accepted KEEP candidate.\n"
            f"- Frozen landing remains final: `{_repo_rel(baseline_artifact)}`\n",
            encoding="utf-8",
        )
    elif point_module_count == 0 and accepted_modules["accepted_interval_module"] is not None:
        interval_module = accepted_modules["accepted_interval_module"]
        registry["final_candidate"] = {
            "type": "baseline_plus_interval_module",
            "point_baseline_artifact": _repo_rel(baseline_artifact),
            "interval_module": interval_module,
            "decision": "stop_after_branch4",
            "reason": "Only the interval/probability branch produced an accepted module; no accepted point-improving modules remain to fuse."
        }
        _write_json(REGISTRY_PATH, registry)
        state["current_branch"] = "v2_complete_baseline_plus_interval_module"
        NEXT_ACTION_PATH.write_text(
            "# V2 Next Action\n\n- Final action: `stop V2 continuous loop; keep frozen landing as the final point baseline and attach the accepted interval/probability module as the only accepted V2 extension.`\n",
            encoding="utf-8",
        )
        BRANCH_SUMMARY_PATH.write_text(
            "# V2 Branch Summary\n\n## Branch 5: Fusion and controlled tuning\n\n- No accepted point-improving modules were available for fusion.\n- The loop stops with `frozen landing point baseline + accepted interval/probability module`.\n",
            encoding="utf-8",
        )
        BEST_SUMMARY_PATH.write_text(
            "# V2 Best Candidate Summary\n\n"
            "- Final V2 package: `frozen landing point baseline + accepted interval/probability module`\n"
            f"- Point baseline: `{_repo_rel(baseline_artifact)}`\n"
            f"- Accepted interval module: `{interval_module['variant']}`\n"
            f"- Interval artifact: `{interval_module['artifact']}`\n",
            encoding="utf-8",
        )
    else:
        state["current_branch"] = "v2_branch_5_fusion_tuning"
        NEXT_ACTION_PATH.write_text(
            "# V2 Next Action\n\n- Current next action: `enter V2_BRANCH_5 fusion and controlled tuning using only accepted modules.`\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SGDFNet V2 continuous autonomous branch loop.")
    parser.add_argument(
        "--branch",
        default="auto",
        choices=["auto", "risk_hour_bias", "feature_group_graph", "hard_regime_correction", "interval_probability", "fusion_tuning"],
    )
    args = parser.parse_args()

    _ensure_report_dir()
    state = _load_json(STATE_PATH)
    registry = _load_json(REGISTRY_PATH)
    selected_branch = _normalize_branch_name(state.get("current_branch", "")) if args.branch == "auto" else args.branch
    if selected_branch == "complete":
        baseline_artifact = PROJECT_ROOT.parent / state["frozen_landing_artifact"]
        _finalize_fusion_stop(state, registry, baseline_artifact)
        _update_research_memory(state, registry, baseline_artifact)
        next_stage_completed = subprocess.run(
            [sys.executable, str(NEXT_STAGE_GENERATOR)],
            cwd=str(PROJECT_ROOT.parent),
            check=True,
            capture_output=True,
            text=True,
        )
        next_stage_package = next_stage_completed.stdout.strip().splitlines()[-1].strip()
        AUTO_SUMMARY_PATH.write_text(
            "# SGDFNet Auto Research Summary\n\n"
            f"- Frozen execution baseline: `{_repo_rel(baseline_artifact)}`\n"
            f"- Active stage: `V2_CONTINUOUS`\n"
            f"- Current branch state: `{state['current_branch']}`\n"
            "- Continuous loop status: `complete`\n"
            f"- Next stage package: `{next_stage_package}`\n",
            encoding="utf-8",
        )
        state["last_updated"] = str(date.today())
        state["allowed_next_actions"] = [
            "generate paper-package prep from frozen landing plus accepted interval module",
            "review next-stage package",
            "launch the next approved research stage from the generated package",
        ]
        _write_json(STATE_PATH, state)
        print("V2_CONTINUOUS_COMPLETE")
        return

    baseline_artifact = PROJECT_ROOT.parent / state["frozen_landing_artifact"]
    baseline_metrics = _score_predictions(baseline_artifact / "predictions.csv")

    state["current_stage"] = "V2_CONTINUOUS"
    if selected_branch == "risk_hour_bias":
        state["current_branch"] = "v2_branch_1_risk_hour_bias"
    elif selected_branch == "feature_group_graph":
        state["current_branch"] = "v2_branch_2_feature_group_graph"
    elif selected_branch == "hard_regime_correction":
        state["current_branch"] = "v2_branch_3_hard_regime_correction"
    elif selected_branch == "interval_probability":
        state["current_branch"] = "v2_branch_4_interval_probability"
    elif selected_branch == "fusion_tuning":
        state["current_branch"] = "v2_branch_5_fusion_tuning"
    state["frozen_execution_baseline_artifact"] = state["frozen_landing_artifact"]
    state["frozen_execution_baseline_config"] = state["current_best_config"]
    state["branch_order"] = [
        "risk_hour_bias",
        "feature_group_graph",
        "hard_regime_correction",
        "interval_probability",
        "fusion_tuning",
    ]
    state["active_branch_budget"] = {"risk_hour_bias": 4, "feature_group_graph": 3, "hard_regime_correction": 4, "interval_probability": 3, "fusion_tuning": 6}
    state["consecutive_reject_limit"] = {"risk_hour_bias": 2, "feature_group_graph": 2, "hard_regime_correction": 2, "interval_probability": 2, "fusion_tuning": 3}
    state["global_material_worsening_rules"] = {
        "full_year_rt_capped_smape_abs": 0.25,
        "segment_9_16_rt_capped_smape_abs": 0.50,
    }
    state["allowed_next_actions"] = [
        "run risk-hour bias branch",
        "run feature-group graph branch",
        "run interval/probability branch",
        "compare candidate against frozen execution baseline",
        "write V2 branch ledger and reports",
    ]
    state["blocked_actions"] = [
        "modifying frozen landing artifact",
        "silent Protocol B changes",
        "silent metric formula changes",
        "overwriting prior V2 artifacts",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    if selected_branch == "risk_hour_bias":
        specs = BRANCH1_VARIANTS
        branch_title = "Branch 1: Risk-hour bias"
        reject_limit = 2
    elif selected_branch == "feature_group_graph":
        specs = BRANCH2_VARIANTS
        branch_title = "Branch 2: Feature-group graph"
        reject_limit = 2
    elif selected_branch == "hard_regime_correction":
        specs = BRANCH3_VARIANTS
        branch_title = "Branch 3: Hard-regime correction"
        reject_limit = 2
    elif selected_branch == "interval_probability":
        specs = BRANCH4_VARIANTS
        branch_title = "Branch 4: Interval / probability"
        reject_limit = 2
    elif selected_branch == "fusion_tuning":
        specs = []
        branch_title = "Branch 5: Fusion and controlled tuning"
        reject_limit = 3
    else:
        raise ValueError(f"Unsupported branch: {selected_branch}")

    reject_streak = 0
    kept_row = None
    branch_rows = []
    negative_rows = []

    for spec in specs:
        if spec["branch"] == "interval_probability":
            artifact_path = _run_probability_variant(spec["config_path"])
        else:
            artifact_path = _run_variant(spec["config_path"])
        artifact_abs = PROJECT_ROOT.parent / artifact_path
        cand = _score_predictions(artifact_abs / "predictions.csv")
        normal_hour_harm = cand["normal_hour_capped_smape"] - baseline_metrics["normal_hour_capped_smape"]
        prob_metrics = _load_probability_summary(artifact_abs) if spec["branch"] == "interval_probability" else {}
        if spec["branch"] == "interval_probability":
            keep, reason = _evaluate_probability_keep(baseline_metrics, cand, prob_metrics, normal_hour_harm)
        else:
            keep, reason = _evaluate_keep(spec["branch"], baseline_metrics, cand, normal_hour_harm)
        decision = "KEEP" if keep else "REJECT"
        row = {
            "branch": spec["branch"],
            "variant": spec["variant"],
            "hypothesis": spec["hypothesis"],
            "changed_factor": spec["changed_factor"],
            "config_path": spec["config_path"],
            "artifact_path": _repo_rel(artifact_abs),
            "comparison_against_frozen_baseline": _repo_rel(baseline_artifact),
            "segment_9_16_rt_capped_smape": cand["segment_9_16_rt_capped_smape"],
            "risk_hour_9_10_15_avg_capped_smape": cand["risk_hour_9_10_15_avg_capped_smape"],
            "full_year_rt_capped_smape": cand["full_year_rt_capped_smape"],
            "segment_9_16_rt_smape": cand["segment_9_16_rt_smape"],
            "top10_tail_rt_capped_smape": cand["top10_tail_rt_capped_smape"],
            "normal_hour_harm_capped_delta": normal_hour_harm,
            "mean_interval_coverage": prob_metrics.get("mean_interval_coverage", ""),
            "mean_interval_width": prob_metrics.get("mean_interval_width", ""),
            "mean_spike_recall_topk": prob_metrics.get("mean_spike_recall_topk", ""),
            "mean_spike_average_precision": prob_metrics.get("mean_spike_average_precision", ""),
            "mean_interval_brier_proxy": prob_metrics.get("mean_interval_brier_proxy", ""),
            "decision": decision,
            "reason": reason,
        }
        _append_ledger_row(row)
        branch_rows.append({**row, **cand, **prob_metrics})

        if keep and kept_row is None:
            kept_row = {**row, **cand}
            if spec["branch"] == "risk_hour_bias":
                registry["accepted_risk_hour_module"] = {
                    "variant": spec["variant"],
                    "artifact": _repo_rel(artifact_abs),
                    "config": spec["config_path"],
                    "reason": reason,
                }
            elif spec["branch"] == "feature_group_graph":
                registry["accepted_graph_module"] = {
                    "variant": spec["variant"],
                    "artifact": _repo_rel(artifact_abs),
                    "config": spec["config_path"],
                    "reason": reason,
                }
            elif spec["branch"] == "hard_regime_correction":
                registry["accepted_hard_correction"] = {
                    "variant": spec["variant"],
                    "artifact": _repo_rel(artifact_abs),
                    "config": spec["config_path"],
                    "reason": reason,
                }
            elif spec["branch"] == "interval_probability":
                registry["accepted_interval_module"] = {
                    "variant": spec["variant"],
                    "artifact": _repo_rel(artifact_abs),
                    "config": spec["config_path"],
                    "reason": reason,
                }
            _write_json(REGISTRY_PATH, registry)
            reject_streak = 0
            break

        negative_rows.append({**row, **cand})
        reject_streak += 1
        if reject_streak >= reject_limit and spec["variant"] != "RHB3_risk_weight":
            break

    branch_lines = ["# V2 Branch Summary", "", f"## {branch_title}", ""]
    for row in branch_rows:
        branch_lines.append(
            f"- `{row['variant']}` -> `{row['decision']}` | 9_16 capped `{row['segment_9_16_rt_capped_smape']:.4f}` | "
            f"risk 9/10/15 avg `{row['risk_hour_9_10_15_avg_capped_smape']:.4f}` | overall capped `{row['full_year_rt_capped_smape']:.4f}`"
        )
        if row["branch"] == "interval_probability":
            branch_lines.append(
                f"  - probability: coverage `{float(row.get('mean_interval_coverage', float('nan'))):.4f}` | "
                f"spike recall@topk `{float(row.get('mean_spike_recall_topk', float('nan'))):.4f}` | "
                f"spike AP `{float(row.get('mean_spike_average_precision', float('nan'))):.4f}`"
            )
        branch_lines.append(f"  - reason: {row['reason']}")
    BRANCH_SUMMARY_PATH.write_text("\n".join(branch_lines) + "\n", encoding="utf-8")

    if kept_row is not None:
        BEST_SUMMARY_PATH.write_text(
            "# V2 Best Candidate Summary\n\n"
            f"- Best V2 candidate: `{kept_row['variant']}`\n"
            f"- Artifact: `{kept_row['artifact_path']}`\n"
            f"- 9_16 capped SMAPE: `{kept_row['segment_9_16_rt_capped_smape']:.4f}`\n"
            f"- Risk-hour avg capped SMAPE: `{kept_row['risk_hour_9_10_15_avg_capped_smape']:.4f}`\n"
            f"- Full-year capped SMAPE: `{kept_row['full_year_rt_capped_smape']:.4f}`\n",
            encoding="utf-8",
        )
        NEXT_ACTION_PATH.write_text(
            "# V2 Next Action\n\n- Current next action: `evaluate whether further downstream modules are justified, with the current accepted module kept as best V2 branch so far.`\n",
            encoding="utf-8",
        )
        state["current_branch"] = f"v2_{specs[0]['branch']}_keep"
    else:
        BEST_SUMMARY_PATH.write_text(
            "# V2 Best Candidate Summary\n\n- No KEEP candidate has been found yet. Frozen landing remains the best official baseline.\n",
            encoding="utf-8",
        )
        if args.branch == "risk_hour_bias":
            NEXT_ACTION_PATH.write_text(
                "# V2 Next Action\n\n- Current next action: `switch to V2_BRANCH_2 feature-group graph after the negative risk-hour bias branch.`\n",
                encoding="utf-8",
            )
            state["current_branch"] = "v2_branch_2_feature_group_graph"
        elif selected_branch == "feature_group_graph":
            NEXT_ACTION_PATH.write_text(
                "# V2 Next Action\n\n- Current next action: `switch to V2_BRANCH_3 hard-regime correction after the negative feature-group graph branch.`\n",
                encoding="utf-8",
            )
            state["current_branch"] = "v2_branch_3_hard_regime_correction"
        elif selected_branch == "hard_regime_correction":
            NEXT_ACTION_PATH.write_text(
                "# V2 Next Action\n\n- Current next action: `switch to V2_BRANCH_4 interval / probability after the negative hard-regime correction branch.`\n",
                encoding="utf-8",
            )
            state["current_branch"] = "v2_branch_4_interval_probability"
        elif selected_branch == "interval_probability":
            _finalize_fusion_stop(state, registry, baseline_artifact)
        elif selected_branch == "fusion_tuning":
            _finalize_fusion_stop(state, registry, baseline_artifact)

    NEGATIVE_RESULTS_PATH.write_text(
        "# V2 Negative Results\n\n"
        + "\n".join(
            [
                f"- `{row['variant']}` rejected: {row['reason']}"
                for row in negative_rows
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    comp_rows = []
    for name, metrics in [("frozen_landing_baseline", baseline_metrics)] + [
        (row["variant"], row) for row in branch_rows
    ]:
        comp_rows.append(
            {
                "candidate": name,
                "full_year_rt_capped_smape": metrics["full_year_rt_capped_smape"],
                "segment_9_16_rt_capped_smape": metrics["segment_9_16_rt_capped_smape"],
                "risk_hour_9_10_15_avg_capped_smape": metrics["risk_hour_9_10_15_avg_capped_smape"],
                "hour_9_capped_smape": metrics["hour_9_capped_smape"],
                "hour_10_capped_smape": metrics["hour_10_capped_smape"],
                "hour_15_capped_smape": metrics["hour_15_capped_smape"],
                "worst_month_9_16_capped_smape": metrics["worst_month_9_16_capped_smape"],
                "segment_9_16_rt_smape": metrics["segment_9_16_rt_smape"],
                "top10_tail_rt_capped_smape": metrics["top10_tail_rt_capped_smape"],
                "normal_hour_capped_smape": metrics["normal_hour_capped_smape"],
            }
        )
    pd.DataFrame(comp_rows).to_csv(FINAL_COMPARISON_PATH, index=False, encoding="utf-8-sig")

    _update_research_memory(state, registry, baseline_artifact)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{_repo_rel(baseline_artifact)}`\n"
        f"- Active stage: `V2_CONTINUOUS`\n"
        f"- Current branch state: `{state['current_branch']}`\n"
        f"- Latest branch `{selected_branch}` outcome: `{'KEEP' if kept_row is not None else 'NEGATIVE'}`\n",
        encoding="utf-8",
    )

    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)


if __name__ == "__main__":
    main()
