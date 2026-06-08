# V2 Run Summary

## 1. Executive summary

- Total runtime: not reliably logged in a single runtime manifest; the V2 loop ran across multiple sequential branch executions on `2026-06-05`.
- Full-2025 V2 experiments attempted under explicit recorded scope: `7`
  - `1` time-frequency experiment in `V2_J3`
  - `2` risk-hour bias experiments
  - `1` feature-group graph experiment
  - `2` hard-regime correction experiments
  - `1` interval / probabilistic experiment
- Additional non-comparable follow-up packaging evidence present:
  - `1` fusion packaging / `2026-04` promotion validation record in the registry
- Branches attempted:
  - `V2_J3 time-frequency`
  - `risk_hour_bias`
  - `feature_group_graph`
  - `hard_regime_correction`
  - `interval_probability`
  - `fusion_tuning` (summary / packaging evidence only; no same-scope full-2025 replacement run recorded in the V2 ledger)
- Branches skipped: none in the planned V2 chain, but several branches ended early after rejection.
- Best V2 candidate under the same full-2025 Protocol B scope:
  - `P1_quantile_interval`
  - scope: `full 2025 Protocol B` for point metrics, plus additional uncertainty diagnostics
- Did any V2 candidate beat the frozen landing model on the same full-2025 Protocol B official capped point-metric scope?
  - `No`
- Does the frozen landing model remain final?
  - `Yes`

## 2. Frozen landing baseline

Authoritative frozen landing in the current worktree:

- model name: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`
- config: `SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml`
- artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- full-year RT capped SMAPE: `10.906743313696468`
- full-year `9_16` RT capped SMAPE: `15.504180616043215`
- full-year raw RT SMAPE: `20.79251599092717`
- full-year raw `9_16` RT SMAPE: `36.343056642225086`

Important baseline note:

- The user prompt referenced an older historical landing baseline:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_20260605_134012`
- The current worktree freeze, registries, and V2 branch comparisons all use:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- This summary therefore uses the current worktree frozen baseline as authoritative.

## 3. Branch-by-branch summary

### 3.1 V2_J3 time-frequency

- branch name: `V2_J3 time-frequency`
- variants tested:
  - `SGDFNet_V2_J3_TF1_20260605_164407`
- hypothesis:
  - simple moving-average residual features may improve `9_16` and risk-hour behavior
- changed factor:
  - `TF1 moving-average residual features`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_J3_TF1_20260605_164407`
- key metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `10.843562843939626`
  - full-year `9_16` RT capped SMAPE: `15.298323635483852`
  - full-year raw RT SMAPE: `20.937991535532365`
  - full-year raw `9_16` RT SMAPE: `36.663156705634265`
  - `9_16` worst-month capped SMAPE: `25.717663530368423`
  - hour `15` capped SMAPE: `17.284637768496037`
  - hour `14` capped SMAPE: `12.901840145362948`
  - hour `11` capped SMAPE: `12.832119415600536`
  - top-10% tail RT capped SMAPE: `39.213444404080114`
- decision:
  - `REJECT`
- reason:
  - modest capped gains on some `9_16` / risk-hour cells were not enough under the KEEP rule; J3 acceptance summary is `NEGATIVE`

### 3.2 Risk-hour bias

#### Variant `RHB1_hour_bias`

- changed factor:
  - `hour bias calibration on risk hours 9/10/15`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B1_RHB1_HourBias_20260605_170856`
- key metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `10.930287247130297`
  - full-year `9_16` RT capped SMAPE: `15.574812416344695`
  - risk-hour average capped SMAPE for hours `9/10/15`: `19.188195794443587`
  - full-year raw `9_16` RT SMAPE: `36.60422376047461`
- decision:
  - `REJECT`
- reason:
  - harmed the official full-year capped metric and the `9_16` official capped metric; risk-hour average also worsened

#### Variant `RHB1_segment_hour_bias`

- changed factor:
  - `segment-hour bias calibration on 9_16 risk hours 9/10/11/14/15`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B1_RHB1_SegmentHourBias_20260605_170920`
- key metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `10.944251748796349`
  - full-year `9_16` RT capped SMAPE: `15.616705921342849`
  - risk-hour average capped SMAPE for hours `9/10/15`: `19.188195794443587`
  - full-year raw `9_16` RT SMAPE: `36.84524337125452`
- decision:
  - `REJECT`
- reason:
  - worsened both official capped metrics and did not improve the risk-hour aggregate

### 3.3 Feature-group graph

- branch name: `feature_group_graph`
- variant:
  - `G1_static_graph`
- changed factor:
  - `static feature-group graph features`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B2_G1_StaticGraph_20260605_172539`
- key metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `10.878052327548035`
  - full-year `9_16` RT capped SMAPE: `15.388258448834636`
  - risk-hour average capped SMAPE for hours `9/10/15`: `18.90771215702164`
  - full-year raw `9_16` RT SMAPE: `37.013328237104254`
  - top-10% tail RT capped SMAPE: `39.74235206352968`
- decision:
  - `REJECT`
- reason:
  - this branch improved the official capped metric subset, including `9_16` and risk-hour average, but worsened the raw `9_16` full-year metric and did not meet the branch KEEP rule; this is a same-scope full-2025 result, but only a partial win

### 3.4 Hard-regime / spike correction

#### Variant `H1_error_gate_bias`

- changed factor:
  - `validation residual error-gate bias correction`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B3_H1_ErrorGateBias_20260605_172845`
- key metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `12.093277817807731`
  - full-year `9_16` RT capped SMAPE: `17.10839224426859`
  - risk-hour average capped SMAPE: `21.05197006232967`
  - full-year raw `9_16` RT SMAPE: `39.439661862653935`
- decision:
  - `REJECT`
- reason:
  - large regressions in full-year capped, `9_16` capped, risk-hour average, and raw `9_16`

#### Variant `H2_combo_error_sign_gate_bias`

- changed factor:
  - `validation residual error-sign combo gate bias correction`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B3_H2_ComboErrorSignGateBias_20260605_172915`
- key metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `12.42500741875956`
  - full-year `9_16` RT capped SMAPE: `17.536844721467354`
  - risk-hour average capped SMAPE: `21.514382442086056`
  - full-year raw `9_16` RT SMAPE: `40.730294202754266`
  - top-10% tail RT capped SMAPE: `35.04085156650184`
- decision:
  - `REJECT`
- reason:
  - despite a tail diagnostic gain on one subset, the same-scope full-year capped and `9_16` results worsened too much

### 3.5 Interval / probabilistic output

- branch name: `interval_probability`
- variant:
  - `P1_quantile_interval`
- changed factor:
  - `quantile interval head on frozen baseline feature family`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`
- key metrics
  - point metric scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `10.906743313696468`
  - full-year `9_16` RT capped SMAPE: `15.504180616043215`
  - full-year raw RT SMAPE: `20.79251599092717`
  - full-year raw `9_16` RT SMAPE: `36.343056642225086`
  - point-metric comparison versus frozen landing:
    - identical under the same full-2025 scope
  - probability metric scope: `full 2025 Protocol B uncertainty diagnostics`
  - mean interval coverage: `0.774679179467486`
  - mean interval width: `98.98832580308662`
  - mean spike recall top-k: `0.6897721611789117`
  - mean spike average precision: `0.638992261151562`
  - mean interval brier proxy: `0.042530611979165335`
- decision:
  - `KEEP`
- reason:
  - preserved the same full-2025 point metrics while adding useful uncertainty diagnostics

### 3.6 Fusion / controlled tuning

- branch name: `fusion_tuning`
- recorded evidence:
  - `ffam_002` fusion packaging artifact:
    - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Fusion_SignedTailPointPlusIntervalTailFlag_V1_20260605_195453`
  - `2026-04` promotion validation artifact:
    - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_PromotionValidation_202604_FusionBundle_V1_20260605_201409`
- accepted modules combined in that packaging:
  - signed-tail calibration evidence `stcfam_001`
  - interval module `P1_quantile_interval`
- key metrics
  - scope: `2026-04 single-month promotion validation`, not `full 2025 Protocol B`
  - RT capped SMAPE: `12.500682342932146`
  - `9_16` RT capped SMAPE: `16.243557451904437`
  - raw RT SMAPE: `26.73964557533788`
  - top-10% tail RT capped SMAPE: `60.56170314905004`
- decision:
  - `KEEP` inside the packaging validation record
- reason:
  - useful packaging evidence, but not a full-2025 same-scope replacement result
- comparability:
  - `not directly comparable to frozen landing for replacement`

## 4. Best candidate analysis

### Best V2 candidate under replacement-safe scope

- name:
  - `P1_quantile_interval`
- config:
  - `SGDFNet/configs/v2_branch4_p1_quantile_interval.yaml`
- artifact:
  - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`
- accepted modules:
  - interval / probabilistic output only
- same-scope full-year metrics
  - scope: `full 2025 Protocol B`
  - full-year RT capped SMAPE: `10.906743313696468`
  - full-year `9_16` RT capped SMAPE: `15.504180616043215`
  - full-year raw RT SMAPE: `20.79251599092717`
  - full-year raw `9_16` RT SMAPE: `36.343056642225086`
- risk-hour metrics
  - scope: `full 2025 Protocol B risk-hour subset`
  - identical to frozen landing because point predictions were unchanged
- raw diagnostics
  - scope: `full 2025 Protocol B uncertainty diagnostics`
  - mean interval coverage: `0.774679179467486`
  - mean interval width: `98.98832580308662`
  - spike recall top-k: `0.6897721611789117`
  - spike average precision: `0.638992261151562`
- comparison vs frozen landing
  - point metrics: `tie`
  - uncertainty diagnostics: `better, because the frozen landing baseline had no interval head`
- operational significance
  - meaningful as a research / uncertainty extension
  - not meaningful as a point-prediction replacement
- should it replace frozen landing?
  - `No`

### Best partial same-scope point diagnostic improvement

- candidate:
  - `G1_static_graph`
- why it matters:
  - same-scope full-2025 official capped metrics improved on the subset of interest:
    - full-year RT capped SMAPE: `10.8781` vs frozen `10.9067`
    - full-year `9_16` RT capped SMAPE: `15.3883` vs frozen `15.5042`
    - risk-hour average capped SMAPE: `18.9077` vs frozen `19.0871`
- why it was not accepted:
  - raw `9_16` full-year SMAPE worsened to `37.0133`
  - branch KEEP rule was not met
  - no decisive replacement case was established

### Replacement conclusion

- No V2 candidate beat the frozen landing model in a way strong enough to justify replacement under the same full-2025 Protocol B official capped point-metric scope.
- Frozen landing remains final.

## 5. Metric scope audit

### Comparable same-scope metrics

1. `full_year_rt_capped_smape = 10.906743313696468`
   - scope: `full 2025 Protocol B`
   - source: `SGDFNet/research_control/06_LANDING_FREEZE.json`
   - comparable to frozen landing: `Yes`

2. `segment_9_16_rt_capped_smape = 15.504180616043215`
   - scope: `full 2025 Protocol B / 9_16 segment`
   - source: `SGDFNet/research_control/06_LANDING_FREEZE.json`
   - comparable to frozen landing: `Yes`

3. `TF1 overall_rt_capped_smape = 10.843562843939626`
   - scope: `full 2025 Protocol B`
   - source: `SGDFNet/reports/v2_j3_time_frequency/tf_experiment_ledger.csv`
   - comparable to frozen landing: `Yes`

4. `G1_static_graph overall_rt_capped_smape = 10.878052327548035`
   - scope: `full 2025 Protocol B`
   - source: `SGDFNet/reports/v2_continuous/v2_experiment_ledger.csv`
   - comparable to frozen landing: `Yes`

5. `P1_quantile_interval overall_rt_capped_smape = 10.906743313696468`
   - scope: `full 2025 Protocol B`
   - source: `SGDFNet/reports/v2_continuous/v2_experiment_ledger.csv`
   - comparable to frozen landing: `Yes`

### Diagnostic but not replacement-comparable metrics

6. `mean_interval_coverage = 0.774679179467486`
   - scope: `full 2025 Protocol B uncertainty diagnostic`
   - source: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936/probability_summary.json`
   - comparable to frozen landing point metric: `No`

7. `fusion bundle RT capped SMAPE = 12.500682342932146`
   - scope: `2026-04 promotion validation single-month scope`
   - source: `SGDFNet/research_control/05_BEST_MODEL_REGISTRY.json`
   - comparable to frozen landing full-2025 scope: `No`

### Scope mismatch warning

8. `full_year_summary.json` capped metrics for the frozen landing artifact
   - values:
     - full-year RT capped SMAPE: `18.111625215245596`
     - full-year `9_16` RT capped SMAPE: `30.847423831384308`
   - scope / formula status:
     - artifact summary values exist, but they do not match the official rescored floor-50 capped metrics used by the current landing freeze
   - source:
     - `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230/full_year_summary.json`
   - comparable to frozen landing official score:
     - `No`
   - warning:
     - raw metrics match across sources, but capped metrics do not; future acceptance decisions should use the official rescored floor-50 capped discipline consistently

## 6. V2 acceptance judgment

- classification:
  - `V2_ACCEPTED_AS_RESEARCH_ONLY`
- decision basis:
  - no V2 candidate established a strong enough same-scope full-2025 point-metric win to replace frozen landing
  - `P1_quantile_interval` is worth keeping as a research / uncertainty extension because it preserved the same point metrics and added useful probabilistic diagnostics

## 7. Lessons learned

### What worked

- strict rolling Protocol B comparison made branch outcomes easy to audit
- risk-hour diagnosis correctly exposed recurring concentration around hours `9`, `10`, and `15`
- the interval / probabilistic branch added useful uncertainty outputs without harming same-scope point metrics
- graph features showed some real same-scope capped improvements, so feature interaction structure is not a dead end

### What failed

- risk-hour bias calibrations did not transfer safely enough
- hard-regime correction variants were strongly harmful under the official full-2025 scope
- TF1 produced only partial wins and did not cross the KEEP boundary
- fusion evidence never became a same-scope full-2025 replacement case

### What should not be retried blindly

- direct hard-regime local correction with the current error-gate family
- broad post-hoc local repair loops that trade away raw `9_16` stability
- acceptance decisions that mix official rescored capped metrics with incompatible artifact-summary capped metrics

### What remains promising

- graph-like structured feature interactions, but only with stricter same-scope control
- uncertainty outputs as an add-on, not as a point-model replacement
- future real-time work should focus on a stronger trunk / point signal rather than another repair cascade

### Remaining risk

- metric-discipline inconsistency around capped scores remains a real reporting risk
- the current best research-only candidate improves uncertainty but not the official point metric
- some later packaging evidence is only available on single-month or promotion-validation scope

## 8. Next recommendation

- exact recommendation:
  - `keep frozen landing model and stop V2`
- why:
  - no V2 candidate clearly beat the frozen landing model on the same full-2025 Protocol B official capped point-metric scope
  - the only accepted V2 result is research-only / uncertainty-oriented, not a deployable replacement
