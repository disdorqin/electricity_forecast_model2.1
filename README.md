# electricity_forecast_model2.1

> **30-Day Prediction Ledger + Dynamic Fusion Weights Production Pipeline**

本仓库在 2.0 基础上新增 **ledger 生产链路**：每天只做真实预测，连续积累 30 天预测账本（prediction ledger）和实际值账本（actual ledger），从第 31 天开始用前 30 天真实预测+实际值学习动态融合权重（Daily Ledger GEF），再融合当天预测并进入负电价分类器。

**旧 2.0 staged pipeline（model_stage / learner_stage / fuse_stage / classifier_stage / full）完整保留为 baseline。**

---

## 模型架构

| 模型 | 设备 | 目标 | 实现来源 |
|------|------|------|----------|
| LightGBM | CPU | Dayahead | EPF v1.0（`--epf-v1-root`） |
| TimesFM | CPU | Dayahead + Realtime | EPF v1.0（`--epf-v1-root`） |
| TimeMixer | GPU | Dayahead + Realtime | v2.0（内部 early stopping / calibration） |
| SGDFNet | CPU | Realtime | v2.0（内部 val_days 校准） |
| RT916 (SpikeFusionNet) | GPU | Realtime | v2.0（内部 DA-RT 联动） |

- **LightGBM / TimesFM**：完全复刻 EPF v1.0 最佳实现，通过 `runners/adapters/` 统一 adapter 调用。
- **TimeMixer / RT916 / SGDFNet**：保留内部 early stopping 和 calibration split，这些是模型内部优化，不是给融合学习器的 validation tap。
- **TimeMixer full_refit**：CLI 参数 `--timemixer-full-refit` 存在且默认开启，但实际 full refit 逻辑尚未在模型代码中实现（train+valid 全量重训后预测）。当前 RunConfig 已包含 `full_refit` 字段。
- **Realtime cutoff**：所有 realtime 模型通过 `--realtime-cutoff-hour 14` 统一控制，不再硬编码 15。

---

## 快速上手

### 安装与权重

```bash
pip install -r requirements.txt
# TimesFM 权重: models/timesFM/config.json + model.safetensors
```

### 核心命令

```bash
# 2.1 推荐：一键完整生产链路
python main.py --pipeline ledger_full --date 2026-02-24 \
    --epf-v1-root "D:\作业\大创_挑战杯_互联网\大学生创新创业计划\大创实现\其他资料\epf"

# 30 天历史回填（可交付前预跑，过夜）
python main.py --pipeline ledger_backfill --start 2026-01-25 --end 2026-02-23 \
    --epf-v1-root "D:\作业\大创_挑战杯_互联网\大学生创新创业计划\大创实现\其他资料\epf"

# 分阶段调试
python main.py --pipeline ledger_predict --date 2026-02-24 --epf-v1-root "..."
python main.py --pipeline ledger_weight --date 2026-02-24
python main.py --pipeline ledger_fuse --date 2026-02-24
python main.py --pipeline ledger_classifier --date 2026-02-24
```

### 旧 2.0 pipeline（保留）

```bash
python main.py 2026-06-19   # 等价于 --pipeline full
python main.py --pipeline model_stage --date 2026-06-19
python main.py --pipeline learner_stage --date 2026-06-19
python main.py --pipeline fuse_stage --date 2026-06-19
python main.py --pipeline classifier_stage --date 2026-06-19
```

---

## 关键业务口径

| 口径 | 值 |
|------|-----|
| Dayahead cutoff | D-1 全日数据 |
| Realtime cutoff | **D-1 14:00**（`--realtime-cutoff-hour 14`） |
| TimesFM 设备 | **CPU**（不入 GPU queue） |
| LightGBM/TimesFM EPF v1.0 | **exact** 模式（`--epf-v1-mode exact`），无 `--epf-v1-root` 直接失败 |
| TimeMixer full_refit | train+valid 全量 refit（`--timemixer-full-refit`） |
| RT916 realtime | AMP 训练 / FP32 推理导出（`asof_hour=14`） |
| SGDFNet | `decision_hour=14`，val_days 仅用于内部校准 |
| 权重学习 | BGEW daily from ledger，day_gate 0.3-0.85（含最近一周 boost） |
| 主指标 | SMAPE-floor50（per-value clip）+ 0.7*smape + 0.3*mae_percent |

---

## 输出目录结构

```
outputs/
  ledger/                         # 跨日期累积账本
    dayahead/
      prediction/prediction_ledger.parquet + .csv
      actual/actual_ledger.parquet + .csv
      weight/weight_history.csv
    realtime/
      prediction/prediction_ledger.parquet + .csv
      actual/actual_ledger.parquet + .csv
      weight/weight_history.csv

  runs/
    YYYY-MM-DD/                   # 单日运行目录
      run_manifest.json           # 运行清单
      logs/pipeline.log
      dayahead/
        prediction/all_model_predictions_long.csv
        weight/weights.csv + dynamic_weight_trace.csv + candidate_metrics.csv + coverage_report.csv
        fuse/fused_predictions.csv + fused_debug.csv
        final/dayahead_final_predictions.csv
      realtime/
        prediction/all_model_predictions_long.csv
        weight/weights.csv + ...
        fuse/fused_predictions.csv + fused_debug.csv
        final/realtime_final_predictions.csv + realtime_final_predictions_corrected.csv
      final/
        dayahead_final_predictions.csv
        realtime_final_predictions.csv
        realtime_final_predictions_corrected.csv
        submission_ready.csv
```

命名约定：
- **prediction** = 各模型真实预测
- **weight** = 从过去 30 天账本学出的权重
- **fuse** = 加权融合结果
- **final** = 最终交付文件
- **ledger** = 跨日期累计的预测/实际值账本

---

## SMAPE 计算口径

严格按 `docs/metrics_calculation.md`：

```python
y_clip  = max(y_true, 50)
pred_clip = max(y_pred, 50)
SMAPE = mean(|pred_clip - y_clip| / ((|pred_clip| + |y_clip|) / 2)) * 100
```

GEF learner 损失：
```python
loss = 0.7 * smape_floor50 + 0.3 * mae_percent
mae_percent = 100 * MAE / max(median(|y_true_clip|), 50)
```

---

## 新 CLI 参数（2.1 ledger）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--epf-v1-root` | None | **[必需]** EPF v1.0 LightGBM/TimesFM 仓库路径 |
| `--epf-v1-mode` | `exact` | `exact`（忠实 v1）或 `cutoff_safe`（截断数据） |
| `--allow-v2-fallback` | False | 允许 LightGBM/TimesFM fallback 到 2.0 |
| `--realtime-cutoff-hour` | `14` | Realtime 截止小时（D-1 14:00） |
| `--recent-week-boost` | True | 最近一周 day_gate 平滑增强 |
| `--recent-week-max-gate` | `0.85` | day_gate 上限 |
| `--timemixer-epochs` | `80` | TimeMixer 训练轮数 |
| `--timemixer-patience` | `15` | Early stopping 耐心值 |
| `--timemixer-batch-size` | `16` | 批大小 |
| `--timemixer-full-refit` | True | train+valid 全量 refit |
| `--timemixer-seeds` | `42` | 随机种子 |
| `--ledger-root` | `outputs/ledger` | 账本根目录 |
| `--runs-root` | `outputs/runs` | 单日运行根目录 |
| `--allow-missing-models` | False | 允许缺少模型继续 |
| `--allow-equal-weight-fallback` | False | 允许无权重时使用等权 |
| `--strict-classifier` | False | 分类器失败时中断 pipeline |

---

## Runtime 目标

| 任务 | 目标 |
|------|------|
| 单日 `ledger_full` | **~30 分钟** |
| 30 天 `ledger_backfill` | 过夜运行 |
| Dayahead 3 模型 | CPU queue 并行 |
| Realtime 4 模型 | GPU queue 串行 |

---

## 调度策略

```
CPU queue (max_workers=2):
  LightGBM v1.0
  TimesFM v1.0 CPU
  SGDFNet
  数据处理

GPU queue (max_workers=1, serial):
  TimeMixer
  RT916
```

## 跨模型文档

- [`docs/metrics_calculation.md`](./docs/metrics_calculation.md) — SMAPE, MAPE, MAE, RMSE 等
- [`docs/实验运行约定.md`](./docs/实验运行约定.md) — 实验流程
- [`docs/项目执行逻辑与陪跑步骤对齐.md`](./docs/项目执行逻辑与陪跑步骤对齐.md) — 陪跑步骤

## 许可

MIT License
