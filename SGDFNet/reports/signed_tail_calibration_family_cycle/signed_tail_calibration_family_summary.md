# Signed-Tail Calibration Family Summary

- Source state: `SIGNED_TAIL_PROBABILITY_FAMILY_COMPLETE / signed_tail_probability_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best signed-tail probability candidate remained rejected: `stpfam_002` with `mean_signed_average_precision=0.5737` and `mean_signed_recall_topk_9_16=0.5963`.
- New family decision: convert the signed-tail ranking signal into a leakage-safe point calibration branch.
- Reason:
  - signed-tail ranking improved relative to the accepted interval module
  - the signal was still not strong enough to justify a standalone probability keep
  - the next falsifiable step is to use signed-tail probability only as a trigger for val-learned bias correction
- First candidates:
  - `signed_tail_probability_triggered_bias`
  - `signed_tail_probability_triggered_bias_9_16_seg_local`
