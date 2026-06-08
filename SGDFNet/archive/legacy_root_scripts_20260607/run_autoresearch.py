from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_PATH = PROJECT_ROOT / "research_control" / "03_STAGE_STATE.json"
NEXT_STAGE_PACKAGE_PATH = PROJECT_ROOT / "reports" / "next_stage_package" / "next_stage_package.json"
J8_MANIFEST_PATH = PROJECT_ROOT / "reports" / "j8_package" / "j8_package_manifest.json"


def _load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    state["last_updated"] = str(date.today())
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_next_stage_package() -> dict | None:
    if not NEXT_STAGE_PACKAGE_PATH.exists():
        return None
    return json.loads(NEXT_STAGE_PACKAGE_PATH.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal SGDFNet autonomous research launcher.")
    parser.add_argument(
        "--action",
        choices=[
            "auto",
            "j0_baseline",
            "j1_segment_local",
            "j1_forecast_pressure",
            "j2_tail_weighted",
            "j2_segment_conditioned",
            "j2_asymmetric_loss",
            "j2_val_segment_bias",
            "j2_val_all_segment_bias",
            "j2_val_direction_bias",
            "j2_val_threshold_bias",
            "j2_val_recent_bias",
            "j2_val_mean_bias",
            "j2_val_bias_tail",
            "j2_val_q40_bias",
        ],
        # Keep the explicit list close to current accepted branches for safe automation growth.
        default="auto",
    )
    args = parser.parse_args()

    state = _load_state()
    action = args.action
    if action == "auto":
        if state["current_stage"] == "NEW_BRANCH_PREP" and state["current_branch"] == "new_branch_init_ready":
            new_branch_init_path = PROJECT_ROOT / "reports" / "new_branch_init" / "new_branch_init.json"
            if new_branch_init_path.exists():
                cmd = [sys.executable, str(PROJECT_ROOT / "run_new_cycle_prep.py")]
                completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
                print(completed.stdout.strip().splitlines()[-1].strip())
                return
        if state["current_stage"] == "NEW_CYCLE_READY" and state["current_branch"] == "new_cycle_prep_complete":
            new_cycle_manifest = PROJECT_ROOT / "reports" / "new_cycle_prep" / "new_cycle_prep_manifest.json"
            if new_cycle_manifest.exists():
                cmd = [sys.executable, str(PROJECT_ROOT / "run_cycle_kickoff.py")]
                completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
                print(completed.stdout.strip().splitlines()[-1].strip())
                return
        if state["current_stage"] == "KICKOFF_READY" and state["current_branch"] == "cycle_kickoff_complete":
            kickoff_manifest = PROJECT_ROOT / "reports" / "cycle_kickoff" / "cycle_kickoff_manifest.json"
            if kickoff_manifest.exists():
                cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_first_experiment.py")]
                completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
                print(completed.stdout.strip().splitlines()[-1].strip())
                return
        if state["current_stage"] == "FIRST_EXPERIMENT_READY" and state["current_branch"] == "first_experiment_instance_complete":
            first_manifest = PROJECT_ROOT / "reports" / "first_experiment_instance" / "first_experiment_instance_manifest.json"
            if first_manifest.exists():
                cmd = [sys.executable, str(PROJECT_ROOT / "run_first_experiment.py")]
                completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
                print(completed.stdout.strip().splitlines()[-1].strip())
                return
        if state["current_stage"] == "FIRST_EXPERIMENT_RAN" and state["current_branch"] == "first_experiment_run_complete":
            first_manifest = PROJECT_ROOT / "reports" / "first_experiment_instance" / "first_experiment_instance_manifest.json"
            if first_manifest.exists():
                cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_first_experiment.py")]
                completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
                print(completed.stdout.strip().splitlines()[-1].strip())
                return
        if state["current_stage"] == "FIRST_EXPERIMENT_EVALUATED" and state["current_branch"] == "first_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_next_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FRESH_CYCLE_EXPERIMENT_READY" and state["current_branch"] == "fresh_cycle_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_next_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FRESH_CYCLE_EXPERIMENT_RAN" and state["current_branch"] == "fresh_cycle_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_next_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FRESH_CYCLE_EXPERIMENT_EVALUATED" and state["current_branch"] == "fresh_cycle_experiment_decision_complete":
            if state.get("last_fresh_cycle_decision") == "KEEP":
                decision_path = Path(state["active_fresh_cycle_instance_dir"]) / "decision.json"
                print(str(decision_path.resolve()))
                return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_next_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FRESH_CYCLE_COMPLETE" and state["current_branch"] == "fresh_cycle_candidate_pool_exhausted":
            kickoff_decision = PROJECT_ROOT / "reports" / "fresh_cycle" / "first_experiment_decision.json"
            if kickoff_decision.exists():
                cmd = [sys.executable, str(PROJECT_ROOT / "prepare_kickoff_followup_cycle.py")]
            else:
                cmd = [sys.executable, str(PROJECT_ROOT / "prepare_followup_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_FOLLOWUP_CYCLE_PREPARED" and state["current_branch"] == "kickoff_followup_cycle_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_FOLLOWUP_EXPERIMENT_READY" and state["current_branch"] == "kickoff_followup_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_kickoff_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_FOLLOWUP_EXPERIMENT_RAN" and state["current_branch"] == "kickoff_followup_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_kickoff_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_FOLLOWUP_EXPERIMENT_EVALUATED" and state["current_branch"] == "kickoff_followup_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_FOLLOWUP_CYCLE_COMPLETE" and state["current_branch"] == "kickoff_followup_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_kickoff_tailcal_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_TAILCAL_FAMILY_PREPARED" and state["current_branch"] == "kickoff_tailcal_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_TAILCAL_EXPERIMENT_READY" and state["current_branch"] == "kickoff_tailcal_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_kickoff_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_TAILCAL_EXPERIMENT_RAN" and state["current_branch"] == "kickoff_tailcal_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_kickoff_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_TAILCAL_EXPERIMENT_EVALUATED" and state["current_branch"] == "kickoff_tailcal_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_TAILCAL_FAMILY_COMPLETE" and state["current_branch"] == "kickoff_tailcal_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_kickoff_conservative_tailcal_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_CONSERVATIVE_TAILCAL_FAMILY_PREPARED" and state["current_branch"] == "kickoff_conservative_tailcal_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_conservative_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_READY" and state["current_branch"] == "kickoff_conservative_tailcal_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_kickoff_conservative_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_RAN" and state["current_branch"] == "kickoff_conservative_tailcal_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_kickoff_conservative_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_CONSERVATIVE_TAILCAL_EXPERIMENT_EVALUATED" and state["current_branch"] == "kickoff_conservative_tailcal_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_conservative_tailcal_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_CONSERVATIVE_TAILCAL_FAMILY_COMPLETE" and state["current_branch"] == "kickoff_conservative_tailcal_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_kickoff_selective_gate_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_SELECTIVE_GATE_FAMILY_PREPARED" and state["current_branch"] == "kickoff_selective_gate_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_selective_gate_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_SELECTIVE_GATE_EXPERIMENT_READY" and state["current_branch"] == "kickoff_selective_gate_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_kickoff_selective_gate_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_SELECTIVE_GATE_EXPERIMENT_RAN" and state["current_branch"] == "kickoff_selective_gate_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_kickoff_selective_gate_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_SELECTIVE_GATE_EXPERIMENT_EVALUATED" and state["current_branch"] == "kickoff_selective_gate_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_selective_gate_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_SELECTIVE_GATE_FAMILY_COMPLETE" and state["current_branch"] == "kickoff_selective_gate_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_kickoff_monthhour_selective_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_PREPARED" and state["current_branch"] == "kickoff_monthhour_selective_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_monthhour_selective_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_MONTHHOUR_SELECTIVE_EXPERIMENT_READY" and state["current_branch"] == "kickoff_monthhour_selective_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_kickoff_monthhour_selective_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_MONTHHOUR_SELECTIVE_EXPERIMENT_RAN" and state["current_branch"] == "kickoff_monthhour_selective_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_kickoff_monthhour_selective_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_MONTHHOUR_SELECTIVE_EXPERIMENT_EVALUATED" and state["current_branch"] == "kickoff_monthhour_selective_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_monthhour_selective_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_COMPLETE" and state["current_branch"] == "kickoff_monthhour_selective_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_kickoff_structural_point_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_STRUCTURAL_POINT_FAMILY_PREPARED" and state["current_branch"] == "kickoff_structural_point_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_structural_point_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_STRUCTURAL_POINT_EXPERIMENT_READY" and state["current_branch"] == "kickoff_structural_point_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_kickoff_structural_point_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_STRUCTURAL_POINT_EXPERIMENT_RAN" and state["current_branch"] == "kickoff_structural_point_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_kickoff_structural_point_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_STRUCTURAL_POINT_EXPERIMENT_EVALUATED" and state["current_branch"] == "kickoff_structural_point_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_kickoff_structural_point_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "KICKOFF_STRUCTURAL_POINT_FAMILY_COMPLETE" and state["current_branch"] == "kickoff_structural_point_family_candidate_pool_exhausted":
            summary_path = PROJECT_ROOT / "reports" / "kickoff_structural_point_family_cycle" / "kickoff_structural_point_experiment_results.csv"
            if summary_path.exists():
                print(str(summary_path.resolve()))
                return
        if state["current_stage"] == "FOLLOWUP_CYCLE_PREPARED" and state["current_branch"] == "followup_cycle_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FOLLOWUP_EXPERIMENT_READY" and state["current_branch"] == "followup_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FOLLOWUP_EXPERIMENT_RAN" and state["current_branch"] == "followup_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FOLLOWUP_EXPERIMENT_EVALUATED" and state["current_branch"] == "followup_experiment_decision_complete":
            if state.get("last_followup_decision") == "KEEP":
                decision_path = Path(state["active_followup_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_followup_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FOLLOWUP_CYCLE_COMPLETE" and state["current_branch"] == "followup_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_next_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "NEXT_FAMILY_CYCLE_PREPARED" and state["current_branch"] == "next_family_cycle_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_next_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "NEXT_FAMILY_EXPERIMENT_READY" and state["current_branch"] == "next_family_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_next_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "NEXT_FAMILY_EXPERIMENT_RAN" and state["current_branch"] == "next_family_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_next_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "NEXT_FAMILY_EXPERIMENT_EVALUATED" and state["current_branch"] == "next_family_experiment_decision_complete":
            if state.get("last_next_family_decision") == "KEEP":
                decision_path = Path(state["active_next_family_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_next_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "NEXT_FAMILY_CYCLE_COMPLETE" and state["current_branch"] == "next_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_monthhour_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "MONTHHOUR_FAMILY_PREPARED" and state["current_branch"] == "monthhour_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_monthhour_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "MONTHHOUR_FAMILY_EXPERIMENT_READY" and state["current_branch"] == "monthhour_family_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_monthhour_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "MONTHHOUR_FAMILY_EXPERIMENT_RAN" and state["current_branch"] == "monthhour_family_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_monthhour_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "MONTHHOUR_FAMILY_EXPERIMENT_EVALUATED" and state["current_branch"] == "monthhour_family_experiment_decision_complete":
            if state.get("last_monthhour_decision") == "KEEP":
                decision_path = Path(state["active_monthhour_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_monthhour_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "MONTHHOUR_FAMILY_COMPLETE" and state["current_branch"] == "monthhour_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_errorgate_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "ERRORGATE_FAMILY_PREPARED" and state["current_branch"] == "errorgate_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_errorgate_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "ERRORGATE_FAMILY_EXPERIMENT_READY" and state["current_branch"] == "errorgate_family_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_errorgate_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "ERRORGATE_FAMILY_EXPERIMENT_RAN" and state["current_branch"] == "errorgate_family_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_errorgate_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "ERRORGATE_FAMILY_EXPERIMENT_EVALUATED" and state["current_branch"] == "errorgate_family_experiment_decision_complete":
            if state.get("last_errorgate_decision") == "KEEP":
                decision_path = Path(state["active_errorgate_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_errorgate_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "ERRORGATE_FAMILY_COMPLETE" and state["current_branch"] == "errorgate_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_structural_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "STRUCTURAL_FAMILY_PREPARED" and state["current_branch"] == "structural_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_structural_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "STRUCTURAL_FAMILY_EXPERIMENT_READY" and state["current_branch"] == "structural_family_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_structural_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "STRUCTURAL_FAMILY_EXPERIMENT_RAN" and state["current_branch"] == "structural_family_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_structural_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "STRUCTURAL_FAMILY_EXPERIMENT_EVALUATED" and state["current_branch"] == "structural_family_experiment_decision_complete":
            if state.get("last_structural_decision") == "KEEP":
                decision_path = Path(state["active_structural_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_structural_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "STRUCTURAL_FAMILY_COMPLETE" and state["current_branch"] == "structural_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_tfpressure_probability_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "TFPRESSURE_PROBABILITY_FAMILY_PREPARED" and state["current_branch"] == "tfpressure_probability_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_tfpressure_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "TFPRESSURE_PROBABILITY_EXPERIMENT_READY" and state["current_branch"] == "tfpressure_probability_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_tfpressure_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "TFPRESSURE_PROBABILITY_EXPERIMENT_RAN" and state["current_branch"] == "tfpressure_probability_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_tfpressure_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "TFPRESSURE_PROBABILITY_EXPERIMENT_EVALUATED" and state["current_branch"] == "tfpressure_probability_experiment_decision_complete":
            if state.get("last_tfpressure_probability_decision") == "KEEP":
                decision_path = Path(state["active_tfpressure_probability_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_tfpressure_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "TFPRESSURE_PROBABILITY_FAMILY_COMPLETE" and state["current_branch"] == "tfpressure_probability_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_signed_tail_probability_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_PROBABILITY_FAMILY_PREPARED" and state["current_branch"] == "signed_tail_probability_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_signed_tail_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_PROBABILITY_EXPERIMENT_READY" and state["current_branch"] == "signed_tail_probability_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_signed_tail_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_PROBABILITY_EXPERIMENT_RAN" and state["current_branch"] == "signed_tail_probability_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_signed_tail_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_PROBABILITY_EXPERIMENT_EVALUATED" and state["current_branch"] == "signed_tail_probability_experiment_decision_complete":
            if state.get("last_signed_tail_probability_decision") == "KEEP":
                decision_path = Path(state["active_signed_tail_probability_instance_dir"]) / "decision.json"
                if decision_path.exists():
                    print(str(decision_path.resolve()))
                    return
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_signed_tail_probability_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_PROBABILITY_FAMILY_COMPLETE" and state["current_branch"] == "signed_tail_probability_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_signed_tail_calibration_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_CALIBRATION_FAMILY_PREPARED" and state["current_branch"] == "signed_tail_calibration_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_signed_tail_calibration_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_CALIBRATION_EXPERIMENT_READY" and state["current_branch"] == "signed_tail_calibration_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_signed_tail_calibration_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_CALIBRATION_EXPERIMENT_RAN" and state["current_branch"] == "signed_tail_calibration_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_signed_tail_calibration_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_CALIBRATION_EXPERIMENT_EVALUATED" and state["current_branch"] == "signed_tail_calibration_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_signed_tail_calibration_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE" and state["current_branch"] == "signed_tail_calibration_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_fusion_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FUSION_FAMILY_PREPARED" and state["current_branch"] == "fusion_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_fusion_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FUSION_FAMILY_EXPERIMENT_READY" and state["current_branch"] == "fusion_family_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_fusion_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FUSION_FAMILY_EXPERIMENT_RAN" and state["current_branch"] == "fusion_family_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_fusion_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FUSION_FAMILY_EXPERIMENT_EVALUATED" and state["current_branch"] == "fusion_family_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_fusion_family_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "FUSION_FAMILY_COMPLETE" and state["current_branch"] == "fusion_family_candidate_pool_exhausted":
            cmd = [sys.executable, str(PROJECT_ROOT / "prepare_promotion_validation_family_cycle.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "PROMOTION_VALIDATION_FAMILY_PREPARED" and state["current_branch"] == "promotion_validation_family_manifest_ready":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_promotion_validation_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "PROMOTION_VALIDATION_EXPERIMENT_READY" and state["current_branch"] == "promotion_validation_experiment_instance_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_promotion_validation_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "PROMOTION_VALIDATION_EXPERIMENT_RAN" and state["current_branch"] == "promotion_validation_experiment_run_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "evaluate_promotion_validation_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "PROMOTION_VALIDATION_EXPERIMENT_EVALUATED" and state["current_branch"] == "promotion_validation_experiment_decision_complete":
            cmd = [sys.executable, str(PROJECT_ROOT / "instantiate_promotion_validation_experiment.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "PROMOTION_VALIDATION_FAMILY_COMPLETE" and state["current_branch"] == "promotion_validation_family_candidate_pool_exhausted":
            summary_path = PROJECT_ROOT / "reports" / "promotion_validation_family_cycle" / "promotion_validation_experiment_results.csv"
            if summary_path.exists():
                print(str(summary_path.resolve()))
                return
        if state["current_stage"] == "J8" and state["current_branch"] == "j8_package_complete" and J8_MANIFEST_PATH.exists():
            cmd = [sys.executable, str(PROJECT_ROOT / "generate_new_branch_init.py")]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        next_stage_package = _load_next_stage_package()
        if next_stage_package and next_stage_package.get("status") == "ready" and next_stage_package.get("recommended_stage") == "J8":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_j8_package.py"), "--package", str(NEXT_STAGE_PACKAGE_PATH)]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "V2_CONTINUOUS":
            cmd = [sys.executable, str(PROJECT_ROOT / "run_v2_continuous.py"), "--branch", "auto"]
            completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
            print(completed.stdout.strip().splitlines()[-1].strip())
            return
        if state["current_stage"] == "J0":
            action = "j0_baseline"
        elif state["current_stage"] == "J1" and state["current_branch"] == "forecast_pressure_feature_redesign_next":
            action = "j1_segment_local"
        elif state["current_stage"] == "J1" and state["current_branch"] == "j1_segment_local_rejected_next_pressure":
            action = "j1_forecast_pressure"
        elif state["current_stage"] == "J2" and state["current_branch"] == "tail_weighted_objective_next":
            action = "j2_tail_weighted"
        elif state["current_stage"] == "J2" and state["current_branch"] == "segment_conditioned_baseline_next":
            action = "j2_segment_conditioned"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_asymmetric_loss":
            action = "j2_asymmetric_loss"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_val_segment_bias":
            action = "j2_val_segment_bias"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_all_segment_bias_sensitivity":
            action = "j2_val_all_segment_bias"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_direction_calibration":
            action = "j2_val_direction_bias"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_direction_threshold_sensitivity":
            action = "j2_val_threshold_bias"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_combined_bias_tail_sensitivity":
            action = "j2_val_bias_tail"
        elif state["current_stage"] == "J2" and state["current_branch"] == "j2_checkpoint_next_calibration_quantile_sensitivity":
            action = "j2_val_q40_bias"
        else:
            raise ValueError(f"No auto-dispatch rule registered for stage={state['current_stage']} branch={state['current_branch']}")

    if action == "j0_baseline":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_baseline.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "protocol_b_a0_baseline_completed"
        state["current_best_model"] = "SGDFNet-ProtocolB-A0-Baseline"
        state["current_best_config"] = str(config_path)
        state["current_best_artifact"] = run_dir
        state["allowed_next_actions"] = [
            "register J0 baseline in ledger",
            "compare future branches against the accepted Protocol B baseline",
            "start J1 feature redesign under Protocol B",
        ]
        _save_state(state)
        print(run_dir)
        return

    if action == "j1_segment_local":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j1_segment_local_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j1_segment_local_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j1_forecast_pressure":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j1_forecast_pressure_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j1_forecast_pressure_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_tail_weighted":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_tail_weighted_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_tail_weighted_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_segment_conditioned":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_segment_conditioned_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_segment_conditioned_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_asymmetric_loss":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_asymmetric_loss_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_asymmetric_loss_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_segment_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_segment_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_segment_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_all_segment_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_all_segment_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_all_segment_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_direction_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_direction_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_direction_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_threshold_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_threshold_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_threshold_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_recent_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_recent_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_recent_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_mean_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_mean_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_mean_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_bias_tail":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_bias_tail_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_bias_tail_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    if action == "j2_val_q40_bias":
        config_path = PROJECT_ROOT / "configs" / "protocol_b_a0_j2_val_q40_bias_v1.yaml"
        cmd = [sys.executable, str(PROJECT_ROOT / "run_protocol_b.py"), "--config", str(config_path)]
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT.parent), check=True, capture_output=True, text=True)
        run_dir = completed.stdout.strip().splitlines()[-1].strip()
        state["current_branch"] = "j2_val_q40_bias_completed_pending_registration"
        state["last_candidate_artifact"] = run_dir
        _save_state(state)
        print(run_dir)
        return

    raise ValueError(f"Unsupported action: {action}")


if __name__ == "__main__":
    main()
