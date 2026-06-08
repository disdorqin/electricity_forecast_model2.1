# Runtime Boundaries

## Protected original directories

This formal package is a copied implementation. It does not require edits to:

- `SpikeTimesNet/`
- `MarketLinkedSpikeTimesNet/`
- `EquiFreqFormer/`
- `EcoFormer/`
- `TriFactorSpikeTimesNet/`
- `scripts/runners/`

## Data assumptions

- Uses the project's existing `data/shandong_pmos_hourly.xlsx`
- Uses only in-project fields and derived features
- Uses no weather API and no new external data source

## Supported release bundle windows

- day-ahead: 2025 full-year release window, plus 2026-01 to 2026-05 package validation window
- real-time: 2025 release window from existing packaged sources

Direct core execution modes may be used outside those windows if the underlying dataset covers them.
