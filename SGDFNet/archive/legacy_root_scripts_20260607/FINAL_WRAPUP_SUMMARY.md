# SGDFNet Final Wrap-Up Summary

## 1. Final status

- Close-out date: `2026-06-05`
- Final frozen point baseline:
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
  - config: `SGDFNet/configs/protocol_b_a0_j2_val_segment_bias_v1.yaml`
- Final point-baseline conclusion:
  - keep this as the current stable landing-ready point model
  - do not replace it with any later kickoff family candidate

## 2. Official metric position

- Official business metric: floor-50 `rt_capped_smape`
- Official frozen baseline metrics:
  - full-year RT capped SMAPE: `10.9067`
  - full-year `9_16` RT capped SMAPE: `15.5042`
- Secondary diagnostic raw metrics:
  - full-year RT SMAPE: `20.7925`
  - full-year `9_16` RT SMAPE: `36.3431`

## 3. What was actually accepted

- Accepted core point baseline:
  - `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`
- Accepted uncertainty/probability extension:
  - `P1_quantile_interval`
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`
- Accepted signed-tail calibration evidence:
  - `stcfam_001`
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_SignedTailCalibration_TFPressure_V1_20260605_194106`
- Accepted fusion packaging evidence:
  - `ffam_002`
  - artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_Fusion_SignedTailPointPlusIntervalTailFlag_V1_20260605_195453`

## 4. What was rejected

- A1 direction-head-only extension:
  - structurally valid, but did not solve hard-tail price behavior
- A3 gated two-expert point model:
  - gate/expert collapse
- A3R gated residual correction:
  - residual near-zero, no hard-regime price gain
- Risk-hour bias branch:
  - no accepted point improvement
- Feature-group graph branch:
  - no accepted point improvement
- Hard-regime correction branch:
  - no accepted point improvement
- Kickoff post-hoc local repair families:
  - repeated capped/tail gains
  - repeated raw overall / raw `9_16` regressions
- Kickoff structural-point first candidate:
  - `kspoint_001`
  - decision: `REJECT`

## 5. Main research conclusion

The current evidence says the bottleneck is no longer “we need one more clever local repair rule.” The main bottleneck is point-signal quality in the hard regime, especially around `9_16` and risk hours. Post-hoc repair families can buy some capped/tail gains, but they repeatedly fail to preserve raw overall and raw `9_16` behavior.

That means the most defensible packaging today is:

- freeze the stable point baseline
- keep accepted interval/probability output as an attachable extension
- treat later kickoff local-repair families as negative evidence, not new final models

## 6. Important metric-discipline warning

There is a real metric-discipline inconsistency in the current worktree:

- the frozen landing baseline in `03_STAGE_STATE.json` and `05_BEST_MODEL_REGISTRY.json` uses official rescoring from `predictions.csv` under floor-50 capped SMAPE
- some later family evaluators, especially the kickoff structural-point evaluator, compare against `full_year_summary.json`

For the frozen baseline artifact:

- `full_year_summary.json` reports capped metrics around:
  - overall `18.1116`
  - `9_16` `30.8474`
- rescoring `predictions.csv` with the official floor-50 capped logic gives:
  - overall `10.9067`
  - `9_16` `15.5042`

Therefore:

- do not mix these two capped-metric disciplines in one conclusion
- future continuation should standardize family evaluation onto `predictions.csv` rescoring under the official floor-50 capped rule

## 7. Recommended handoff position

If we stop here, the clean handoff is:

1. point baseline remains:
   - `SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
2. accepted optional uncertainty extension remains:
   - `SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`
3. signed-tail / fusion evidence remains archived as supporting experiments, not a replacement landing point model
4. next serious model cycle should attack backbone point signal directly, not keep micro-tuning local repair

## 8. Suggested next-stage direction

If a new round starts, the best next direction is:

- design a new real-time SOTA trunk around stronger hard-regime point signal
- keep Protocol B and official floor-50 capped scoring fixed
- standardize every evaluator on the same rescored `predictions.csv` metric discipline
- use the rejected kickoff families as a do-not-repeat map
