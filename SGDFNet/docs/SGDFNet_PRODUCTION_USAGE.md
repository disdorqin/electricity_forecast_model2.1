# SGDFNet Production Usage

## Current entrypoint choice

- For corrected realtime evaluation, prefer `SGDFNet/scripts/run_protocol_b_cutoff.py`.
- `SGDFNet/scripts/run_protocol_b.py` is retained for historical research and landing reproduction, not as the default corrected realtime path.

## Purpose

SGDFNet is packaged here as a command-line runnable realtime electricity price forecasting model based on the accepted Protocol B landing configuration.

## Official landing metric

- official metric: `rt_capped_smape`
- official formula: floor both `actual` and `pred` to `50` before SMAPE

## Required data columns

- `时刻`
- `日前电价`
- `实时电价`
- forecast columns:
  - `地方电厂总加预测值`
  - `联络线受电负荷预测值`
  - `风电总加预测值`
  - `光伏总加预测值`
  - `核电总加预测值`
  - `自备机组总加预测值`
  - `试验机组总加预测值`
  - `直调负荷预测值`
  - `竞价空间预测值`
  - `新能源总加预测值`
- actual columns:
  - `地方电厂总加实际值`
  - `联络线受电负荷实际值`
  - `风电总加实际值`
  - `光伏总加实际值`
  - `核电总加实际值`
  - `自备机组总加实际值`
  - `试验机组总加实际值`
  - `直调负荷实际值`
  - `竞价空间实际值`
  - `新能源总加实际值`

## Commands

### Train

```bash
python scripts/runners/run_sgdfnet_realtime.py \
  --mode train \
  --config SGDFNet/configs/production_sgdfnet_realtime.yaml \
  --data data/shandong_pmos_hourly.xlsx \
  --train-end 2024-12-31 \
  --val-days 30 \
  --output-dir outputs/RT916_SpikeMarketLab/production_runs/train_001
```

### Predict

```bash
python scripts/runners/run_sgdfnet_realtime.py \
  --mode predict \
  --config SGDFNet/configs/production_sgdfnet_realtime.yaml \
  --data data/shandong_pmos_hourly.xlsx \
  --checkpoint outputs/RT916_SpikeMarketLab/production_runs/train_001/checkpoint.joblib \
  --predict-start 2025-01-01 \
  --predict-end 2025-01-31 \
  --output-dir outputs/RT916_SpikeMarketLab/production_runs/predict_2025_01
```

### Train + predict

```bash
python scripts/runners/run_sgdfnet_realtime.py \
  --mode train_predict \
  --config SGDFNet/configs/production_sgdfnet_realtime.yaml \
  --data data/shandong_pmos_hourly.xlsx \
  --train-end 2024-12-31 \
  --val-days 30 \
  --predict-start 2025-01-01 \
  --predict-end 2025-01-31 \
  --output-dir outputs/RT916_SpikeMarketLab/production_runs/tp_2025_01
```

### Rolling 2025

```bash
python scripts/runners/run_sgdfnet_realtime.py \
  --mode rolling_2025 \
  --config SGDFNet/configs/production_sgdfnet_realtime.yaml \
  --data data/shandong_pmos_hourly.xlsx \
  --output-dir outputs/RT916_SpikeMarketLab/production_runs/rolling_2025
```

### Smoke

```bash
python scripts/runners/run_sgdfnet_realtime.py \
  --mode smoke \
  --config SGDFNet/configs/production_sgdfnet_realtime.yaml \
  --data data/shandong_pmos_hourly.xlsx \
  --output-dir outputs/RT916_SpikeMarketLab/production_runs/smoke
```

## Expected outputs

### Train

- `config_snapshot.json`
- `feature_manifest.csv`
- `train_log.csv`
- `checkpoint.joblib`
- `train_summary.json`

### Predict

- `config_snapshot.json`
- `predictions.csv`
- `prediction_summary.json`
- `metrics.json` when actuals are available
- `segment_metrics.csv` when actuals are available
- `hourly_metrics.csv` when actuals are available
- `run_audit.json`

### Rolling 2025

- `config_snapshot.json`
- `monthly_overall_smape_2025.csv`
- `monthly_segment_smape_2025.csv`
- `hourly_smape_2025.csv`
- `target_check_2025.json`
- `predictions_2025.csv`
- `rolling_summary.json`
- `run_audit.json`

## Known risks

- official capped SMAPE must use the floor-50 rescored formula
- some legacy research artifacts used a different capped-metric implementation
- landing model behavior should not be changed before a new landing audit
