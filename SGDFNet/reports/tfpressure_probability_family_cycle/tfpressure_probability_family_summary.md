# TF+Pressure Probability Family Summary

- Source state: `STRUCTURAL_FAMILY_COMPLETE / structural_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best structural candidate remained rejected: `sfam_002` with `overall_rt_smape=20.9254` and `segment_9_16_rt_smape=36.4396`.
- New family decision: stop extending negative point-structure branches and test whether the strongest TF+pressure near-miss base improves probability outputs.
- Reason:
  - TF+pressure is still the strongest lightweight near-miss for point metrics
  - structural fusion stayed negative for the raw 9_16 objective
  - the next falsifiable question is whether better uncertainty / spike-ranking emerges on the stronger near-miss base
- First candidates:
  - `tfpressure_quantile_interval`
  - `tfpressure_spike_probability`
