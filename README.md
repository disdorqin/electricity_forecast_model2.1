# electricity_forecast_model2.1

> **30-Day Prediction Ledger + Dynamic BGEW Fusion Weights — Production Pipeline for Shandong Electricity Spot Price Forecasting**

本仓库在 2.0 基础上新增 **ledger 生产链路**：每天只做真实预测，连续积累 30 天预测账本（prediction ledger）和实际值账本（actual ledger），从第 31 天开始用前 30 天真实预测+实际值学习动态融合权重（Daily Ledger GEF），再融合当天预测并进入负电价分类器。

**旧 2.0 staged pipeline** 已归档到 `_archive/legacy_staged_pipeline/`。旧 TimesFM wrapper 已归档到 `_archive/legacy_timesfm_wrapper/`。使用 `ledger_*` 系列 pipeline 作为正式入口。

---

## 当前正式链路

```
ledger_backfill  →  ledger_predict  →  ledger_weight  →  ledger_fuse  →  ledger_classifier  →  final_outputs
(30天 backfill)     (7 模型预测)       (BGEW 权重学习)     (加权融合)        (负电价分类器)         (最终交付文件)
```

| 阶段 | pipeline 参数 | 核心功能 |
|------|--------------|---------|
| 1. 30天回填 | `ledger_backfill` | 回填历史 N 天预测+实际值到 ledger |
| 2. 预测 | `ledger_predict` | 所有模型跑 24h 预测，写入 ledger |
| 3. 权重学习 | `ledger_weight` | 从过去 30 天 ledger 学习 BGEW 权重 |
| 4. 融合 | `ledger_fuse` | 用学出的权重融合各模型预测 |
| 5. 分类器 | `ledger_classifier` | 对 realtime 极端价格分类校正 |
| 6. 最终输出 | `ledger_full` (1-5一次性) | 生成 submission_ready.csv |

---

## 模型组成

| 模型 | 设备 | 目标 | 实现来源 |
|------|------|------|----------|
| LightGBM | CPU | Dayahead | EPF v1.0（`--epf-v1-root`） |
| TimesFM | CPU | Dayahead + Realtime | EPF v1.0（`--epf-v1-root`） |
| TimeMixer | GPU | Dayahead + Realtime | v2.0 内部 early stopping / calibration |
| SGDFNet | CPU | Realtime | v2.0 内部 val_days 校准 |
| RT916 (SpikeFusionNet) | GPU | Realtime | v2.0 内部 DA-RT 联动 |

- **LightGBM / TimesFM**：通过 `runners/adapters/` 调用 EPF v1.0 实现。
- **TimeMixer / RT916 / SGDFNet**：保留内部 early stopping 和 calibration split。
- **TimesFM 在 ledger pipeline 中的入口**：`runners/adapters/timesfm_v1.py` → `TimesFMBackend.infer.predict_price_for_date()` → `TimesFMBackend.price_forecast_copy_分时段预测.forecast_next_day()`。
- **Realtime cutoff**：所有 realtime 模型通过 `--realtime-cutoff-hour 14` 统一控制，D-1 14:00 截止。

---

## 目录结构

```
cli/                  CLI 参数定义层（main.py 使用 cli/parser.py）
pipelines/            正式链路编排层（ledger_*, prediction_ledger）
runners/              模型 registry + EPF v1 adapter 层
runtime/              CPU/GPU 调度层（model device routing）
fusion/               融合核心：
  - learners/daily_ledger_gef.py  → BGEW 权重学习器
  - apply_daily_ledger_weights.py → 权重应用
  - classifier_bridge.py          → 负电价分类器
  - adapters/                     → 各模型 adapter
lightGBM/             LightGBM 模型实现
TimesFMBackend/          TimesFM 后端（EPF v1 实现；注意：不是 TensorFlow）
TimeMixer/            TimeMixer 模型实现
RT916_SpikeFusionNet/ RT916 模型实现
SGDFNet/              SGDFNet 模型实现
ExtremPriceClf/       极端价格分类器
utils/                通用工具（business_day.py, reproducibility.py, io.py）
scripts/              验证/审计脚本（env_check, verify_final_pipeline, reproducibility 等）
data/                 本地输入数据（.gitignore 忽略，不提交 Git）
outputs/              本地运行产物（.gitignore 忽略，不提交 Git）
docs/                 项目文档
```

---

## 环境安装

### 前置条件

- Python >= 3.10
- CUDA 可用 GPU（TimeMixer / RT916 必需）
- 约 10 GB 磁盘空间（含模型权重缓存）

### 安装步骤

```bash
# 1. 创建 conda 环境
conda create -n epf-2 python=3.11
conda activate epf-2

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 TF/（TimesFM 本地包）
pip install -e TF/
```

### 依赖说明

完整依赖见 `requirements.txt`。关键包：

| 包 | 用途 | 必需 |
|----|------|------|
| pandas, numpy | 数据处理 | 是 |
| torch>=2.0 | 深度学习后端 | 是 |
| lightgbm>=4.0 | LightGBM 模型 | 是 |
| scikit-learn | 评估指标 | 是 |
| pyarrow | Parquet I/O | 是 |
| openpyxl | Excel 读写 | 是 |
| huggingface_hub | TimesFM 权重下载 | 是 |
| jax | TimesFM xreg 协变量回归 | 可选 |

---

## 数据放置

模型推理需要输入数据文件，默认路径为 `data/shandong_pmos_hourly.xlsx`。

```text
data/
  shandong_pmos_hourly.xlsx   ← 默认输入数据文件
```

`data/` 目录已被 `.gitignore` 忽略，不会提交到 Git。

---

## 一键运行命令

```powershell
# 完整生产链路（自包含运行，无需外部 EPF 仓库）
conda run -n epf-2 python main.py 2026-02-24 ^
    --data-path data/shandong_pmos_hourly.xlsx ^
    --seed 42

# 30 天历史回填
conda run -n epf-2 python main.py --pipeline ledger_backfill ^
    --start 2026-01-25 --end 2026-02-23 ^
    --data-path data/shandong_pmos_hourly.xlsx ^
    --seed 42

# Smoke 快速测试
conda run -n epf-2 python main.py --pipeline ledger_smoke --date 2026-02-24 ^
    --smoke-training-months 3 --smoke-timemixer-epochs 3 --smoke-timemixer-patience 1 ^
    --seed 42 --deterministic --force
```

---

## 分阶段运行命令

```powershell
# 仅预测
conda run -n epf-2 python main.py --pipeline ledger_predict --date 2026-02-24

# 仅权重学习（需先跑过 predict）
conda run -n epf-2 python main.py --pipeline ledger_weight --date 2026-02-24

# 仅融合（需先跑过 weight）
conda run -n epf-2 python main.py --pipeline ledger_fuse --date 2026-02-24

# 仅分类器（需先跑过 fuse）
conda run -n epf-2 python main.py --pipeline ledger_classifier --date 2026-02-24
```

> Note: `--epf-v1-root` is optional for legacy compatibility only. Normal runs use bundled `lightGBM/` and `TimesFMBackend/`.

---

## 输出结构

```
outputs/
  ledger/                         # 跨日期累积账本
    dayahead/prediction/prediction_ledger.parquet + .csv
    dayahead/actual/actual_ledger.parquet + .csv
    realtime/prediction/prediction_ledger.parquet + .csv
    realtime/actual/actual_ledger.parquet + .csv

  runs/YYYY-MM-DD/
    run_manifest.json             # 完整运行元信息
    dayahead/
      prediction/all_model_predictions_long.csv
      weight/weights.csv + dynamic_weight_trace.csv + coverage_report.csv + candidate_metrics.csv
      fuse/fused_predictions.csv + fused_debug.csv
      final/dayahead_final_predictions.csv
    realtime/
      prediction/all_model_predictions_long.csv
      weight/weights.csv + ...
      fuse/fused_predictions.csv + fused_debug.csv
      final/realtime_final_predictions_corrected.csv
    final/
      submission_ready.csv        ← 最终交付
```

命名约定：**prediction**（模型预测）→ **weight**（权重）→ **fuse**（融合）→ **final**（交付）。注意使用 `fuse/`，不是 `fused/`。

详细说明见 [`docs/OUTPUT_CONVENTION.md`](docs/OUTPUT_CONVENTION.md)。

---

## 缓存与 force 机制

- **ledger_predict**：模型预测文件已存在时自动缓存跳过（cache HIT）。加 `--force` 强制重跑所有模型。
- **ledger_weight**：始终重跑（从 ledger 读取最新训练数据）。
- **ledger_fuse**：根据 weight + prediction 文件重跑。
- **ledger_classifier**：根据 fuse 输出重跑。
- **ledger_full**：按 1-5 阶段顺序执行，各阶段复用缓存。

---

## 30 天 ledger/backfill 说明

`ledger_backfill` 按日期顺序逐天调用 `ledger_predict`，将各模型预测追加到 prediction ledger。累计 30 天后，正式 D 日可以用前 30 天的真实预测+实际值学习权重。

```powershell
# 示例：回填 2026-01-25 至 2026-02-23
conda run -n epf-2 python main.py --pipeline ledger_backfill ^
    --start 2026-01-25 --end 2026-02-23 ^
    --epf-v1-root "path\to\epf-v1"
```

- 每完成一天，预测写入 `outputs/ledger/{task}/prediction/prediction_ledger.parquet`。
- 实际值写入 `outputs/ledger/{task}/actual/actual_ledger.parquet`。
- 预计运行时间：过夜（取决于模型数量和 GPU 串行排队）。

---

## 动态权重学习器说明

DailyLedgerGEF（`fusion/learners/daily_ledger_gef.py`）是核心权重学习器：

- **初始化**：所有模型等权。
- **顺序更新**：从 D-30（age_days=30）到 D-1（age_days=1）逐日更新。
- **day_gate**：线性衰减，0.3 到 0.85，最近一周 boost 到 0.85。
- **损失函数**：`0.7 × smape_floor50 + 0.3 × mae_percent`
  - smape_floor50：per-value clip at 50，symmetric MAPE
  - mae_percent：100 × MAE / max(median(y_true_clip), 50)
- **分时段**：dayahead/realtime 均按 1-8、9-16、17-24 三时段独立学习权重。
- **证据收缩（evidence shrinkage）**：防止过拟合于稀疏数据。

---

## classifier 说明

`fusion/classifier_bridge.py` 对 realtime 融合预测进行极端价格分类校正：

- **校正类型**：将融合预测中的极端低价（mid-low）修正为 -80.00。
- **输入**：realtime fused_predictions.csv（24h）。
- **输出**：realtime_final_predictions_corrected.csv。
- **fallback 机制**：classifier_bridge 失败时自动 fallback 到副分类器。

---

## 验证脚本

| 脚本 | 用途 | 命令 |
|------|------|------|
| `scripts/env_check.py` | 环境依赖检查 | `python scripts/env_check.py` |
| `scripts/verify_final_pipeline.py` | 已有输出验证 | `python scripts/verify_final_pipeline.py --date YYYY-MM-DD` |
| `scripts/check_reproducibility.py` | 可复现性检查 | `python scripts/check_reproducibility.py YYYY-MM-DD --seed 42 --deterministic --epf-v1-root ...` |
| `scripts/check_timemixer_alignment.py` | TimeMixer 时间对齐检查 | `python scripts/check_timemixer_alignment.py --date YYYY-MM-DD` |
| `scripts/verify_smoke.py` | Smoke 结果验证 | `python scripts/verify_smoke.py` |

---

## 关键业务口径

| 口径 | 值 |
|------|-----|
| Dayahead cutoff | D-1 全日数据 |
| Realtime cutoff | D-1 14:00（`--realtime-cutoff-hour 14`） |
| TimesFM 设备 | CPU（不入 GPU queue） |
| LightGBM/TimesFM EPF v1 mode | `exact`（默认）；无 `--epf-v1-root` 直接失败 |
| TimeMixer full_refit | train+valid 全量 refit（默认开启） |
| 权重学习 period | 1-8, 9-16, 17-24（三时段） |
| day_gate 范围 | 0.3–0.85（含最近一周 boost） |
| 学习器损失 | 0.7×smape_floor50 + 0.3×mae_percent |
| 权重和 | 每个 period 内部归一化为 1.0 |
| 融合输出字段 | `y_fused`（融合值） |
| final 输出字段 | `dayahead_price`, `realtime_price` |

---

## 不提交到 Git 的文件

以下文件/目录已通过 `.gitignore` 忽略，不会提交到 Git：

```text
data/                          # 输入数据
outputs/                       # 所有运行产物
models/                        # 模型权重缓存
daily_runs/                    # 旧 pipeline 输出
fusion_runs/                   # 旧融合实验输出
.claude/                       # Claude Code 持久化
.workbuddy/                    # Workbuddy 工作区
__pycache__/                   # Python 缓存
*.log                          # 日志
```

---

## 调度策略

```
CPU queue (max_workers=2):
  LightGBM v1.0  — dayahead
  TimesFM v1.0   — dayahead + realtime (固定 CPU)
  SGDFNet        — realtime

GPU queue (max_workers=1, serial):
  TimeMixer      — dayahead + realtime
  RT916          — realtime
```

---

## 常见问题

**Q: Do I need the developer's old EPF folder (`--epf-v1-root`)?**
A: No. The delivery version is self-contained. LightGBM and TimesFMBackend are bundled in this repository. The `--epf-v1-root` option is only retained for legacy compatibility and should not be used for normal delivery runs.

**Q: `EPF v1 root not found` 错误？**
A: 旧版 ledger pipeline 要求 `--epf-v1-root`。当前交付版已是自包含运行，不再需要外部 EPF 仓库。如果看到该错误，请更新代码到最新 main 分支。

**Q: CUDA out of memory？**
A: GPU queue 默认串行（max_gpu_workers=1）。如果仍有 OOM，减小 batch size（`--timemixer-batch-size 8`）。

**Q: 如何只重跑 fuse，不重跑模型？**
A: 直接运行 `ledger_fuse`，它会读取已有的 prediction 和 weight 文件。

**Q: `TF/` 是 TensorFlow 吗？**
A: 不是。`TimesFMBackend/` 是当前 ledger pipeline 使用的 TimesFM 实现后端（EPF v1.0），包含完整 timesfm_2p5 PyTorch+Flax 代码。`TimesFMBackend/` 不是 TensorFlow。

---

## 许可

MIT License
