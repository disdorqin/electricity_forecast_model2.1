# LANDING FREEZE

- Accepted landing model: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`
- Config: `SGDFNet\configs\protocol_b_a0_j2_val_segment_bias_v1.yaml`
- Artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Official full-year capped RT SMAPE: `10.9067`
- Official full-year 9_16 capped RT SMAPE: `15.5042`
- Raw full-year RT SMAPE: `20.7925`
- Raw 9_16 RT SMAPE: `36.3431`
- Known risks:
  - 9_16-dominant failure concentration
  - worst capped months: `[{'month': '2025-12', 'rt_capped_smape': 14.33458685673481, 'rt_smape': 29.054421923739703, 'rows': 744}, {'month': '2025-03', 'rt_capped_smape': 13.98411435562503, 'rt_smape': 25.67037293442696, 'rows': 744}, {'month': '2025-05', 'rt_capped_smape': 12.11844442375362, 'rt_smape': 23.86164172266001, 'rows': 744}]`
  - worst 9_16 capped months: `[{'month': '2025-12', 'rt_capped_smape': 25.714153052159347, 'rt_smape': 49.89172161064533, 'rows': 248}, {'month': '2025-07', 'rt_capped_smape': 20.432256577123965, 'rt_smape': 40.207036203659605, 'rows': 248}, {'month': '2025-01', 'rt_capped_smape': 16.611780692019046, 'rt_smape': 43.217731568807736, 'rows': 248}]`
  - worst capped hours: `[{'hour': 10, 'rows': 365, 'rt_smape': 42.889044258892824, 'rt_capped_smape': 20.06077862452579}, {'hour': 9, 'rows': 365, 'rt_smape': 37.56581978968239, 'rt_capped_smape': 19.672823597375388}, {'hour': 15, 'rows': 365, 'rt_smape': 42.51972420564064, 'rt_capped_smape': 17.527703637996517}]`
- Freeze rules:
  - future V2 experiments must not overwrite this model or artifact
  - every V2 result must be compared against this frozen landing model
