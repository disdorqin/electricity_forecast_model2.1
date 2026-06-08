# Kickoff MonthHour Selective Family Summary

- Source state: `KICKOFF_SELECTIVE_GATE_FAMILY_COMPLETE / kickoff_selective_gate_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best selective-gate near-miss: `ksgate_002` with `full_year_rt_capped_smape=10.8593`, `segment_9_16_rt_capped_smape=15.3606`, and `top10_tail_rt_capped_smape=38.8026`.
- New family decision: switch to a cleaner teacher driven by stable month-hour risk cells from the diagnosis, instead of tail-triggered residual medians.
- First candidates:
  - `kickoff_monthhour_selective_season_risk_hours`
  - `kickoff_monthhour_selective_sign_consistent_risk_hours`
