# Final Packaging Summary

## Model

- model name: `RT916_SpikeFusionNet`
- lock source: `E1003`
- best policy: `rule_policy`
- formal package root: `D:\作业\science\大创科研时序\代码\elec\RT916_SpikeFusionNet`

## Main Entry

```powershell
python RT916_SpikeFusionNet\run.py --help
```

## Input Data

- primary dataset: `D:\作业\science\大创科研时序\代码\elec\data\shandong_pmos_hourly.xlsx`
- fixed packaged release surfaces:
  - `outputs/RT916_SpikeMarketLab/experiments/*`
  - `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet_2025/eval_2026_01_05/*` for the read-only 2026 day-ahead validation window

## Output Root

`D:\作业\science\大创科研时序\代码\elec\outputs\RT916_SpikeMarketLab\model_packages\RT916_SpikeFusionNet`

## Canonical Business Fields

The package now uses canonical column names through shared constants in `src/rt916_spikefusionnet/policy.py`:

- `时刻`
- `日前电价`
- `预测日前电价`
- `实时电价`
- `预测实时电价`

The CLI target map in `src/rt916_spikefusionnet/cli.py` also resolves to:

- `dayahead -> 日前电价`
- `realtime -> 实时电价`

## Real Non-Dry-Run Verification

### 1. Day-ahead release bundle

Command:

```powershell
python RT916_SpikeFusionNet\run.py --mode release_bundle --target dayahead --start "2025-01-01 01:00:00" --end "2025-01-31 00:00:00"
```

Output:

- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/dayahead/2025010101_2025013100/predictions.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/dayahead/2025010101_2025013100/monthly_summary.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/dayahead/2025010101_2025013100/source_manifest.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/dayahead/2025010101_2025013100/policy_selection.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/dayahead/2025010101_2025013100/bundle_summary.json`

Observed summary:

- rows: `720`
- avg_smape: `28.672000935710013`
- status: file generation succeeded

### 2. Realtime direct run

Command:

```powershell
python RT916_SpikeFusionNet\run.py --mode run --target realtime --start "2025-01-01 01:00:00" --end "2025-01-03 00:00:00"
```

Output:

- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/实时电价_分段/2025-01-01_2025-01-03_预测结果/run_20260604_122254/预测结果.csv`

Observed summary:

- rows: `48`
- CLI returned success and wrote prediction output

### 3. Realtime release bundle

Command:

```powershell
python RT916_SpikeFusionNet\run.py --mode release_bundle --target realtime --start "2025-01-01 01:00:00" --end "2025-01-31 00:00:00"
```

Output:

- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/realtime/2025010101_2025013100/predictions.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/realtime/2025010101_2025013100/monthly_summary.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/realtime/2025010101_2025013100/source_manifest.csv`
- `outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/predictions/release_bundle/realtime/2025010101_2025013100/bundle_summary.json`

Observed summary:

- rows: `720`
- avg_smape: `30.140099164240514`
- status: file generation succeeded

## Window Guard

The release bundle now fails loudly outside the validated window.

Example:

```powershell
python RT916_SpikeFusionNet\run.py --mode release_bundle --target realtime --start "2026-01-01 01:00:00" --end "2026-01-31 00:00:00"
```

Observed result:

- raises `ValueError`
- message includes:
  `release_bundle target=realtime only supports months ['2025-01', ..., '2025-12']; unsupported months requested: ['2026-01']`

## Code-Level Guarantees

1. capped SMAPE:
   `src/rt916_spikefusionnet/policy.py:53-56` clips both actual and prediction with `clip(lower=floor)` before SMAPE aggregation.

2. train/val-only policy:
   `src/rt916_spikefusionnet/policy.py:407-423` chooses `timemixer` only from validation deltas, improved/harmed day counts, and worst validation period delta; no test actual is used for selection.

3. asof after-cutoff target-derived lag and rolling recompute:
   `src/rt916_spikefusionnet/core.py:626-627` first applies `apply_asof_cutoff_for_inference(...)`, then calls `recompute_target_dependent_selected_features(...)`.

4. DA/RT switch does not use the wrong columns:
   `src/rt916_spikefusionnet/policy.py:35-37` defines explicit `TARGET_COLUMNS`, and `src/rt916_spikefusionnet/policy.py:296-299` validates required columns for the chosen target before assembly.

## Resolved Issues

- formal package moved to the project root
- unified CLI added
- canonical business column names enforced through constants and validators
- release bundle now has explicit supported-window guardrails
- non-dry-run day-ahead and realtime execution paths verified

## Remaining Boundaries

- the release-safe policy is formally locked only for the validated release windows
- 2026 day-ahead release bundle support remains tied to the historical read-only validation surfaces already produced by the project
- this packaging pass focused on release correctness and verifiability, not on improving the locked model score
