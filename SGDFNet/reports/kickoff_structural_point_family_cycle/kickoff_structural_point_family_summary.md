# Kickoff Structural Point Family Summary

- Source state: `KICKOFF_MONTHHOUR_SELECTIVE_FAMILY_COMPLETE / kickoff_monthhour_selective_family_candidate_pool_exhausted`
- Frozen baseline artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Conclusion from the kickoff post-hoc families: capped and tail gains are easy to buy locally, but raw 9_16 remains stubborn.
- New family decision: stop local post-fit repair and return to point-signal trunk enhancement.
- Chosen base idea:
  - reuse the strongest structural near-miss pattern: TF + pressure + static graph + segment-local stats
  - add risk-hour weighting inside training instead of outside-model bias repair
- First candidates:
  - `structural_graph_seglocal_plus_risk_weight`
  - `structural_graph_seglocal_plus_risk_and_mild_tail_weight`
