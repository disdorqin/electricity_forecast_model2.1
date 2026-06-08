# electricity_forecast_model2.0

本仓库包含两个电力负荷/电价时序预测模型实现:

- [`RT916_SpikeFusionNet/`](./RT916_SpikeFusionNet/) — RT916 脉冲融合网络(年度切片 + 双通道脉冲残差 + 域自适应/TimeMixer)
- [`SGDFNet/`](./SGDFNet/) — SGDFNet(分段门控 + 误差/方向门控融合 + 区间与概率校准)

## 目录结构

```
.
├── README.md
├── .gitignore
├── RT916_SpikeFusionNet/
│   ├── README.md
│   ├── README_RT916.md
│   ├── FINAL_PACKAGING_SUMMARY.md
│   ├── run.py
│   ├── configs/
│   ├── docs/
│   └── src/rt916_spikefusionnet/
└── SGDFNet/
    ├── README.md
    ├── archive/
    ├── configs/
    ├── docs/
    ├── reports/
    ├── research_control/
    ├── scripts/
    └── src/sgdfnet/
```

## 快速上手

详细使用方式见各子项目的 README:

- RT916_SpikeFusionNet: [`RT916_SpikeFusionNet/README_RT916.md`](./RT916_SpikeFusionNet/README_RT916.md)
- SGDFNet: [`SGDFNet/README.md`](./SGDFNet/README.md)

## 许可

仅供研究用途,具体许可见各子项目说明。
