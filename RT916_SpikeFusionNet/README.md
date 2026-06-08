# RT916_SpikeFusionNet

`RT916_SpikeFusionNet` is the formal release-safe package for RT916 day-ahead and real-time forecasting in this project.

This bundle is the locked version derived from the release-safe line:

- best day-ahead stage3 policy: `rule_policy`
- lock experiment: `E1003`
- release-safe leakage fix: target-derived lag and rolling features are recomputed after the asof cutoff during inference

## Layout

- `configs/`: release profile and default CLI settings
- `docs/`: packaging notes and runtime boundaries
- `src/rt916_spikefusionnet/`: model source, feature processing, release policy, and CLI implementation
- `run.py`: single command-line entry

## Core commands

Show CLI help:

```powershell
python RT916_SpikeFusionNet\run.py --help
```

Dry-run a direct model invocation:

```powershell
python RT916_SpikeFusionNet\run.py --mode run --target realtime --start "2025-01-01 01:00:00" --end "2025-01-03 00:00:00" --dry-run
```

Release-safe bundle generation for day-ahead:

```powershell
python RT916_SpikeFusionNet\run.py --mode release_bundle --target dayahead --start "2025-01-01 01:00:00" --end "2025-12-31 00:00:00"
```

Release-safe bundle generation for both day-ahead and real-time:

```powershell
python RT916_SpikeFusionNet\run.py --mode release_bundle --target all --start "2025-01-01 01:00:00" --end "2025-01-31 00:00:00"
```

Daily backtest:

```powershell
python RT916_SpikeFusionNet\run.py --mode daily_backtest --target realtime --start "2025-01-01 01:00:00" --end "2025-01-31 00:00:00"
```

Joint day-ahead plus real-time backtest:

```powershell
python RT916_SpikeFusionNet\run.py --mode joint_da_rt --target all --start "2025-01-01 01:00:00" --end "2025-01-31 00:00:00"
```

## Supported targets and modes

- `--target dayahead`
- `--target realtime`
- `--target all` for `release_bundle` only

- `--mode run`: direct train plus predict through the copied package core
- `--mode daily_backtest`: daily asof backtest using the copied package core
- `--mode joint_da_rt`: DA-first then RT-with-DA-injection backtest
- `--mode release_bundle`: formal release-safe assembly path using fixed stage sources plus the locked `rule_policy`

## Outputs

The package writes to:

`outputs/RT916_SpikeMarketLab/model_packages/RT916_SpikeFusionNet/`

That tree contains runtime artifacts, release bundle outputs, caches, and summaries.
