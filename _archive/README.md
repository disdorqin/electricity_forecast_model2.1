# Archive

This folder contains legacy code and experiments preserved for traceability.
It is **not** used by the production `ledger_full` pipeline.

## Contents

| Path | Original Location | Description |
|------|------------------|-------------|
| `legacy_timesfm_wrapper/` | `TimesFM/` | Old TimesFM wrapper used only by the legacy staged pipeline. The active TimesFM backend is `TimesFMBackend/`. |
| `legacy_staged_pipeline/` | various | Old 2.0 staged pipeline: `staged_pipeline.py`, `services/`, `fusion_pipeline.py`, `predict_pipeline.py`, `train_pipeline.py`. All superseded by the `ledger_*` pipeline family. |
| `fusion_legacy/` | `fusion/*.py`, `fusion/runners/` | Legacy fusion experiment scripts, runners, and meta-learners. Not used by the current ledger pipeline. |
| `dev_scripts/` | `scripts/*.py`, `scripts/*.md` | Temporary/ad-hoc development scripts. The official scripts remain in `scripts/`. |

## Policy

- Archive files are **not deleted** — they remain in Git history for reference.
- No archived file is imported or referenced by the production pipeline.
- To restore any archived file: `git mv _archive/path/to/file original/path/to/file`
