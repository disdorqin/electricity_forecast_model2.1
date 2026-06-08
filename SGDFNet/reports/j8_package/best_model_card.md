# Best Model Card

- Package type: `paper_package_prep`
- Point model: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`
- Point artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Point config: `SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml`
- Official full-year capped RT SMAPE: `10.9067`
- Official 9_16 capped RT SMAPE: `15.5042`
- Secondary raw full-year RT SMAPE: `20.7925`
- Secondary raw 9_16 RT SMAPE: `36.3431`

## Interval Extension

- Module: `P1_quantile_interval`
- Interval artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`
- Mean interval coverage: `0.7747`
- Mean spike recall@topk: `0.6898`
- Mean spike average precision: `0.6390`
- Mean interval width: `98.9883`

## Claim Boundary

- This package claims a stable point baseline plus an accepted interval/probability extension.
- It does not claim point-metric improvement from the interval-only module.

## Promotion Validation

- Fresh validated month: `2026-04`
- Fusion-bundle promotion artifact: `C:\Users\37813\.codex\worktrees\ce61\elec\outputs\RT916_SpikeMarketLab\experiments\SGDFNet_PromotionValidation_202604_FusionBundle_V1_20260605_201409`
- Point-only control artifact: `C:\Users\37813\.codex\worktrees\ce61\elec\outputs\RT916_SpikeMarketLab\experiments\SGDFNet_PromotionValidation_202604_PointOnlyControl_V1_20260605_201907`
- Promotion RT capped SMAPE: `12.5007`
- Promotion 9_16 capped SMAPE: `16.2436`
- Promotion decision: `KEEP`
