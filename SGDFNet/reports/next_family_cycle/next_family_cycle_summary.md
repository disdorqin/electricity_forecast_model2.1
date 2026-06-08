# Next Family Cycle Summary

- Source state: `FOLLOWUP_CYCLE_COMPLETE / followup_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Follow-up TF family conclusion:
  - best raw-near-miss candidate: `followup_002` with `segment_9_16_rt_smape=36.3780`, `overall_rt_smape=20.8771`
  - best capped/tail candidate: `followup_002` with `segment_9_16_rt_capped_smape=15.3739`, `overall_rt_capped_smape=10.8667`
- New family decision: keep the strongest TF+pressure point-signal base and add leakage-safe risk-hour localized calibration.
- Reason:
  - pure TF improved tails/capped but not enough on raw 9_16
  - TF+pressure moved closer to the raw baseline while keeping capped/tail gains
  - the next falsifiable question is whether localized risk-hour calibration can convert that near-miss into a raw 9_16 win
- First candidates:
  - `hour_bias_risk_extended_on_tf_pressure`
  - `segment_hour_bias_risk_extended_on_tf_pressure`
