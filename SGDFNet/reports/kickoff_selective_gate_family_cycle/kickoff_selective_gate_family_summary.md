# Kickoff Selective Gate Family Summary

- Source state: `KICKOFF_CONSERVATIVE_TAILCAL_FAMILY_COMPLETE / kickoff_conservative_tailcal_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best conservative near-miss: `kctcal_002` with `full_year_rt_capped_smape=10.8575`, `segment_9_16_rt_capped_smape=15.3551`, and `top10_tail_rt_capped_smape=38.9236`.
- New family decision: stop shrinking bias blindly and switch to a validation-gated selective correction mechanism.
- Mechanism:
  - require predicted-sign consistency
  - require large predicted |delta| cells only
  - require val-side subgroup improvement before enabling a bias
- First candidates:
  - `kickoff_selective_signed_tail_global_valgated`
  - `kickoff_selective_signed_tail_916_valgated`
