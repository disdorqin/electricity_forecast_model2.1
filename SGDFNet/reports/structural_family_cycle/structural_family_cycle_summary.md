# Structural Family Cycle Summary

- Source state: `ERRORGATE_FAMILY_COMPLETE / errorgate_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Best prior tail specialist (still rejected as main model): `egfam_002` with `top10_tail_delta_mae=105.7699` and `overall_rt_smape=23.0284`.
- New family decision: stop adding lightweight calibration patches and return to the point-signal core with structural feature fusion on top of TF+pressure.
- Reason:
  - TF+pressure remains the strongest near-miss base for the main objective
  - graph-like structural features were negative on the old base, but were never tested on the stronger TF+pressure base
  - the next main-model question is whether structural feature interactions improve raw 9_16 without depending on post-fit patching
- First candidates:
  - `tf_pressure_static_group_graph`
  - `tf_pressure_static_group_graph_plus_segment_local`
