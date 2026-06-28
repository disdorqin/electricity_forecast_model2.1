# Reproducible Bundle (复现包)

本目录提供快速复现所需的最小数据，无需重新运行 30 天 backfill。

## 目录结构

```
fixtures/repro_bundle/
├── ledger/                          # 32 天 seed ledger（从 fixtures/seed_ledger/ 复制）
│   ├── dayahead/
│   │   ├── prediction/prediction_ledger.parquet
│   │   ├── prediction/prediction_ledger.csv
│   │   ├── actual/actual_ledger.parquet
│   │   └── actual/actual_ledger.csv
│   └── realtime/
│       ├── prediction/prediction_ledger.parquet
│       ├── prediction/prediction_ledger.csv
│       ├── actual/actual_ledger.parquet
│       └── actual/actual_ledger.csv
└── sample_runs/                     # 验证通过的直接交付样例（非正式输出）
    ├── 2026-02-26/                  # 单日完整链路样例
    │   ├── run_manifest.json
    │   ├── delivery_report.md
    │   ├── submission_ready.csv
    │   └── final/submission_ready.csv
    └── range_2026-02-24_to_2026-02-26/  # 三日 range 样例
        ├── 2026-02-24/
        ├── 2026-02-25/
        ├── 2026-02-26/
        ├── range_manifest.json
        └── range_summary.csv
```

## 用途

- **`ledger/`**：覆盖 2026-01-25 ~ 2026-02-25（32 天），包含所有模型的预测值和实际值。复制到 `outputs/ledger/` 后可跳过 `ledger_backfill`，直接运行 `ledger_full` 每日链路。
- **`sample_runs/`**：验证通过的完整交付样例，**不是**新的正式预测结果。用于验收参考和复现确认。

## 使用方式

### 快速复制 ledger（跳过 backfill）

Linux / macOS：

```bash
mkdir -p outputs/ledger
cp -r fixtures/repro_bundle/ledger/* outputs/ledger/
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force outputs/ledger | Out-Null
Copy-Item fixtures/repro_bundle/ledger/* outputs/ledger -Recurse -Force
```

### 查看样例交付

```bash
# 单日样例
cat fixtures/repro_bundle/sample_runs/2026-02-26/delivery_report.md
cat fixtures/repro_bundle/sample_runs/2026-02-26/final/submission_ready.csv

# Range 样例
cat fixtures/repro_bundle/sample_runs/range_2026-02-24_to_2026-02-26/range_summary.csv
```

## 数据来源

- `ledger/`：由 `ledger_backfill --start 2026-01-25 --end 2026-02-25` 生成，完整覆盖 30 天权重学习窗口。
- `sample_runs/`：来自最终验证归档 `outputs/_validation_archive/20260628_165754/`，所有日期均通过 NORMAL 交付验收。

## 注意

- 本目录是**静态 fixture**，不作为正式运行产物。
- 正式运行产物在 `outputs/`（被 `.gitignore` 忽略）。
- 如果 `outputs/ledger/` 为空，必须先复制本目录或运行 `ledger_backfill`。
- `sample_runs/` 仅用于验收参考，不应作为正式预测输入。
