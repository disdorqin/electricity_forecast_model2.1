# SGDFNet Realtime Protocol B Cutoff Rectification Plan

## Goal

Rectify SGDFNet realtime forecasting to the business-safe Protocol B boundary:

- decision time = `D 15:00`
- actual realtime data is visible only up to `D 15:00`
- `D 15:00 -> D 24:00` must not use actual realtime values
- that blocked window may use day-ahead price as the realtime anchor fill
- target-side historical features must be recomputed after cutoff/fill
- prediction target is all 24 hours of `D+1`

## Current leakage points

The current SGDFNet realtime path leaks because feature construction happens on the full raw table before any test-time visibility restriction:

1. `preprocess_dataframe(...)` builds `delta_target = rt_actual - da_anchor` on the full table.
2. Delta-derived lag/rolling features are computed directly from full `delta_target`.
3. Residual-history features use full actual-side columns before test split.
4. `run_protocol_b_experiment(...)` splits after preprocessing, so test rows inherit history that was already computed with future-visible actual realtime values.
5. The packaged `predict_sgdfnet(...)` path filters an already-preprocessed frame, which keeps the same leakage behavior.

This means the old path is not compliant with Protocol B for realtime deployment.

## New decision-time definition

For target day `T = D + 1`:

- `decision_day = D`
- `decision_timestamp = D 15:00`
- visible actual realtime max timestamp is exactly `D 15:00`
- same-day rows after `D 15:00` are not allowed to consume actual realtime values or actual-side same-day values

## Protocol B visible information set

At decision timestamp `D 15:00`, the runtime may use:

1. all historical rows strictly before `D`
2. target-day-1 rows on `D` up to and including `15:00`
3. all forecast-side columns already available in the source data
4. day-ahead price (`DA anchor`) for `D 16:00 -> D 24:00` as a safe fill surrogate

The runtime may not use:

1. actual realtime values after `D 15:00`
2. actual-side system columns after `D 15:00`
3. target-derived lag/rolling values that were precomputed from the uncensored full table

## Feature handling rules

### Must cutoff first, then recompute

These features are target-side or actual-side history features and must be recomputed on the visible sequence:

- `delta_*`
- `tf_*`
- same-hour delta rolling features
- `hist_*` actual lag features
- residual-history features built from actual minus forecast
- any weekly or long-window target-history feature

Implementation rule:

- replace the history source with a visible runtime source
- for realtime anchor history use:
  - actual realtime up to `D 15:00`
  - DA fill for `D 16:00 -> D 24:00`
- for actual-side columns use:
  - actual values up to `D 15:00`
  - paired forecast columns after `D 15:00`

### Can remain unchanged

These are forecast-side or calendar-side and remain directly usable:

- raw forecast columns
- engineered forecast interactions
- calendar features
- `da_anchor`
- segment/hour/month/day flags

## Script and function changes

### Data layer

Modified / extended:

- `SGDFNet/src/sgdfnet/data_contract.py`

Changes:

- split business-day semantics from timestamp
- allow `preprocess_dataframe(...)` to accept alternate history sources for realtime and actual-side columns
- recompute target-history features from those alternate visible sources instead of always using full `rt_actual`

### New walk-forward runtime

Added:

- `SGDFNet/src/sgdfnet/protocol_b_cutoff.py`
- `SGDFNet/run_protocol_b_cutoff.py`

Responsibilities:

- build `decision_day -> target_day` walk-forward evaluation
- apply `D 15:00` hard cutoff
- fill blocked same-day realtime window with DA anchor
- substitute forecast-side values for blocked same-day actual-side columns
- recompute lag/rolling/history features after cutoff
- train on leakage-safe historical rows only
- predict `D+1` full 24 hours
- emit split/cutoff audit

### Config

Added:

- `SGDFNet/configs/protocol_b_cutoff_smoke_202501.yaml`

## Model layer decision

Default conclusion: **do not modify the model trunk**.

Reason:

- SGDFNet currently uses HGB delta regression on tabular features
- the leakage issue is in data visibility and feature generation order, not in tensor definition
- once the runtime rebuilds the visible history before feature generation, the existing model interface remains sufficient

Only data/runtime changes are required for the current rectification pass.

## Walk-forward evaluation rule

The corrected runtime must evaluate day by day:

1. choose `decision_day = D`
2. train/validate using only rows whose business day is strictly before `D`
3. build visible runtime table at `D 15:00`
4. recompute historical target-side features on that visible runtime table
5. predict all 24 rows of `D+1`
6. after finishing `D+1`, the next cycle may expose the newly allowed actual data up to the next decision cutoff only

This replaces the old month-level test slice that reused globally precomputed target-history features.

## Expected smoke outputs

The smoke must prove:

1. max visible realtime timestamp equals the decision cutoff
2. blocked same-day window uses only DA fill
3. target-day full 24-row prediction is generated
4. next-day rolling only advances by newly allowed information
5. no claim of parity with release models is made before the cutoff runtime is validated
