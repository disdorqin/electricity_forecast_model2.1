# Architecture

## Package intent

This package converts the lab's locked release-safe result into a clean project-root model bundle.

## Main pieces

- `core.py`: copied training and inference backbone
- `dataprocess.py`: feature engineering and cutoff-safe target-dependent feature recomputation
- `model.py`, `annual_model.py`, `annual_model_da_timemixer.py`, `annual_loss.py`: copied backbone and specialized modules
- `policy.py`: formal release-safe stage3 rule policy and release bundle assembly
- `cli.py`: unified command-line entry

## Release-safe policy

The formal release path only uses:

- fixed stage1 and stage2 historical sources from the packaged best experiments
- stage3 `base` or `timemixer`
- rolling 12-month train plus 1-month validation rule selection

Guardrails:

- stage3 validation delta must be at least `+0.3`
- harmed validation days must not exceed improved validation days
- worst validation period delta must be at least `-1.0`
- full-day validation delta must be at least `-0.3`

If those checks fail, the package keeps `base`.
