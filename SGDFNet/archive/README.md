# SGDFNet Archive

This archive stores historical root-level scripts and summaries that are no longer part of the primary SGDFNet entry surface.

## Archive Buckets

- `legacy_root_scripts_20260607/`
  - former root-level orchestration, family-cycle, evaluation, and packaging scripts
  - kept for traceability only
  - not the recommended place to start new work

## Why These Files Were Moved

The SGDFNet root had accumulated many one-off experiment drivers and cycle-specific automation files.
They were cluttering the active package and making it harder to identify the current safe realtime path.

The active runnable surface now centers on `SGDFNet/scripts/`:

- `run_protocol_b_cutoff.py`
- `run_protocol_b.py`
- `run_cutoff_recovery_batch.py`
- `generate_landing_2025.py`

If an archived script is needed again, restore it deliberately rather than letting it remain mixed into the active surface.
