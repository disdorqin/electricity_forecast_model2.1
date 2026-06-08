# SGDFNet Module Index

## Core control and registry

- `SGDFNet/research_control/00_CONSTRAINTS_AND_TARGETS.md`
  - operating constitution, metric hierarchy, stop rules
- `SGDFNet/research_control/01_MASTER_PLAN_J0_J8.md`
  - stage roadmap
- `SGDFNet/research_control/02_RESEARCH_MEMORY.md`
  - long-lived research memory
- `SGDFNet/research_control/03_STAGE_STATE.json`
  - machine-readable current state
- `SGDFNet/research_control/04_EXPERIMENT_LEDGER.csv`
  - experiment ledger
- `SGDFNet/research_control/05_BEST_MODEL_REGISTRY.json`
  - accepted / best registry
- `SGDFNet/research_control/06_LANDING_FREEZE.json`
  - frozen landing record

## Stable baseline

- config:
  - `SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- role:
  - current stable point baseline

## Accepted extension modules

- interval / probability:
  - config: `SGDFNet/configs/v2_branch4_p1_quantile_interval.yaml`
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`
  - role: accepted uncertainty extension

- signed-tail calibration evidence:
  - instance config: `SGDFNet/reports/signed_tail_calibration_family_cycle/instances/stcfam_001_signed_tail_calibration_tfpressure/experiment_config.yaml`
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_SignedTailCalibration_TFPressure_V1_20260605_194106`
  - role: accepted local repair evidence, not frozen landing replacement

- fusion packaging evidence:
  - instance config: `SGDFNet/reports/fusion_family_cycle/instances/ffam_002_signed_tail_point_plus_interval_tailflag/experiment_config.yaml`
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Fusion_SignedTailPointPlusIntervalTailFlag_V1_20260605_195453`
  - role: archived combined package evidence

## Main report folders

- `SGDFNet/reports/landing_2025`
  - landing freeze and audit reports
- `SGDFNet/reports/v2_j3_time_frequency`
  - time-frequency diagnosis and TF exploration outputs
- `SGDFNet/reports/v2_continuous`
  - continuous V2 ledger, branch summary, best-candidate summary, final comparison
- `SGDFNet/reports/kickoff_*`
  - later kickoff families; mostly negative evidence and family-by-family results

## Practical reading order

If someone needs to resume quickly, read in this order:

1. `SGDFNet/FINAL_WRAPUP_SUMMARY.md`
2. `SGDFNet/research_control/03_STAGE_STATE.json`
3. `SGDFNet/research_control/05_BEST_MODEL_REGISTRY.json`
4. `SGDFNet/research_control/02_RESEARCH_MEMORY.md`
5. `SGDFNet/reports/v2_continuous/v2_best_candidate_summary.md`
6. `SGDFNet/reports/kickoff_structural_point_family_cycle/kickoff_structural_point_experiment_results.csv`

## Known caution

Do not casually compare:

- capped metrics stored in some `full_year_summary.json`
- capped metrics rescored from `predictions.csv` with the official floor-50 rule

Use the official rescored floor-50 capped discipline for future acceptance decisions.
