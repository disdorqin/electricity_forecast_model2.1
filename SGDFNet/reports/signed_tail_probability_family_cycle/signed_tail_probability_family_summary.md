# Signed-Tail Probability Family Summary

- Source state: `TFPRESSURE_PROBABILITY_FAMILY_COMPLETE / tfpressure_probability_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best TF+pressure probability candidate remained rejected: `ppfam_001` with `mean_spike_average_precision=0.6321` and `mean_spike_recall_topk=0.6711`.
- New family decision: stop reusing unsigned spike probability and test whether sign-aware tail probabilities can exploit the tail-specialist clue from the error-gate branch.
- Reason:
  - `egfam_002` was bad as a main model but unusually strong on top-tail delta error
  - unsigned probability on top of TF+pressure did not beat the accepted interval module
  - the next falsifiable question is whether positive/negative tail ranking is the missing probability signal
- First candidates:
  - `signed_tail_dual_probability`
  - `signed_tail_dual_probability_plus_segment_local`
