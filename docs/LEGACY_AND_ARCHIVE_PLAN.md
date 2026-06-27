# Legacy & Archive Plan

> **Status: Plan only — no files have been moved or deleted yet.**

This document describes the current state of legacy directories and files in the repository, and provides a plan for future cleanup.

---

## Guiding Principle

Do not break the old `staged_pipeline` until it is confirmed fully replaced by the `ledger` pipeline.

The old staged pipeline (`model_stage`, `learner_stage`, `fuse_stage`, `classifier_stage`, `full`) is preserved as a working baseline. Once it is no longer needed, legacy files can be safely archived.

---

## 1. TF/ vs TimesFM/

| Directory | Status | Used by ledger pipeline | Used by staged_pipeline | Plan |
|-----------|--------|------------------------|------------------------|------|
| `TF/` | **Active** | Yes (via `runners/adapters/timesfm_v1.py` → `TF.infer`) | No | KEEP — this is the canonical TimesFM backend |
| `TimesFM/` | **Legacy wrapper** | No | Yes (via `runners/registry.py` → `TimesFM.pipeline`) | ARCHIVE_LATER after staged_pipeline is retired |

**Why duplicate?** `TimesFM/` was the original 2.0 wrapper. `TF/` was added as the EPF v1.0 backend containing the full `timesfm_2p5` implementation (PyTorch + Flax). Both directories contain an identical `src/timesfm/` package.

**Archive plan:**
1. Confirm staged_pipeline is fully replaced by ledger pipeline
2. Move `TimesFM/` → `_archive/TimesFM/`
3. Update `runners/registry.py` to remove the `TimesFM.pipeline` entry
4. Keep `TF/` as the canonical TimesFM directory

**Renaming note:** `TF/` could be renamed to `TimesFM/` to avoid confusion with TensorFlow, but this would require updating all import references (`runners/adapters/timesfm_v1.py`, `TF/infer.py` internal imports). Not recommended until a dedicated refactor phase.

---

## 2. fusion/ — Legacy Scripts

The following files are **not used** by the ledger pipeline and are candidates for `_archive/fusion_legacy/`:

### Legacy fusion runners (not imported by any pipeline)
```
fusion/run_pipeline.py
fusion/run_dayahead_pipeline.py
fusion/run_realtime_pipeline.py
fusion/run_fit.py
fusion/run_end_to_end_fixed_fusion.py
fusion/run_final_fusion_pipeline.py
fusion/run_rolling_backtest.py
fusion/run_full_fusion_suite.py
fusion/run_repro_training_length_suite.py
fusion/prepare_history_outputs.py
fusion/prepare_manifest.py
fusion/repro_suite.py
fusion/meta_learner.py
fusion/manifest_template.csv
```

### Legacy fusion runner scripts (all in `fusion/runners/`)
```
fusion/runners/analyze_rt916_spikes.py
fusion/runners/assemble_timemixer_round4_combo.py
fusion/runners/run_lightgbm_epf_export.py
fusion/runners/run_lightgbm_export.py
fusion/runners/run_rt916_export.py
fusion/runners/run_sgdfnet_export.py
fusion/runners/run_timemixer_direct24_batch.py
fusion/runners/run_timemixer_enhanced_export.py
fusion/runners/run_timemixer_export.py
fusion/runners/run_timemixer_frozen_batch.py
fusion/runners/run_timemixer_multiseed_batch.py
fusion/runners/run_timemixer_rt916_spike_day_batch.py
fusion/runners/run_timemixer_safe_fusion.py
fusion/runners/run_timemixer_safe_fusion_batch.py
fusion/runners/run_timemixer_vmd_rt916.py
fusion/runners/run_timesfm_epf_export.py
fusion/runners/run_timesfm_export.py
```

### Active fusion files (DO NOT ARCHIVE)
```
fusion/learners/daily_ledger_gef.py        # Used by ledger_weight
fusion/apply_daily_ledger_weights.py        # Used by ledger_fuse
fusion/classifier_bridge.py                 # Used by ledger_classifier
fusion/metrics.py                           # Shared metrics
fusion/registry.py                          # Fusion adapter registry
fusion/adapters/*.py                        # Per-model adapters
fusion/coverage_utils.py                    # Coverage reports
fusion/pipeline_common.py                   # Shared pipeline helpers
fusion/project_defaults.py                  # Defaults config
```

**Note:** `fusion/contracts.py`, `fusion/weights.py`, and `fusion/run_fixed_window_fusion.py` are still used by the old staged pipeline. Archive only after staged_pipeline is retired.

---

## 3. services/

| File | Used by ledger pipeline | Used by staged_pipeline | Plan |
|------|------------------------|------------------------|------|
| `services/fusion_service.py` | No | Yes (imported by `fusion_pipeline.py`) | ARCHIVE_LATER after staged_pipeline retired |
| `services/predict_service.py` | No | Yes (imported by `predict_pipeline.py`, `train_pipeline.py`) | ARCHIVE_LATER after staged_pipeline retired |

`services/` wraps model execution as subprocess calls for the old pipeline. The ledger pipeline runs models directly through `runtime/resource_scheduler.py`.

---

## 4. staged_pipeline.py

`pipelines/staged_pipeline.py` is the old 2.0 pipeline entry that chains `model_stage` → `learner_stage` → `fuse_stage` → `classifier_stage`. It remains functional but is being superseded by the `ledger_*` pipeline family.

The ledger pipeline differs from the staged pipeline in several ways:
- Uses EPF v1.0 adapters for LightGBM and TimesFM (not direct model pipelines)
- Uses `runtime/resource_scheduler.py` for CPU/GPU concurrency (not the old executor)
- Uses ledger storage (not daily run directories)
- Uses `DailyLedgerGEF` for weight learning (not the old `fusion/weights.py`)

**Plan:** Keep `staged_pipeline.py` until all production runs use the ledger pipeline.

---

## 5. Legacy Output Directories

| Directory | Description | Plan |
|-----------|-------------|------|
| `outputs/unified_runs/` | Old pipeline per-model output format | DELETE_AFTER_BACKUP |
| `outputs/2026-02-01/` | Legacy top-level output | DELETE_AFTER_BACKUP |
| `outputs/RT916_SpikeMarketLab/` | RT916 experimental output | DELETE_AFTER_BACKUP |
| `daily_runs/` | Old staged pipeline output | DELETE_AFTER_BACKUP |

---

## 6. Recommended Archive Steps (Future Phase)

1. **Back up** outputs/ contents (if needed), then cleanup legacy output directories.
2. **Move** `TimesFM/` → `_archive/TimesFM/`.
3. **Move** `fusion/legacy/` files (listed above) → `_archive/fusion_legacy/`.
4. **Move** `services/` → `_archive/services/` (after staged_pipeline retired).
5. **Remove** `staged_pipeline.py` → `_archive/pipelines/staged_pipeline.py` (after confirmed fully replaced).
6. **Update** `runners/registry.py` to remove `TimesFM.pipeline` entry.
7. **Clean up** `docs/LEGACY_AND_ARCHIVE_PLAN.md` after archive is done.

---

## Current Do-Not-Touch List

These are confirmed as not interfering with the current ledger pipeline. Do not touch until the next cleanup phase:

- `TimesFM/` — still referenced by `runners/registry.py` for staged_pipeline
- `services/` — still referenced by `pipelines/fusion_pipeline.py`
- `pipelines/staged_pipeline.py` — functional baseline
- `fusion/contracts.py`, `fusion/weights.py`, `fusion/run_fixed_window_fusion.py` — used by staged_pipeline
- All `fusion/runners/*.py` — archived in plan only
