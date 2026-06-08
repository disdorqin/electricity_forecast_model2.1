# Packaging Changelog

## Files created

- `scripts/runners/run_sgdfnet_realtime.py`
- `SGDFNet/src/sgdfnet/production_api.py`
- `SGDFNet/src/sgdfnet/io_utils.py`
- `SGDFNet/src/sgdfnet/checkpointing.py`
- `SGDFNet/src/sgdfnet/dataset.py`
- `SGDFNet/src/sgdfnet/eval_a0.py`
- `SGDFNet/configs/production_sgdfnet_realtime.yaml`
- `SGDFNet/docs/SGDFNet_PRODUCTION_USAGE.md`
- `SGDFNet/docs/MODEL_CARD.md`
- `SGDFNet/docs/PACKAGING_CHANGELOG.md`

## Files modified

- `SGDFNet/src/sgdfnet/__init__.py`
- `SGDFNet/src/sgdfnet/data_contract.py`

## Behavior changes

- adds stable public packaging APIs
- adds a production CLI runner for train, predict, train_predict, rolling_2025, and smoke
- keeps the accepted landing Protocol B path as the authoritative research path

## Verification commands

- `python scripts/runners/run_sgdfnet_realtime.py --help`
- `python scripts/runners/run_sgdfnet_realtime.py --mode smoke --config SGDFNet/configs/production_sgdfnet_realtime.yaml --data data/shandong_pmos_hourly.xlsx --output-dir outputs/RT916_SpikeMarketLab/production_runs/smoke --overwrite`

## Landing behavior expectation

- landing metrics are expected to remain unchanged because the accepted research path and metrics logic are not altered
