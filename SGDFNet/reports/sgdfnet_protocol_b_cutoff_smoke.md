# SGDFNet Protocol B Cutoff Smoke

## Scope

Smoke config:

- config: `SGDFNet/configs/protocol_b_cutoff_smoke_202501.yaml`
- runtime: `SGDFNet/run_protocol_b_cutoff.py`
- artifact dir: `outputs/RT916_SpikeMarketLab/experiments/SGDFNet_ProtocolB_Cutoff_Smoke_202501_20260606_114249`

Target window:

- decision days: `2025-01-01` to `2025-01-04`
- predicted target days: `2025-01-02` to `2025-01-05`

## Smoke questions and answers

### 1. For a decision day, what is the max visible realtime timestamp?

From `split_audit.json`:

- `2025-01-01 -> 2025-01-02`: max visible realtime timestamp = `2025-01-01 15:00:00`
- `2025-01-02 -> 2025-01-03`: max visible realtime timestamp = `2025-01-02 15:00:00`
- `2025-01-03 -> 2025-01-04`: max visible realtime timestamp = `2025-01-03 15:00:00`
- `2025-01-04 -> 2025-01-05`: max visible realtime timestamp = `2025-01-04 15:00:00`

Conclusion: the visible realtime boundary is explicitly locked at `<= D 15:00`.

### 2. Is the runtime strictly `<= D 15:00`?

Yes.

The audit records the blocked same-day window as:

- `D 16:00:00 -> D+1 00:00:00`

and the runtime marks:

- `same_day_post_cutoff_filled_with_da = true`
- `feature_recomputed_after_cutoff = true`

### 3. Is `D 15:00 -> 24:00` filled only with DA?

Yes.

Manual spot check on `decision_day = 2025-01-01`:

- `2025-01-01 16:00`: `visible_rt_anchor = 387.11 = 日前电价`
- `2025-01-01 17:00`: `visible_rt_anchor = 406.19 = 日前电价`
- `2025-01-01 18:00`: `visible_rt_anchor = 400.78 = 日前电价`
- ...
- `2025-01-02 00:00`: `visible_rt_anchor = 330.49 = 日前电价`

The smoke check confirms `all_fill_matches_da = true`.

### 4. Was full `D+1` 24-hour prediction generated successfully?

Yes.

`predictions.csv` contains:

- total rows: `96`
- target days: `2025-01-02`, `2025-01-03`, `2025-01-04`, `2025-01-05`
- rows per target day: `24`

Conclusion: the walk-forward runtime generates the full next-day 24-hour forecast.

### 5. On next-day rolling, did we only add newly allowed information?

Operationally yes.

Each iteration advances from:

- `decision_day = D`
- visible realtime max = `D 15:00`

to:

- `decision_day = D + 1`
- visible realtime max = `D+1 15:00`

So the newly exposed actual realtime information is exactly the additional allowed window up to the next decision cutoff, not the full uncensored next day.

## Smoke metrics

These metrics are only to confirm runtime viability, not release comparison:

- overall raw `rt_smape` = `11.9208`
- overall capped `rt_capped_smape` = `10.1963`
- overall `9_16 rt_capped_smape` = `14.4074`
- overall direction accuracy = `0.8958`

## Leakage conclusion

Smoke result: **Protocol B cutoff + walk-forward path runs successfully and enforces the intended visibility boundary**.

What is fixed in this smoke path:

1. no actual realtime values after `D 15:00` are used as runtime-visible history
2. blocked same-day realtime anchor is replaced by DA
3. target-derived lag/rolling features are recomputed after cutoff/fill
4. evaluation is day-by-day walk-forward rather than monthly test slicing on a globally precomputed frame

## Important limitation

This smoke validates the cutoff runtime mechanics only.

It does **not** yet authorize SGDFNet realtime results to be treated as formally comparable with the already packaged release model family until a wider corrected-window validation is completed.
