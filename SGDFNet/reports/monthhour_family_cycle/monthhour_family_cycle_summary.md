# Month-Hour Family Cycle Summary

- Source state: `NEXT_FAMILY_CYCLE_COMPLETE / next_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best previous localized-calibration candidate by capped/tail balance: `nextfam_001` with `segment_9_16_rt_capped_smape=15.4837`, `top10_tail_delta_mae=114.9570`.
- New family decision: move from pure hour-level repair to month-hour structured repair on top of TF+pressure.
- Reason:
  - previous hour-level and segment-hour-level variants were effectively equivalent on the restricted 9_16 calibration scope
  - the next non-isomorphic question is whether season/month-bucket hour structure captures unresolved month-hour concentration
  - this stays leakage-safe and still fits the one-main-factor discipline
- First candidates:
  - `month_hour_bias_risk_extended_on_tf_pressure`
  - `month_hour_bias_risk_extended_on_tf_pressure_recent14`
