# File Catalog

- `run.py`: top-level CLI entry
- `configs/release_safe_profile.json`: release-safe metadata and source experiment references
- `configs/default_cli.json`: default CLI suggestion
- `src/rt916_spikefusionnet/core.py`: copied backbone runner
- `src/rt916_spikefusionnet/dataprocess.py`: feature and leakage-safe processing
- `src/rt916_spikefusionnet/model.py`: core model blocks
- `src/rt916_spikefusionnet/train.py`: simple direct invocation helper
- `src/rt916_spikefusionnet/policy.py`: release-safe rule policy and bundle assembly
- `src/rt916_spikefusionnet/cli.py`: CLI parser and dispatch
