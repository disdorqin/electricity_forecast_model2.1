# Best Model Landing Summary

- Model name: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`
- Config path: `C:\Users\37813\.codex\worktrees\ce61\elec\SGDFNet\configs\protocol_b_a0_j2_val_segment_bias_v1.yaml`
- Artifact path: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Official full-year capped RT SMAPE: `10.9067`
- Official full-year 9-16 capped RT SMAPE: `15.5042`
- Secondary raw full-year RT SMAPE: `20.7925`
- Secondary raw 9-16 RT SMAPE: `36.3431`
- Known risks:
  - raw SMAPE is still materially harsher than the capped business metric
  - the original artifact summary used the legacy capped implementation and should not be used for official landing acceptance
- Deployment notes:
  - keep the current artifact fixed for landing reporting
  - use the landing report package as the official source of capped metrics
- What should not be changed before landing:
  - no model retuning
  - no feature-contract changes
  - no new routing or hard-regime modules
