# SGDFNet

## Current Status

This directory has been cleaned to keep the **active cutoff-safe realtime path** easy to find.

The current formal realtime reference is the **no-leakage Protocol B / D15 cutoff / walk-forward** line:

- entrypoint: `scripts/run_protocol_b_cutoff.py`
- core implementation: `src/sgdfnet/protocol_b_cutoff.py`
- frozen best config: `configs/cutoff_recovery_2026_diag_a_prune_actualside.yaml`
- freeze record: `research_control/07_NO_LEAKAGE_FREEZE.json`
- human-readable freeze summary: `reports/sgdfnet_no_leakage_freeze.md`

## What To Use Now

### Realtime no-leakage evaluation

Use:

```bash
python SGDFNet/scripts/run_protocol_b_cutoff.py --config SGDFNet/configs/cutoff_recovery_2026_diag_a_prune_actualside.yaml
```

This is the current safe realtime path.

### Historical landing research path

Use only for the historical 2025 landing scope:

```bash
python SGDFNet/scripts/run_protocol_b.py --config SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml
```

This is **not** the default corrected realtime path.

## Directory Guide

- `src/sgdfnet/`
  - active package code
  - model, metrics, data contract, Protocol B logic, cutoff-safe logic
- `configs/`
  - active experiment and freeze configs
- `reports/`
  - freeze notes, protocol memos, landing summaries, research summaries
- `research_control/`
  - machine-readable control state and freeze records
- `scripts/`
  - active runnable entrypoints
- `archive/legacy_root_scripts_20260607/`
  - historical root-level automation and branch scripts kept only for traceability

## Cleanup Notes

- Root-level historical automation scripts were moved into `archive/legacy_root_scripts_20260607/`.
- The active runnable scripts were intentionally kept small inside `scripts/`:
  - `run_protocol_b_cutoff.py`
  - `run_protocol_b.py`
  - `run_cutoff_recovery_batch.py`
  - `generate_landing_2025.py`

## Current Best Corrected Realtime Result

- model/config: `cutoff_recovery_2026_diag_a_prune_actualside.yaml`
- protocol: `B_D15_cutoff_walk_forward`
- overall RT capped SMAPE: `16.5902`
- segment `9_16` RT capped SMAPE: `21.1907`
- evaluation coverage: `2026-01-01` to `2026-05-12 00:00:00`

## Important Rule

Do not mix the old leaked realtime path with the corrected cutoff-safe path in the same comparison table.
