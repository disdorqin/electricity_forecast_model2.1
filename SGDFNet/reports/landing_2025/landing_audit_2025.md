# SGDFNet Landing Audit 2025

- Status: `PASS_WITH_NOTES`
- Artifact audited: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Data source: `data\shandong_pmos_hourly.xlsx`
- Official metric: `rt_capped_smape` with floor-50 preprocessing (`actual/pred < 50 => 50`)

## Integrity

- Data integrity: `PASS`
- Protocol B integrity: `PASS`
- Feature leakage audit: `PASS`
- Prediction integrity: `FAIL`
- Reproducibility: `PASS`

## Official Targets

- Full-year RT capped SMAPE: `10.9067` vs target `< 25`
- Full-year 9-16 RT capped SMAPE: `15.5042` vs target `< 30`
- Full-year target met: `True`
- 9-16 target met: `True`
- Secondary raw full-year RT SMAPE: `20.7925`
- Secondary raw 9-16 RT SMAPE: `36.3431`

## Metric Recalculation Notes

- Raw metrics matched stored summary within tolerance: `True`
- Capped metric matched stored summary within tolerance: `False`
- Note: the artifact's original capped field used the legacy formula; this landing package recomputes the official floor-50 metric directly from `predictions.csv`.

## Worst Cases

- Worst 3 months by capped RT SMAPE: `[{'month': '2025-12', 'rt_capped_smape': 14.33458685673481, 'rt_smape': 29.054421923739703, 'rows': 744}, {'month': '2025-03', 'rt_capped_smape': 13.98411435562503, 'rt_smape': 25.67037293442696, 'rows': 744}, {'month': '2025-05', 'rt_capped_smape': 12.11844442375362, 'rt_smape': 23.86164172266001, 'rows': 744}]`
- Worst 3 months by raw RT SMAPE: `[{'month': '2025-12', 'rt_smape': 29.054421923739703, 'rt_capped_smape': 14.33458685673481, 'rows': 744}, {'month': '2025-03', 'rt_smape': 25.67037293442696, 'rt_capped_smape': 13.98411435562503, 'rows': 744}, {'month': '2025-02', 'rt_smape': 24.759254788144723, 'rt_capped_smape': 10.852358920383091, 'rows': 672}]`
- Worst 3 months for 9-16 capped RT SMAPE: `[{'month': '2025-12', 'rt_capped_smape': 25.714153052159347, 'rt_smape': 49.89172161064533, 'rows': 248}, {'month': '2025-07', 'rt_capped_smape': 20.432256577123965, 'rt_smape': 40.207036203659605, 'rows': 248}, {'month': '2025-01', 'rt_capped_smape': 16.611780692019046, 'rt_smape': 43.217731568807736, 'rows': 248}]`
- Worst 3 hours by capped RT SMAPE: `[{'hour': 10, 'rows': 365, 'rt_smape': 42.889044258892824, 'rt_capped_smape': 20.06077862452579}, {'hour': 9, 'rows': 365, 'rt_smape': 37.56581978968239, 'rt_capped_smape': 19.672823597375388}, {'hour': 15, 'rows': 365, 'rt_smape': 42.51972420564064, 'rt_capped_smape': 17.527703637996517}]`
- Failure concentration: `9_16-dominant`
