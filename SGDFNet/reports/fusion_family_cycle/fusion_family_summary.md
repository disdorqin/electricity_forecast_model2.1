# Fusion Family Summary

- Source state: `SIGNED_TAIL_CALIBRATION_FAMILY_COMPLETE / signed_tail_calibration_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best accepted point-repair branch: `stcfam_001` with `full_year_rt_capped_smape=10.8707` and `segment_9_16_rt_capped_smape=15.3246`.
- New family decision: unify the accepted signed-tail point repair with the accepted interval module into a release-style fusion package.
- Reason:
  - the current automation has produced one accepted point-repair branch and one accepted interval branch
  - they should be evaluated as a unified candidate rather than left as disconnected artifacts
  - the next falsifiable step is whether the bundle preserves both the point gains and uncertainty outputs cleanly
- First candidates:
  - `signed_tail_point_plus_interval_bundle`
  - `signed_tail_point_plus_interval_bundle_with_tailflag`
