# SGDFNet No-Leakage Freeze

- Frozen best no-leakage model: `SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide`
- Protocol: `B_D15_cutoff_walk_forward`
- Config: `SGDFNet/configs/cutoff_recovery_2026_diag_a_prune_actualside.yaml`
- Artifact: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide_20260607_094712`
- Baseline for comparison: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Baseline_20260607_094003`

## Frozen Metrics

- Full-window RT capped SMAPE: `16.5902`
- Full-window RT SMAPE: `32.2228`
- Full-window RT MAE: `54.0577`
- Segment `9_16` RT capped SMAPE: `21.1907`
- Segment `9_16` RT SMAPE: `52.7001`
- Risk-hour `9/10/15` RT capped SMAPE: `24.5123`
- Top-10% tail delta MAE: `165.2440`
- Top-10% tail RT SMAPE: `84.5243`
- Direction accuracy: `0.7910`
- Positive direction recall: `0.7490`

## Improvement vs No-Leakage Baseline

- Overall capped SMAPE gain: `+0.1072`
- Segment `9_16` capped SMAPE gain: `+0.2095`
- Top-10% tail delta MAE gain: `+3.1616`
- Top-10% tail RT SMAPE gain: `+2.6690`

## Scope Notes

- This freeze is the current **best corrected no-leakage reference**, not a replacement for the historical 2025 landing freeze.
- The evaluation window is `2026-01-01` through `2026-05-12 00:00:00`.
- `2026-05` is partial because the current workspace dataset ends at `2026-05-12 00:00:00`.
- All future corrected realtime comparisons should use this freeze unless a later no-leakage run beats it under the same protocol and metric formula.
