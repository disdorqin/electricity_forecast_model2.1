from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
REGISTRY_PATH = PROJECT_ROOT / "research_control" / "05_BEST_MODEL_REGISTRY.json"
PACKAGE_DEFAULT = PROJECT_ROOT / "reports" / "next_stage_package" / "next_stage_package.json"
J8_DIR = PROJECT_ROOT / "reports" / "j8_package"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(rel_path: str) -> Path:
    return PROJECT_ROOT.parent / Path(rel_path.replace("\\", "/"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_best_model_card(package: dict, registry: dict, landing_target: dict, probability_summary: dict) -> str:
    lines = [
        "# Best Model Card",
        "",
        f"- Package type: `{package['package_type']}`",
        f"- Point model: `{registry['official_landing_model']['name']}`",
        f"- Point artifact: `{package['point_baseline_artifact']}`",
        f"- Point config: `{package['point_baseline_config']}`",
        f"- Official full-year capped RT SMAPE: `{landing_target['full_year_rt_capped_smape']:.4f}`",
        f"- Official 9_16 capped RT SMAPE: `{landing_target['segment_9_16_rt_capped_smape']:.4f}`",
        f"- Secondary raw full-year RT SMAPE: `{landing_target['secondary_raw_full_year_rt_smape']:.4f}`",
        f"- Secondary raw 9_16 RT SMAPE: `{landing_target['secondary_raw_9_16_rt_smape']:.4f}`",
        "",
        "## Interval Extension",
        "",
        f"- Module: `{package['accepted_interval_module']['variant']}`",
        f"- Interval artifact: `{package['accepted_interval_module']['artifact']}`",
        f"- Mean interval coverage: `{probability_summary['mean_interval_coverage']:.4f}`",
        f"- Mean spike recall@topk: `{probability_summary['mean_spike_recall_topk']:.4f}`",
        f"- Mean spike average precision: `{probability_summary['mean_spike_average_precision']:.4f}`",
        f"- Mean interval width: `{probability_summary['mean_interval_width']:.4f}`",
        "",
        "## Claim Boundary",
        "",
        "- This package claims a stable point baseline plus an accepted interval/probability extension.",
        "- It does not claim point-metric improvement from the interval-only module.",
    ]
    promo = package.get("promotion_validation")
    if promo:
        lines.extend(
            [
                "",
                "## Promotion Validation",
                "",
                f"- Fresh validated month: `{promo['validated_month']}`",
                f"- Fusion-bundle promotion artifact: `{promo['fusion_bundle_artifact']}`",
                f"- Point-only control artifact: `{promo['point_only_control_artifact']}`",
                f"- Promotion RT capped SMAPE: `{promo['rt_capped_smape']:.4f}`",
                f"- Promotion 9_16 capped SMAPE: `{promo['segment_9_16_rt_capped_smape']:.4f}`",
                f"- Promotion decision: `{promo['decision']}`",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SGDFNet J8 paper package from the next-stage package.")
    parser.add_argument("--package", default=str(PACKAGE_DEFAULT))
    args = parser.parse_args()

    package_path = Path(args.package)
    package = _load_json(package_path)
    if package.get("status") != "ready" or package.get("recommended_stage") != "J8":
        raise ValueError("Next-stage package is not ready for J8 execution.")

    state = _load_json(STATE_PATH)
    registry = _load_json(REGISTRY_PATH)

    landing_target = _load_json(PROJECT_ROOT / "reports" / "landing_2025" / "target_check_2025.json")
    landing_audit = (PROJECT_ROOT / "reports" / "landing_2025" / "landing_audit_2025.md").read_text(encoding="utf-8")
    best_landing_summary = (PROJECT_ROOT / "reports" / "landing_2025" / "best_model_landing_summary.md").read_text(encoding="utf-8")
    monthly_overall = pd.read_csv(PROJECT_ROOT / "reports" / "landing_2025" / "monthly_overall_smape_2025.csv")
    monthly_segment = pd.read_csv(PROJECT_ROOT / "reports" / "landing_2025" / "monthly_segment_smape_2025.csv")
    v2_ledger = pd.read_csv(PROJECT_ROOT / "reports" / "v2_continuous" / "v2_experiment_ledger.csv")
    v2_negative = (PROJECT_ROOT / "reports" / "v2_continuous" / "v2_negative_results.md").read_text(encoding="utf-8")
    interval_artifact = _repo_path(package["accepted_interval_module"]["artifact"])
    probability_summary = _load_json(interval_artifact / "probability_summary.json")
    probability_monthly = pd.read_csv(interval_artifact / "probability_monthly_summary.csv")
    promotion_validation = package.get("promotion_validation")

    J8_DIR.mkdir(parents=True, exist_ok=True)

    merged = monthly_overall.merge(
        probability_monthly,
        left_on="month",
        right_on="month",
        how="left",
    )
    merged.to_csv(J8_DIR / "full_2025_point_interval_summary.csv", index=False, encoding="utf-8-sig")

    seg916 = monthly_segment[monthly_segment["segment_name"] == "9_16"].copy()
    seg916 = seg916.merge(probability_monthly[["month", "interval_coverage", "spike_recall_topk", "spike_average_precision"]], on="month", how="left")
    seg916.to_csv(J8_DIR / "segment_9_16_point_interval_summary.csv", index=False, encoding="utf-8-sig")

    coverage_summary = pd.DataFrame(
        [
            {
                "mean_interval_coverage": probability_summary["mean_interval_coverage"],
                "mean_interval_width": probability_summary["mean_interval_width"],
                "mean_spike_recall_topk": probability_summary["mean_spike_recall_topk"],
                "mean_spike_average_precision": probability_summary["mean_spike_average_precision"],
                "mean_interval_brier_proxy": probability_summary["mean_interval_brier_proxy"],
            }
        ]
    )
    coverage_summary.to_csv(J8_DIR / "coverage_calibration_summary.csv", index=False, encoding="utf-8-sig")

    negative_table = v2_ledger[v2_ledger["decision"] == "REJECT"].copy()
    negative_table.to_csv(J8_DIR / "negative_results_table.csv", index=False, encoding="utf-8-sig")

    (J8_DIR / "negative_results_summary.md").write_text(v2_negative, encoding="utf-8")
    (J8_DIR / "landing_audit_snapshot.md").write_text(landing_audit, encoding="utf-8")
    (J8_DIR / "best_model_landing_snapshot.md").write_text(best_landing_summary, encoding="utf-8")
    (J8_DIR / "best_model_card.md").write_text(
        _build_best_model_card(package, registry, landing_target, probability_summary),
        encoding="utf-8",
    )
    if promotion_validation:
        pd.DataFrame([promotion_validation]).to_csv(J8_DIR / "promotion_validation_summary.csv", index=False, encoding="utf-8-sig")

    package_manifest = {
        "generated_on": str(date.today()),
        "source_next_stage_package": str(package_path.resolve()),
        "point_baseline_artifact": package["point_baseline_artifact"],
        "interval_artifact": package["accepted_interval_module"]["artifact"],
        "outputs": [
            "full_2025_point_interval_summary.csv",
            "segment_9_16_point_interval_summary.csv",
            "coverage_calibration_summary.csv",
            "negative_results_table.csv",
            "negative_results_summary.md",
            "landing_audit_snapshot.md",
            "best_model_landing_snapshot.md",
            "best_model_card.md",
            "promotion_validation_summary.csv",
        ],
        "j8_status": "complete",
    }
    _write_json(J8_DIR / "j8_package_manifest.json", package_manifest)

    (J8_DIR / "README.md").write_text(
        "# J8 Package\n\n"
        "- This package is the automated J8 paper-package prep output.\n"
        "- It combines the frozen landing point baseline with the accepted interval/probability extension.\n"
        "- Point-metric claims come from the frozen landing audit.\n"
        "- Interval claims come from the accepted V2 probability artifact.\n",
        encoding="utf-8",
    )

    state["current_stage"] = "J8"
    state["current_branch"] = "j8_package_complete"
    state["allowed_next_actions"] = [
        "review J8 package outputs",
        "export paper-ready tables",
        "start a new research branch after J8 review",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{package['point_baseline_artifact']}`\n"
        "- Active stage: `J8`\n"
        "- Current branch state: `j8_package_complete`\n"
        f"- J8 package dir: `{J8_DIR.resolve()}`\n",
        encoding="utf-8",
    )

    print(str((J8_DIR / "j8_package_manifest.json").resolve()))


if __name__ == "__main__":
    main()
