# SGDFNet Research-Control Constitution

## Scope

This document is the fixed operating contract for all future SGDFNet research work. It governs protocol, metric hierarchy, leakage boundaries, experiment budget, and decision rules. It does not authorize model execution by itself.

## Primary Protocol

- Protocol name: `Protocol B`
- Evaluation scope: rolling monthly backtest over all target months in calendar year 2025
- Target month set: every natural month from `2025-01` through `2025-12`
- Per-target-month temporal rule:
  - train data: timestamps strictly earlier than the validation window of the target month
  - validation data: timestamps strictly earlier than the target month and strictly later than the train core window
  - test data: timestamps inside the target month only
- No experiment may use a looser protocol as its primary evidence after Protocol B is locked.

## Temporal and Leakage Rules

- Features may use only information available as of the forecast timestamp.
- No future actuals may enter features, labels, thresholds, scalers, calibrators, or decomposition states.
- Thresholds, scalers, normalizers, calibrators, and any label-construction statistics must be fit from allowed pre-target data only.
- Validation and test months must use frozen train-derived quantities.
- No post-hoc threshold tuning, label tuning, or calibration tuning on test months.
- No final-test-driven architecture or hyperparameter adjustment.
- If a feature family has ambiguous as-of boundaries, the experiment must emit an explicit leakage audit note before results are considered valid.

## Metric Hierarchy

- Default primary overall metric: `rt_smape`
- Default primary segment metric: `segment_9_16_rt_smape`
- Secondary business-safety metrics:
  - `rt_capped_smape`
  - `segment_9_16_rt_capped_smape`
- Secondary diagnostic metrics may include:
  - tail delta MAE
  - tail RT SMAPE
  - direction accuracy
  - positive direction recall
  - spike or hard-regime F1
  - normal-sample harm rate
- Raw and capped metrics must both be reported explicitly.
- Capped metrics must never silently replace raw metrics in selection logic.

## Final Targets

- Full-year 2025 overall real-time SMAPE target: `< 25`
- Full-year 2025 segment `9-16` real-time SMAPE target: `< 30`
- Any claimed success must report both full-year metrics under Protocol B.

## Stage Pass / Fail / Stop Rules

### Stage Pass

A stage passes only when its declared acceptance metric improves relative to the current accepted baseline and does not violate leakage, protocol, or anti-overfitting rules.

### Experiment Pass

An experiment is `KEEP` only if all conditions hold:

- primary metrics improve or a predeclared stage-specific acceptance rule is met
- no leakage rule is violated
- changed factor matches the one-main-factor rule
- results are reproducible from recorded config and artifact paths

### Retry

An experiment is `RETRY` only when:

- execution failed for non-scientific reasons, or
- artifact integrity is incomplete, or
- a declared implementation bug invalidated the result

### Rejection

An experiment is `REJECT` when:

- primary metrics regress without compensating predeclared gain on the active stage objective, or
- diagnostics show collapse, non-identifiability, or leakage risk, or
- the experiment changed multiple major factors at once

### Program Stop

Stop a branch or program slice when any of the following occurs:

- stage experiment budget is exhausted without structural gain
- three consecutive completed experiments fail to add new evidence
- diagnostics show the active mechanism is misaligned with the task
- the branch requires test-driven tuning to survive

## Anti-Overfitting Rules

- One main factor per experiment.
- No skipping stages.
- No branch may continue on month-specific luck alone.
- No acceptance based on a single favorable month while full-year primary metrics regress.
- No tuning against final test months after those months have been used for model selection evidence.
- If three completed experiments in the same family give no structural improvement, switch branch instead of micro-tuning.

## Workspace Rules

- Protected read-only directories:
  - `TriFactorSpikeTimesNet/**`
  - `SpikeTimesNet/**`
  - `MarketLinkedSpikeTimesNet/**`
  - `EquiFreqFormer/**`
  - `EcoFormer/**`
  - `scripts/runners/**`
- Allowed SGDFNet control workspace:
  - `SGDFNet/**`
  - `outputs/RT916_SpikeMarketLab/experiments/**`
  - `outputs/RT916_SpikeMarketLab/reports/**`
- The control layer must not authorize edits outside allowed SGDFNet-owned paths.

## Experiment Budget Discipline

- Each stage has a finite batch budget defined in the stage roadmap.
- If two completed experiments in a row are micro-variants with no structural new evidence, the next action must be `SWITCH` or `STOP`.
- If three completed experiments in a branch fail the stage gate, Codex must switch branch instead of further threshold micro-tuning.

## Required Artifacts Per Completed Experiment

Every completed experiment must record:

- config path
- baseline artifact path
- candidate artifact path
- protocol identifier
- primary metrics
- secondary metrics
- decision
- reason
- next action
- leakage or split audit if applicable

## Decision Logic

- `KEEP`: experiment becomes the new accepted reference for its scope
- `REJECT`: experiment is scientifically negative and should not be the new reference
- `RETRY`: rerun due to execution or artifact invalidity, not because of disappointing metrics
- `SWITCH`: branch has low remaining value; move to a different method family or stage-approved variant
- `STOP`: terminate the branch or program slice because budget or evidence rules were exhausted

The control system is considered autonomous-execution-ready only when all future work follows these rules without ad hoc reinterpretation.
