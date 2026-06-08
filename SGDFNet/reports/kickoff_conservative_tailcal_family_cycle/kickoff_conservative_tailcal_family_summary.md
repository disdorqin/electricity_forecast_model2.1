# Kickoff Conservative Tail Calibration Family Summary

- Source state: `KICKOFF_TAILCAL_FAMILY_COMPLETE / kickoff_tailcal_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best kickoff tail-cal near-miss: `ktcal_001` with `full_year_rt_capped_smape=10.8849`, `segment_9_16_rt_capped_smape=15.3395`, and `top10_tail_rt_capped_smape=38.8824`.
- New family decision: keep the same kickoff near-miss baseline, but force a stricter trigger and shrunken bias to test whether raw damage came from over-correction rather than wrong direction.
- First candidates:
  - `kickoff_conservative_signed_tail_global_shrinked`
  - `kickoff_conservative_signed_tail_916_shrinked`
