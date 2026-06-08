# Error-Gate Family Cycle Summary

- Source state: `MONTHHOUR_FAMILY_COMPLETE / monthhour_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best previous month-hour candidate by capped/tail balance: `mhfam_001` with `segment_9_16_rt_capped_smape=15.4627`, `top10_tail_delta_mae=114.9363`.
- New family decision: move from hour/month bucket repairs to validation residual error-gated correction on top of TF+pressure.
- Reason:
  - hour and month-hour structure improved some capped/tail behavior but did not repair raw 9_16 enough
  - the next non-isomorphic lightweight question is whether predicted hard-error windows are a better control signal than time buckets
  - this stays release-safe because the gate is learned only from pre-target validation residuals
- First candidates:
  - `error_gate_bias_on_tf_pressure`
  - `combo_error_sign_gate_bias_on_tf_pressure`
