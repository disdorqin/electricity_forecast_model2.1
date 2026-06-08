# Follow-Up Cycle Summary

- Source state: `FRESH_CYCLE_COMPLETE / fresh_cycle_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Fresh-cycle conclusion: all tried one-main-factor point-signal variants were rejected under the raw-metric hierarchy.
- Best rejected fresh-cycle candidate by 9_16 raw SMAPE: `fresh_cycle_002` with `segment_9_16_rt_smape=36.6949` and `overall_rt_smape=20.9485`.
- Worst rejected fresh-cycle candidate by 9_16 raw SMAPE: `fresh_cycle_003` with `segment_9_16_rt_smape=37.8824` and `overall_rt_smape=21.3721`.
- Follow-up family decision: move to a new point-signal family centered on time-frequency moving-average residual features.
- Rationale:
  - segment-local stats family already failed
  - forecast-pressure interaction family already failed
  - naive weekly-history family already failed
  - time-frequency moving-average features exist in the SGDFNet feature contract but have not yet been run in this post-landing autonomous point line
- Guardrails:
  - keep Protocol B fixed
  - keep floor-50 business metric reporting fixed
  - keep frozen landing artifact unchanged
  - change one mechanism family only
