# SGDFNet Model Card

## Model name

- `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`

## Accepted config

- `SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml`

## Landing artifact

- `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`

## 2025 landing metrics

- official full-year RT capped SMAPE: `10.906743313696468`
- official `9_16` RT capped SMAPE: `15.504180616043215`
- secondary raw full-year RT SMAPE: `20.79251599092717`
- secondary raw `9_16` RT SMAPE: `36.343056642225086`

## Intended use

- realtime electricity price forecasting under the existing SGDFNet Protocol B workflow
- production-style CLI packaging for train, predict, train_predict, and rolling 2025 evaluation

## Limitations

- model stack is histogram gradient boosting, not a neural checkpoint format
- historical actual-side inputs are used only as lagged history features
- raw SMAPE remains materially higher than the business capped metric and must still be reported

## Risk hours and months

- dominant hard segment: `9_16`
- risk hours: `9`, `10`, `15`
- hardest months in `9_16`: `2025-12`, `2025-07`, `2025-01`

## No-leakage protocol

- train/validation/test must remain time-ordered
- prediction windows must be explicit
- actual-side features may only appear as historical lagged values
- official capped metric must use floor-50 rescoring

## Version history

- `v1 packaging`: wraps the accepted landing baseline into a CLI runner without changing model behavior

## Corrected realtime reference

- current corrected realtime reference: `SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide`
- protocol: `B_D15_cutoff_walk_forward`
- config: `SGDFNet/configs/cutoff_recovery_2026_diag_a_prune_actualside.yaml`
- artifact: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide_20260607_094712`
- overall capped RT SMAPE: `16.5902`
- `9_16` capped RT SMAPE: `21.1907`
