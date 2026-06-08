# SGDFNet Protocol B Baseline Report

## Baseline

- Model: `SGDFNet-ProtocolB-A0-Baseline`
- Config: `SGDFNet/configs/protocol_b_a0_baseline.yaml`
- Artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_20260605_140508`

## Full-Year 2025 Summary

- RT SMAPE: `20.8329`
- Segment `9-16` RT SMAPE: `36.4570`
- RT capped SMAPE: `18.0857`
- Segment `9-16` capped RT SMAPE: `30.7776`
- Top-10% tail delta MAE: `115.1616`
- Top-10% tail RT SMAPE: `70.7849`
- Direction accuracy: `0.7936`
- Positive direction recall: `0.7771`

## Interpretation

- J0 passes cleanly because the baseline already satisfies the global full-year RT SMAPE target `< 25`.
- The unresolved problem is concentrated in the `9-16` segment, which remains above the `< 30` target.
- This makes `J1` a feature-redesign problem first, not a gate/expert problem.

## Immediate Implication

- Keep the accepted J0 baseline fixed as the comparison anchor.
- Optimize the next branches for `9-16` without giving back the very strong global baseline.
