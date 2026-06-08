# RT916 电力价格 9-16 尖峰预测主线

## 当前锁定方法

- 方法：RT916_ResidualCalibrated_SprintBest_V1
- 配置：segment ExtraTreesRegressor / eta=1.0 / clip=50 / scope=only_sprint_harmed_train_regime
- 指标：新业务 capped SMAPE，actual 和 pred 低于 50 时按 50 计算
- 保护：最终 24h 输出中 1-8、17-24 强制等于 B0，只允许 9-16 修改

## 官方入口

```powershell
python -m scripts.runners.run_rt916_rc_sprintbest --root "D:\作业\science\大创科研时序\代码\elec"
python -m scripts.runners.run_rt916_final_grand_experiment_v1 --root "D:\作业\science\大创科研时序\代码\elec"
python -m scripts.runners.run_rt916_2025_monthly_backtest_v1 --root "D:\作业\science\大创科研时序\代码\elec"
```

## 关键结果

- 2024-04/05/06 命中 35：avg_9_16=34.3203, avg_delta=+3.2556
- 2025 月度回测：overall_avg_9_16=38.88377600965249, overall_avg_delta=0.0
- 2025 回测 verdict：input_blocked_2025

## 文件治理

旧 RT916 探索脚本已归档到 `scripts/deprecated/`，主线保留在 `scripts/runners/run_rt916_rc_sprintbest.py`、`run_rt916_final_grand_experiment_v1.py`、`run_rt916_2025_monthly_backtest_v1.py`。
