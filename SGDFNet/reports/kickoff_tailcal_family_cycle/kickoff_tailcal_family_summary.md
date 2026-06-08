# Kickoff Tail Calibration Family Summary

- Source state: `KICKOFF_FOLLOWUP_CYCLE_COMPLETE / kickoff_followup_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best kickoff follow-up near-miss: `kfollow_001` with `overall_rt_capped_smape=10.8489`, `segment_9_16_rt_capped_smape=15.3226`, and `top10_tail_delta_mae=114.8867`.
- New family decision: attach a kickoff-specific signed-tail calibration branch on top of the best kickoff near-miss instead of reopening the legacy signed-tail family.
- Reason:
  - the kickoff TF+pressure+segment-local branch still regressed raw metrics
  - but it preserved a small capped and tail signal worth testing with a lighter post-fit correction
  - a fresh kickoff-specific family avoids historical ID collisions and keeps the automation chain moving forward
- First candidates:
  - `kickoff_signed_tail_probability_triggered_bias_global`
  - `kickoff_signed_tail_probability_triggered_bias_9_16_seg_local`
