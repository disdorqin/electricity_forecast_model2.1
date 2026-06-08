from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
KICKOFF_DIR = PROJECT_ROOT / "reports" / "cycle_kickoff"
SEED_CSV = KICKOFF_DIR / "kickoff_experiment_seed.csv"
SEED_YAML = KICKOFF_DIR / "kickoff_config_seed.yaml"
INSTANCE_DIR = PROJECT_ROOT / "reports" / "first_experiment_instance"
AUTO_SUMMARY_PATH = PROJECT_ROOT / "reports" / "auto_research_summary.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    state = _load_json(STATE_PATH)
    allowed_states = {
        ("KICKOFF_READY", "cycle_kickoff_complete"),
        ("FIRST_EXPERIMENT_READY", "first_experiment_instance_complete"),
    }
    if (state.get("current_stage"), state.get("current_branch")) not in allowed_states:
        raise ValueError("First experiment instantiation is only allowed from KICKOFF_READY or FIRST_EXPERIMENT_READY refresh states.")
    if not SEED_CSV.exists() or not SEED_YAML.exists():
        raise FileNotFoundError("Kickoff seed artifacts are required before instantiation.")

    with SEED_CSV.open("r", encoding="utf-8") as f:
        row = next(csv.DictReader(f))

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    instantiated_yaml = (
        "experiment_name: SGDFNet_FirstExperiment_FeatureRedesign_V1\n"
        "data_path: data/shandong_pmos_hourly.xlsx\n"
        "output_root: outputs/RT916_SpikeMarketLab/experiments\n"
        "target_year: 2025\n"
        "val_days: 30\n"
        "train_min_rows: 2160\n"
        "apply_segment_bias_calibration: true\n"
        "calibration_segments:\n"
        "  - \"9_16\"\n"
        "\n"
        "feature_config:\n"
        "  include_forecast_columns: true\n"
        "  include_actual_history_columns: true\n"
        "  include_delta_history_features: true\n"
        "  include_weekly_history_features: false\n"
        "  include_forecast_residual_history_features: true\n"
        "  include_segment_local_stats: true\n"
        "  include_forecast_pressure_interactions: false\n"
        "  include_calendar_features: true\n"
        "  include_engineered_forecast_features: true\n"
        "\n"
        "model_config:\n"
        "  loss: absolute_error\n"
        "  quantile_alpha: 0.5\n"
        "  learning_rate: 0.05\n"
        "  max_depth: 6\n"
        "  max_iter: 300\n"
        "  min_samples_leaf: 40\n"
        "  l2_regularization: 0.1\n"
        "  random_state: 42\n"
        "  tail_sample_weight: 1.0\n"
        "  tail_quantile: 0.85\n"
        "  segment_conditioned_models: false\n"
        "\n"
        "instance_id: first_experiment_001\n"
        "status: runnable\n"
        "baseline_reference: " + row["baseline_artifact"].replace("\\", "/") + "\n"
        "changed_factor_label: segment_local_stats_enabled\n"
    )
    (INSTANCE_DIR / row["planned_config_name"]).write_text(instantiated_yaml, encoding="utf-8")

    run_instruction = (
        "# First Experiment Instruction\n\n"
        f"- Experiment ID: `{row['experiment_id']}`\n"
        f"- Stage: `{row['stage']}`\n"
        f"- Branch: `{row['branch']}`\n"
        f"- Changed factor: `{row['changed_factor']}`\n"
        f"- Planned config: `{row['planned_config_name']}`\n"
        "- This instance is intentionally planning-only.\n"
        "- Next implementation step should connect this plan to a concrete training/data path without breaking the frozen baseline contract.\n"
    )
    (INSTANCE_DIR / "FIRST_EXPERIMENT_INSTRUCTION.md").write_text(run_instruction, encoding="utf-8")

    todo_note = (
        "# First Experiment TODO\n\n"
        "- Bind this planned config to a concrete SGDFNet-owned experiment implementation path.\n"
        "- Keep one main factor: stronger raw-error-oriented feature redesign.\n"
        "- Emit predictions.csv, monthly_summary.csv, and leakage_audit.md when the first real run is implemented.\n"
    )
    (INSTANCE_DIR / "FIRST_EXPERIMENT_TODO.md").write_text(todo_note, encoding="utf-8")

    manifest = {
        "generated_on": str(date.today()),
        "experiment_id": row["experiment_id"],
        "stage": row["stage"],
        "branch": row["branch"],
        "changed_factor": row["changed_factor"],
        "baseline_artifact": row["baseline_artifact"],
        "planned_config_name": row["planned_config_name"],
        "outputs": [
            row["planned_config_name"],
            "FIRST_EXPERIMENT_INSTRUCTION.md",
            "FIRST_EXPERIMENT_TODO.md",
        ],
        "instance_status": "runnable",
        "refreshable": True,
    }
    _write_json(INSTANCE_DIR / "first_experiment_instance_manifest.json", manifest)

    state["current_stage"] = "FIRST_EXPERIMENT_READY"
    state["current_branch"] = "first_experiment_instance_complete"
    state["allowed_next_actions"] = [
        "review the first experiment instance",
        "implement the first concrete SGDFNet-owned experiment runner for this instance",
        "execute the first new-cycle experiment",
    ]
    state["last_updated"] = str(date.today())
    _write_json(STATE_PATH, state)

    AUTO_SUMMARY_PATH.write_text(
        "# SGDFNet Auto Research Summary\n\n"
        f"- Frozen execution baseline: `{state['frozen_execution_baseline_artifact']}`\n"
        "- Active stage: `FIRST_EXPERIMENT_READY`\n"
        "- Current branch state: `first_experiment_instance_complete`\n"
        f"- First experiment instance dir: `{INSTANCE_DIR.resolve()}`\n",
        encoding="utf-8",
    )

    print(str((INSTANCE_DIR / "first_experiment_instance_manifest.json").resolve()))


if __name__ == "__main__":
    main()
