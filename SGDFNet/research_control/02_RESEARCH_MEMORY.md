# SGDFNet Research Memory

## Current Best Model

- Current best corrected realtime model: `SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide`
- Corrected realtime status: accepted best no-leakage reference under `B_D15_cutoff_walk_forward`
- Historical 2025 landing model remains separately frozen for the old landing scope

## Current Best Config

- Current best corrected realtime config: `SGDFNet/configs/cutoff_recovery_2026_diag_a_prune_actualside.yaml`

## Current Best Artifact Path

- Current best corrected realtime artifact path: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide_20260607_094712`

## Current Best Corrected Realtime Metrics

- Full-window overall RT capped SMAPE: `16.5902`
- Full-window overall RT SMAPE: `32.2228`
- Segment `9_16` RT capped SMAPE: `21.1907`
- Segment `9_16` RT SMAPE: `52.7001`
- Risk-hour `9/10/15` RT capped SMAPE: `24.5123`
- Top-10% tail delta MAE: `165.2440`
- Top-10% tail RT SMAPE: `84.5243`
- Direction accuracy: `0.7910`
- Positive direction recall: `0.7490`
- Coverage note:
  - evaluation window is `2026-01-01` through `2026-05-12 00:00:00`
  - `2026-05` is partial because the current workspace dataset ends mid-month

## Historical 2025 Landing Metrics

- Historical landing model: `SGDFNet-ProtocolB-A0-ValSegmentBias-Baseline`
- Historical landing artifact: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Historical landing overall RT capped SMAPE: `10.9067`
- Historical landing segment `9_16` RT capped SMAPE: `15.5042`
- Historical landing overall RT SMAPE: `20.7925`
- Historical landing segment `9_16` RT SMAPE: `36.3431`

## Best Monthly Metrics

- Corrected no-leakage monthly capped RT SMAPE:
  - `2026-01`: `19.7744`
  - `2026-02`: `18.8474`
  - `2026-03`: `15.6132`
  - `2026-04`: `12.3727`
  - `2026-05`: `16.0237` on partial-month valid rows only
- Main corrected pressure zone remains segment `9_16`.

## Accepted Modules

- Accepted module family:
  - `A0` as the minimal DA-anchored delta baseline reference under Protocol B
  - `J1 residual-history features` as a small but real positive feature family under the raw-metric hierarchy
  - `J2 validation-only 9-16 segment bias calibration` as a modest positive post-fit repair on top of the accepted baseline
  - `stcfam_001 signed-tail probability-triggered bias calibration` as the first frozen-baseline-post-landing autonomous point-repair branch that produced a keep-worthy capped/tail gain

## Rejected Modules

- `A3` gated two-expert convex mixture: rejected as a practical mechanism
- `A3R` gated residual extreme correction: rejected as a practical mechanism
- `J1 weekly-history feature family`: rejected under Protocol B because it regressed both overall RT SMAPE and 9-16 RT SMAPE
- `J1 segment-local rolling-stat feature family`: rejected because it worsened both primary raw metrics against the accepted residual-history baseline
- `J1 forecast-pressure interaction feature family`: rejected because it worsened both primary raw metrics against the accepted residual-history baseline
- `J2 tail-weighted objective`: rejected as a release baseline mechanism because the tail gain came with a large full-year and 9-16 regression
- `J2 segment-conditioned baseline`: rejected because splitting the regressor by segment degraded nearly every important metric
- `J2 asymmetric quantile loss`: rejected because direction recall improved but price metrics regressed broadly
- `J2 validation-only all-segment bias calibration`: rejected because it gave back overall gains while keeping 9-16 flat
- `J2 validation-only sign-aware 9-16 bias calibration`: rejected because the slight tail gain came with worse primary metrics
- `J2 validation-only thresholded 9-16 bias calibration`: rejected because thresholding weakened the accepted baseline’s primary-metric gain
- `J2 validation-only recent-window 9-16 bias calibration`: rejected because shortening the calibration window worsened the accepted baseline materially
- `J2 validation-only mean 9-16 bias calibration`: rejected because replacing the median with the mean collapsed the accepted baseline
- `J2 validation-only 9-16 bias plus mild tail weighting`: rejected because tail gains came back, but the primary hierarchy still regressed
- `J2 validation-only q40 9-16 bias calibration`: rejected because skewing the residual quantile away from the median materially worsened the accepted baseline

## Failed Hypotheses

- A single added direction head is not enough by itself to repair hard-regime behavior.
- A convex gate over two full experts did not create meaningful expert specialization.
- Residual hard-regime correction stayed near zero and failed to improve hard-regime price error.
- Hard labels alone are not sufficient to recover the missing signal.
- Naive weekly-history lag expansion is not a free gain; it worsened the accepted baseline on both primary metrics.
- Historical forecast-residual features carry a small amount of transferable signal, but the gain is still too weak to claim that the 9-16 problem is solved.
- Segment-local rolling stats and forecast-pressure interactions improved some direction-side diagnostics, but neither translated into better price metrics.
- Tail weighting can buy real hard-tail improvement, but in the current baseline family it over-trades away global and 9-16 stability.
- Naive segment-conditioned model splitting is too destructive in the current setup.
- Mild asymmetric loss shaping pushes direction behavior, but still does not solve the price-metric problem.
- The useful calibration signal is localized; broadening it to all segments washed out the benefit.
- Splitting the 9-16 calibration by predicted sign overfit the repair and lost the primary-metric win.
- Restricting the 9-16 calibration to only larger predicted deviations also weakened the primary-metric win.
- Restricting the 9-16 calibration to only recent validation days weakened the primary-metric win even more.
- Replacing the robust median bias with a mean bias is highly unstable and destroys the accepted calibration.
- Even a small tail-weight reintroduction breaks the accepted calibration’s primary-metric advantage.
- Skewing the residual quantile away from the median also breaks the accepted calibration.

## Key Diagnostics

- `A0` passed as the delta baseline.
- `A1` passed structurally, but the direction head collapsed on validation and test behavior.
- `A3` failed because gate and expert mixture collapsed.
- `A3R` failed because residual correction stayed near zero and did not improve hard-regime price error.
- `A4` is blocked.
- The hard-regime feasibility study indicates label mismatch is not the only problem.
- Validation-only 9-16 bias calibration can improve the primary hierarchy a bit without changing the learned backbone.

## Do-Not-Retry List

- Do not continue blind gate tuning.
- Do not continue blind residual correction tuning.
- Do not retry `A4` before stronger upstream evidence exists.
- Do not use top-absolute-delta labels without new justification and leakage-safe validation.
- Do not micro-tune the rejected weekly-history feature family.
- Do not continue coarse J2 segment-conditioned splits in the current family.

## Postponed Ideas

- Time-frequency decoupling after a stronger baseline exists
- Feature-group graph after baseline strengthening
- Signed correction only if later diagnostics justify it
- Probabilistic outputs after primary signal quality improves

## Next Planned Stage

- Immediate priority: hold the corrected no-leakage freeze steady
- Active focus: any future realtime comparison must use the cutoff-safe frozen reference
- Not the priority: returning to leaked realtime baselines or mixing leaked and corrected result tables

## Corrected Realtime Freeze

- Freeze file: `SGDFNet/research_control/07_NO_LEAKAGE_FREEZE.json`
- Freeze report: `SGDFNet/reports/sgdfnet_no_leakage_freeze.md`
- Frozen corrected baseline for comparison: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Baseline_20260607_094003`
- Frozen corrected best candidate: `outputs/RT916_SpikeMarketLab/cutoff_recovery_experiments/SGDFNet_CutoffRecovery_2026_Diag_A_PruneActualSide_20260607_094712`
- Freeze rule:
  - future corrected realtime work must compare against the frozen no-leakage best candidate above
  - do not treat legacy leaked realtime outputs as formal baselines

## Open Risks

- Raw RT SMAPE may remain dominated by signal quality rather than architecture complexity.
- Direction collapse may reflect weak feature separability rather than missing heads.
- Hard-regime labels may be misaligned with the business difficulty regime.
- Without strict Protocol B discipline, local gains may be misleading.
- The current accepted baseline already looks strong globally, so future changes must avoid damaging `1-8` and `17-24` while chasing `9-16`.
- Small raw-metric gains can hide mixed capped and tail behavior.
- J2 now suggests that surgical validation-side calibration may be more promising than retraining-side objective distortion.

## Paper Narrative Notes

- The story should not be "more hybrid blocks."
- The defensible story is:
  - first lock a leakage-safe rolling protocol
  - then redesign signal-carrying features
  - then build a stronger minimal baseline
  - then add only modules with falsifiable value

## Seeded Historical Facts

- `A0` passed as delta baseline.
- `A1` passed structurally; direction head collapse observed on validation and test.
- `A3` failed because gate or expert mixture collapsed.
- `A3R` failed because residual correction stayed near-zero and did not improve hard-regime price error.
- `A4` is blocked.
- Hard-regime feasibility indicates label mismatch is not the only problem; feature and task redesign are next.
- Next stage priority is `J0 -> J1 -> J2`, not more `A3` or `A3R` tuning.
- In the current worktree, the first real SGDFNet-owned Protocol B run succeeded and established the J0 baseline artifact at `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_20260605_140508`.
- The current accepted artifact is `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`.

## Landing Audit 2025

- Official landing metric: `rt_capped_smape` with floor-50 preprocessing (`actual/pred < 50 => 50`).
- Audited artifact: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`
- Config path: `C:\Users\37813\.codex\worktrees\ce61\elec\SGDFNet\configs\protocol_b_a0_j2_val_segment_bias_v1.yaml`
- Official full-year RT capped SMAPE: `10.9067`
- Official full-year 9-16 RT capped SMAPE: `15.5042`
- Full-year capped target met: `True`
- 9-16 capped target met: `True`
- Secondary raw full-year RT SMAPE: `20.7925`
- Secondary raw 9-16 RT SMAPE: `36.3431`
- Raw SMAPE remains a diagnostic metric and must still be reported beside the official capped metric.
- Next step after landing audit: deployment packaging or paper/ablation package, not blind tuning.

## V2 Landing Freeze

- Landing model is frozen for V2 comparison.
- V2 begins as exploratory improvement work only.
- Landing model remains deployable even if every V2 branch fails.

## V2 Continuous Loop

- Current V2 branch state: `closed_out`.
- Frozen execution baseline: `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_ProtocolB_A0_J2_ValSegmentBias_20260605_143230`.
- Accepted interval module: `P1_quantile_interval` at `outputs\RT916_SpikeMarketLab\experiments\SGDFNet_V2_B4_P1_QuantileInterval_20260605_173936`.
- Accepted signed-tail calibration module: `stcfam_001` at `C:\Users\37813\.codex\worktrees\ce61\elec\outputs\RT916_SpikeMarketLab\experiments\SGDFNet_SignedTailCalibration_TFPressure_V1_20260605_194106`.
- Accepted fusion bundle: `ffam_002` at `C:\Users\37813\.codex\worktrees\ce61\elec\outputs\RT916_SpikeMarketLab\experiments\SGDFNet_Fusion_SignedTailPointPlusIntervalTailFlag_V1_20260605_195453`.
- Final V2 package decision: `research-only interval extension; landing point baseline retained`.
- Branch outcomes under the frozen baseline:
  - `risk_hour_bias`: negative
  - `feature_group_graph`: negative
  - `hard_regime_correction`: negative
  - `interval_probability`: accepted
  - `signed_tail_probability`: informative but not accepted standalone
  - `signed_tail_calibration`: accepted
  - `fusion_family`: packaging evidence only, not a same-scope landing replacement
- V2 close-out judgment:
  - `V2_ACCEPTED_AS_RESEARCH_ONLY`
- Landing replacement status:
  - `frozen landing remains final`
- Main unresolved risk:
  - capped metric scope mismatch exists between some artifact summaries and the official rescored floor-50 capped discipline

## Follow-Up Cycle

- Fresh-cycle point-signal candidate pool has been exhausted with all candidates rejected.
- The next automated family is `time_frequency_point_signal`.
- First follow-up candidate: `tf_moving_average_features_enabled`.
- Interval extension remains accepted for uncertainty, but point-search must continue separately.

## Next Family Cycle

- The TF follow-up family is exhausted but not useless: `TF + pressure` is the closest raw near-miss and keeps capped/tail gains.
- The next automated family is `tf_pressure_risk_hour_localized_calibration`.
- First candidate: `hour_bias_risk_extended_on_tf_pressure`.
- Second candidate: `segment_hour_bias_risk_extended_on_tf_pressure`.

## Kickoff Follow-Up Cycle

- The kickoff fresh-cycle attempt `kickoff_001` was rejected.
- Legacy follow-up candidates are already exhausted, so a fresh kickoff-specific family is required.
- The next automated family is `kickoff_time_frequency_point_signal`.
- First kickoff follow-up candidate: `tf_moving_average_plus_segment_local_enabled`.

## Kickoff Tail Calibration Family

- Kickoff follow-up point-signal candidates were exhausted with no KEEP, but `kfollow_002` preserved a small capped and tail near-miss signal.
- The next automated family is `kickoff_signed_tail_calibration_family`.
- First candidate: `kickoff_signed_tail_probability_triggered_bias_global`.
- Second candidate: `kickoff_signed_tail_probability_triggered_bias_9_16_seg_local`.

## Kickoff Conservative Tail Calibration Family

- Kickoff tail-calibration still improved capped and tail metrics, but the raw damage suggests over-correction.
- The next automated family is `kickoff_conservative_signed_tail_calibration_family`.
- First candidate: `kickoff_conservative_signed_tail_global_shrinked`.
- Second candidate: `kickoff_conservative_signed_tail_916_shrinked`.

## Kickoff Selective Gate Family

- Conservative kickoff tail-calibration improved capped metrics but still hurt raw metrics too much.
- The next automated family is `kickoff_selective_signed_tail_gate_family`.
- First candidate: `kickoff_selective_signed_tail_global_valgated`.
- Second candidate: `kickoff_selective_signed_tail_916_valgated`.

## Kickoff MonthHour Selective Family

- Kickoff selective-gate reduced raw harm but still failed the acceptance gate.
- The next automated family is `kickoff_monthhour_selective_family`.
- First candidate: `kickoff_monthhour_selective_season_risk_hours`.
- Second candidate: `kickoff_monthhour_selective_sign_consistent_risk_hours`.

## Kickoff Structural Point Family

- The kickoff post-hoc families were exhausted with repeated capped gains but persistent raw regressions.
- The next automated family is `kickoff_structural_point_family`.
- First candidate: `structural_graph_seglocal_plus_risk_weight`.
- Second candidate: `structural_graph_seglocal_plus_risk_and_mild_tail_weight`.

