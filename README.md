# Electricity Forecast Delivery Pipeline v2.1

山东电力现货价格预测系统：**多模型预测 + 30 天 Ledger 动态权重融合 + Realtime 极端价格分类校正 + 交付质量门禁 + 应急 fallback**。

最终交付文件为：

```text
outputs/runs/YYYY-MM-DD/final/submission_ready.csv
```

该文件包含未来 24 小时的日前价格（`dayahead_price`）和实时价格（`realtime_price`）预测。

---

## 1. 当前交付状态

本仓库已经完成最终链路验证，详见：[`docs/FINAL_VALIDATION_SUMMARY.md`](docs/FINAL_VALIDATION_SUMMARY.md)。

最终验证结论：

| 验证项 | 结果 |
|---|---|
| 静态检查 | PASS |
| 单日完整链路 | NORMAL，5/5 阶段完成，7/7 模型完成 |
| 30 天权重训练覆盖 | Dayahead 2160/2160，Realtime 2880/2880 |
| 三天 Range 链路 | NORMAL，3/3 天完成，0 degraded，0 failed |
| 故障注入 | 4/4 PASS |
| 假成功检测 | 0 false success |
| 正式输出污染 | 无，实验使用隔离 runs/ledger |

一句话：**工程链路、交付质量门禁、fallback 和 range 模式均已通过最终验证。**

---

## 2. 一分钟理解整体链路

每日正式预测由 `ledger_full` 串联 5 个阶段：

```text
ledger_predict  ->  ledger_weight  ->  ledger_fuse  ->  ledger_classifier  ->  final_outputs
7 模型预测          30 天权重学习       加权融合           Realtime 极端价格校正     交付文件
```

核心设计：

1. `ledger_predict` 跑所有模型并写入跨日期 prediction ledger。
2. `ledger_weight` 读取过去 30 天 prediction ledger + actual ledger，学习动态融合权重。
3. `ledger_fuse` 使用权重对当天各模型预测逐小时融合。
4. `ledger_classifier` 只对 realtime 融合结果做极端低价校正。
5. `final_outputs` 输出 24 行 `submission_ready.csv`。
6. postflight 会校验最终文件格式、行数、小时、列名和状态。
7. 如果正常链路失败，但历史数据可用，系统会生成 `DEGRADED_DELIVERED` 应急交付文件，并明确标记，不伪装成正常成功。

---

## 3. 目录结构

| 路径 | 说明 |
|---|---|
| `main.py` | 统一入口，默认执行单日完整链路 `ledger_full` |
| `cli/` | 命令行参数解析 |
| `pipelines/` | 正式链路编排：predict / weight / fuse / classifier / full / range / fallback |
| `runners/` | 模型 registry 和 adapter |
| `runtime/` | CPU/GPU 并行调度 |
| `fusion/` | BGEW 动态权重学习、融合和分类器桥接 |
| `lightGBM/` | bundled LightGBM v1.0-compatible 实现 |
| `TimesFMBackend/` | bundled TimesFM v1.0-compatible 后端；不是 TensorFlow |
| `TimeMixer/` | TimeMixer 模型实现 |
| `SGDFNet/` | SGDFNet 模型实现 |
| `RT916_SpikeFusionNet/` | RT916 / SpikeFusionNet 模型实现 |
| `ExtremPriceClf/` | Realtime 极端价格分类器 |
| `scripts/` | 验证、检查、稳定性测试脚本 |
| `docs/` | 技术文档和最终验证报告 |
| `fixtures/seed_ledger/` | 示例 seed ledger，用于首次运行时快速初始化 30 天账本 |

运行产物默认不进入 Git：

| 路径 | 说明 |
|---|---|
| `outputs/ledger/` | 跨日期 prediction/actual ledger，用于 30 天权重学习 |
| `outputs/runs/YYYY-MM-DD/` | 单日正式运行结果 |
| `outputs/runs/range_START_to_END/` | 区间运行 manifest 和 summary |
| `outputs/smoke/` | 快速 smoke 测试输出，不污染正式 ledger |
| `data/` | 输入数据，本地放置，不提交 Git |
| `models/` | 模型权重和缓存，本地生成或下载，不提交 Git |

详细输出约定见：[`docs/OUTPUT_CONVENTION.md`](docs/OUTPUT_CONVENTION.md)。

---

## 4. 模型组成

| 模型 | 设备 | 任务 | 说明 |
|---|---|---|---|
| LightGBM | CPU | Dayahead | 使用 bundled `lightGBM/`，保持 1.0-compatible 行为 |
| TimesFM | CPU | Dayahead + Realtime | 使用 bundled `TimesFMBackend/`，保持 1.0-compatible 行为 |
| TimeMixer | GPU | Dayahead + Realtime | 2.x 内部训练 / early stopping / calibration |
| SGDFNet | CPU | Realtime | 2.x Realtime 模型 |
| RT916 / SpikeFusionNet | GPU | Realtime | 2.x Realtime 极端波动模型 |

队列默认：

```text
CPU queue, max_workers=2:
  LightGBM, TimesFM, SGDFNet

GPU queue, max_workers=1:
  TimeMixer, RT916
```

说明：

- LightGBM 和 TimesFM 是 1.0 模型的 bundled 兼容接入，部署人员不需要配置额外模式。
- 正常交付不需要外部 EPF v1.0 仓库。
- GPU 默认串行，降低 CUDA OOM 风险。

---

## 5. 环境安装

推荐 Python 3.10 或 3.11。Windows + CUDA 环境已验证。

```bash
conda create -n epf-2 python=3.10 -y
conda activate epf-2
pip install -r requirements.txt
```

GPU 用户建议先按本机 CUDA 版本安装 PyTorch GPU 版，再安装其他依赖。

TimesFM 当前验证环境：

```text
timesfm==2.0.1
TimesFM_2p5_200M_torch
Windows-compatible, no JAX runtime required for the validated setup
```

快速环境检查：

```bash
python scripts/env_check.py
```

---

## 6. 数据准备

默认输入路径：

```text
data/shandong_pmos_hourly.xlsx
```

必需字段：

| 字段 | 说明 |
|---|---|
| `ds` 或 `时刻` / `时间` | 小时级时间戳 |
| `日前电价` | Dayahead 实际电价 |
| `实时电价` | Realtime 实际电价 |

建议：

- 小时级数据，每天 24 点。
- 业务小时口径：`hour 24 = D+1 00:00`。
- 至少覆盖正式预测日前 30 天；建议保留更长历史。
- `data/` 不提交 Git，由部署方放置。

---

## 7. 首次运行前：准备 30 天 Ledger

`ledger_weight` 必须读取 D-30 到 D-1 的完整 prediction ledger + actual ledger。现在已经有 hard gate：如果 30 天账本缺天、缺模型或缺小时，系统会拒绝学习权重，避免假成功。

### 方式 A：使用 seed ledger 快速初始化

仓库提供示例 seed ledger：

```bash
mkdir -p outputs/ledger
cp -r fixtures/seed_ledger/* outputs/ledger/
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force outputs/ledger | Out-Null
Copy-Item fixtures/seed_ledger/* outputs/ledger -Recurse -Force
```

### 方式 B：完整 Backfill

Backfill 只负责回填历史 prediction ledger 和 actual ledger，不生成最终交付文件。

```powershell
python main.py --pipeline ledger_backfill ^
  --start 2026-01-25 ^
  --end 2026-02-23 ^
  --data-path data/shandong_pmos_hourly.xlsx ^
  --max-cpu-workers 2 ^
  --max-gpu-workers 1 ^
  --seed 42 ^
  --deterministic
```

Backfill 不做：

- 不学习权重；
- 不融合；
- 不跑分类器；
- 不生成 `submission_ready.csv`。

---

## 8. 单日正式预测

最简单命令：

```bash
python main.py 2026-02-24
```

推荐显式命令：

```powershell
python main.py 2026-02-24 ^
  --data-path data/shandong_pmos_hourly.xlsx ^
  --max-cpu-workers 2 ^
  --max-gpu-workers 1 ^
  --seed 42 ^
  --deterministic
```

成功时输出：

```text
outputs/runs/2026-02-24/final/submission_ready.csv
```

交付文件应满足：

| 检查项 | 要求 |
|---|---|
| 行数 | 24 |
| 列名 | `business_day, ds, hour_business, period, dayahead_price, realtime_price` |
| 小时 | `hour_business` = 1..24 |
| hour 24 | `D+1 00:00` |
| 价格列 | numeric，非空 |
| 多余列 | 不允许 `_x` / `_y` 后缀列 |

验证：

```bash
python scripts/verify_final_pipeline.py --date 2026-02-24 --runs-root outputs/runs
```

如果仓库中使用旧验证脚本名，也可运行：

```bash
python scripts/verify_final.py --date 2026-02-24 --runs-root outputs/runs
```

---

## 9. 时间段预测 / Range 模式

两个日期 positional 参数会自动激活 range 模式：

```powershell
python main.py 2026-02-24 2026-02-26 ^
  --data-path data/shandong_pmos_hourly.xlsx ^
  --max-cpu-workers 2 ^
  --max-gpu-workers 1 ^
  --seed 42 ^
  --deterministic
```

等价显式写法：

```powershell
python main.py --pipeline ledger_full_range ^
  --start 2026-02-24 ^
  --end 2026-02-26 ^
  --data-path data/shandong_pmos_hourly.xlsx ^
  --max-cpu-workers 2 ^
  --max-gpu-workers 1 ^
  --seed 42 ^
  --deterministic
```

Range 输出：

```text
outputs/runs/range_2026-02-24_to_2026-02-26/range_manifest.json
outputs/runs/range_2026-02-24_to_2026-02-26/range_summary.csv
```

验证：

```bash
python scripts/verify_range_pipeline.py --start 2026-02-24 --end 2026-02-26 --runs-root outputs/runs
```

---

## 10. Delivery Status 与 Exit Code

每次单日或 range 运行都会写 `delivery_status`。

| 状态 | 含义 | Exit Code |
|---|---|---|
| `NORMAL` | 正常五阶段完成，postflight PASS，未使用 fallback | 0 |
| `DEGRADED_DELIVERED` | 正常链路失败或 postflight 失败，但 emergency fallback 生成了可用交付文件 | 2 |
| `FAILED_NO_DELIVERY` | 正常链路失败，fallback 也失败，没有可用交付文件 | 1 |

注意：`DEGRADED_DELIVERED` 有可用文件，但不能当作正常模型成功。它是应急交付，必须修复原因后重跑正常链路。

---

## 11. Emergency Fallback

当正常链路无法生成有效 `submission_ready.csv` 时，系统会自动尝试 emergency fallback。

Fallback 行为：

| 项 | 行为 |
|---|---|
| 方法 | 历史同小时中位数，优先最近 7 天，其次 30 天，再退到全历史同小时 / 全局中位数 |
| 输出 | 标准 24 行 `submission_ready.csv` |
| 标记 | `delivery_status = DEGRADED_DELIVERED` |
| 报告 | `fallback_report.json` / `fallback_report.md` |
| Ledger | 不写入 prediction ledger，避免污染未来权重学习 |

故障注入验证已覆盖：

- 模型阶段失败后 fallback 成功；
- 历史数据缺失时不会假成功；
- 空 ledger 会被 hard gate 拦截；
- 坏 final 输出会被 postflight 捕捉并触发 fallback。

---

## 12. 质量门禁

### `ledger_weight` hard gate

正式权重学习前会严格检查 D-30..D-1：

| Task | 模型数 | 期望 prediction rows | 期望 actual rows |
|---|---:|---:|---:|
| Dayahead | 3 | 30 × 3 × 24 = 2160 | 30 × 24 = 720 |
| Realtime | 4 | 30 × 4 × 24 = 2880 | 30 × 24 = 720 |

如果缺天、缺模型、缺小时，`ledger_weight` 会失败，不会生成假权重。

### Postflight

`final/submission_ready.csv` 必须通过：

- 文件存在；
- 列名严格一致；
- 24 行；
- 小时 1..24；
- `business_day` 一致；
- 价格列 numeric 且非空；
- 无 `_x` / `_y` 后缀列。

---

## 13. 验证命令

静态与 synthetic 检查：

```bash
python -m py_compile pipelines/delivery_quality.py pipelines/emergency_fallback.py pipelines/delivery_report.py pipelines/ledger_full.py pipelines/ledger_full_range.py pipelines/ledger_weight.py runners/adapters/timesfm_v1.py runners/adapters/lightgbm_v1.py scripts/verify_range_pipeline.py scripts/check_delivery_stability.py main.py
python scripts/check_cli_range_args.py
python scripts/check_delivery_stability.py
```

CLI surface 检查：

```bash
python main.py --help
```

部署人员不需要设置任何隐藏的 v1 adapter mode 参数；正常只使用日期、数据路径、CPU/GPU worker、seed 等基础参数。

---

## 14. 快速 Smoke 测试

Smoke 只验证模型预测链路能跑通，不生成正式交付文件，不污染正式 ledger。

```powershell
python main.py --pipeline ledger_smoke --date 2026-02-24 ^
  --data-path data/shandong_pmos_hourly.xlsx ^
  --smoke-training-months 3 ^
  --smoke-timemixer-epochs 3 ^
  --smoke-timemixer-patience 1 ^
  --seed 42 ^
  --deterministic ^
  --force
```

Smoke 输出在 `outputs/smoke/`。

---

## 15. 实验隔离建议

如果只想验证链路、减少训练时间，可使用隔离目录和小参数：

```powershell
$RUN_ROOT = "outputs/_validation_tmp/runs"
$LEDGER_ROOT = "outputs/_validation_tmp/ledger"

python main.py 2026-02-24 ^
  --data-path data/shandong_pmos_hourly.xlsx ^
  --runs-root $RUN_ROOT ^
  --ledger-root $LEDGER_ROOT ^
  --timemixer-epochs 1 ^
  --timemixer-patience 1 ^
  --max-cpu-workers 2 ^
  --max-gpu-workers 1 ^
  --seed 42
```

注意：这种结果只用于工程链路验证，不作为正式精度结果。实验结束后应归档 manifest / report / summary，并清理临时 runs/ledger。

---

## 16. 常见问题

**Q: 需要外部 EPF v1.0 文件夹吗？**  
不需要。LightGBM 和 TimesFM 的交付版本已 bundled 在本仓库中。

**Q: 为什么第一次运行需要 ledger？**  
因为 `ledger_weight` 要用过去 30 天真实预测/实际值学习融合权重。没有 30 天账本就无法正常学习权重。

**Q: 可以减少模型数量来快跑吗？**  
不建议。完整链路要求 7/7 模型输出完整。减少模型会触发质量门禁，不能作为正式通过。

**Q: 可以减少 TimeMixer epoch 吗？**  
可以用于工程连通性实验，但不能作为正式精度结果。正式交付建议使用默认或约定参数。

**Q: Exit code 2 是失败吗？**  
它表示 `DEGRADED_DELIVERED`：有可用应急交付文件，但不是正常模型成功。需要查看 fallback 报告并修复原因。

**Q: `outputs/runs` 和 `outputs/ledger` 会提交 Git 吗？**  
不会，这些目录被忽略。正式交付时只需要把结果文件按甲方要求交付即可。

---

## 17. 技术文档索引

| 文档 | 说明 |
|---|---|
| [`docs/FINAL_VALIDATION_SUMMARY.md`](docs/FINAL_VALIDATION_SUMMARY.md) | 最终链路验证结果，推荐交付时一并提供 |
| [`docs/OUTPUT_CONVENTION.md`](docs/OUTPUT_CONVENTION.md) | 输出目录、文件结构、字段约定 |
| [`docs/RANGE_PIPELINE_TECHNICAL_GUIDE.md`](docs/RANGE_PIPELINE_TECHNICAL_GUIDE.md) | Range 模式技术说明 |
| [`docs/FINAL_CUDA_ACCEPTANCE_REPORT.md`](docs/FINAL_CUDA_ACCEPTANCE_REPORT.md) | 历史 CUDA 验收记录，已由最终验证报告补充 |

---

## 18. 交付检查清单

交付前建议确认：

```bash
python scripts/check_delivery_stability.py
python scripts/check_cli_range_args.py
python scripts/verify_final_pipeline.py --date YYYY-MM-DD --runs-root outputs/runs
python scripts/verify_range_pipeline.py --start START --end END --runs-root outputs/runs
```

最终给甲方的核心文件：

```text
outputs/runs/YYYY-MM-DD/final/submission_ready.csv
```

可选附带：

```text
outputs/runs/YYYY-MM-DD/run_manifest.json
outputs/runs/YYYY-MM-DD/delivery_report.md
outputs/runs/range_START_to_END/range_manifest.json
outputs/runs/range_START_to_END/range_summary.csv
docs/FINAL_VALIDATION_SUMMARY.md
```

---

## License

MIT License
