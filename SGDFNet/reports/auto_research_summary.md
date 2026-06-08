# SGDFNet Auto Research Summary

- Frozen execution baseline: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Active stage: `V2_CONTINUOUS_CLOSED`
- Current branch state: `v2_run_summary_complete`
- V2 acceptance judgment: `V2_ACCEPTED_AS_RESEARCH_ONLY`
- Best V2 research-only candidate: `P1_quantile_interval`
- Landing replacement: `False`
- New landing audit required: `False`
- Final recommendation: `keep frozen landing model and stop V2`

## Corrected No-Leakage Realtime Freeze

- Official corrected protocol: `B_D15_cutoff_walk_forward`
- Frozen corrected best artifact: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide_20260607_094712`
- Corrected baseline artifact: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Baseline_20260607_094003`
- Best corrected full-window RT capped SMAPE: `16.5902`
- Best corrected segment `9_16` RT capped SMAPE: `21.1907`
- Best corrected top-10% tail delta MAE: `165.2440`
- Status: `accepted_best_no_leakage_reference`
- Rule: future corrected realtime comparisons must use the frozen no-leakage artifact above, not the legacy leaked path
