# Promotion Validation Family Summary

- Source state: `FUSION_FAMILY_COMPLETE / fusion_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- New family decision: validate the current best unified candidate on fresh 2026 data windows.
- Reason:
  - `ffam_002` is now the strongest unified candidate under 2025 rolling evaluation
  - the next highest-value autonomous step is promotion-style validation, not another mechanism family
  - 2026-04 incremental data is available locally and matches the project schema
- First candidates:
  - `promotion_validation_2026_04_fusion_bundle`
  - `promotion_validation_2026_04_point_only_control`

## Executed Results

- `pvfam_001` artifact:
  - `C:\Users\37813\.codex\worktrees\ce61\elec\outputs\RT916_SpikeMarketLab\experiments\SGDFNet_PromotionValidation_202604_FusionBundle_V1_20260605_201409`
  - decision: `KEEP`
  - `rt_capped_smape = 12.5007`
  - `segment_9_16_rt_capped_smape = 16.2436`
  - `rt_smape = 26.7396`
  - `top10_tail_rt_capped_smape = 60.5617`
- `pvfam_002` artifact:
  - `C:\Users\37813\.codex\worktrees\ce61\elec\outputs\RT916_SpikeMarketLab\experiments\SGDFNet_PromotionValidation_202604_PointOnlyControl_V1_20260605_201907`
  - decision: `KEEP`
  - `rt_capped_smape = 12.5007`
  - `segment_9_16_rt_capped_smape = 16.2436`
  - `rt_smape = 26.7396`
  - `top10_tail_rt_capped_smape = 60.5617`

## Interpretation

- The repaired promotion-validation path now produces real 2026-04 predictions instead of null merges.
- On the current 2026-04 window, the interval packaging does not change point metrics relative to the point-only control.
- The promotion family therefore validates transferability of the accepted point branch to fresh 2026 data, while interval outputs remain useful for uncertainty packaging rather than point-score gain.
- The promotion family candidate pool is effectively exhausted for the current 2026-04 scope.
