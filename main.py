from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from cli.parser import build_parser
from pipelines.evaluate_pipeline import run_evaluate_pipeline
from pipelines.sync_dataset_pipeline import run_sync_dataset_pipeline

# Ledger production pipelines
from pipelines.ledger_predict import run_ledger_predict
from pipelines.ledger_backfill import run_ledger_backfill
from pipelines.ledger_weight import run_ledger_weight
from pipelines.ledger_fuse import run_ledger_fuse
from pipelines.ledger_classifier import run_ledger_classifier
from pipelines.ledger_full import run_ledger_full
from pipelines.ledger_smoke import run_ledger_smoke


def main() -> int:
    args = build_parser().parse_args()
    # Global reproducibility: seed must be set before any model code runs
    from utils.reproducibility import set_global_seed

    set_global_seed(args.seed, args.deterministic)
    # Positional date shortcut: `python main.py 2026-02-01`
    if args.pos_date is not None and args.date is None:
        args.date = args.pos_date
    if args.pipeline == "evaluate":
        output_path = run_evaluate_pipeline(args)
        print(output_path)
        return 0
    if args.pipeline == "sync_dataset":
        output_path = run_sync_dataset_pipeline(args)
        print(output_path)
        return 0
    # --- Ledger production pipelines ---
    if args.pipeline == "ledger_predict":
        result = run_ledger_predict(args)
        print(f"ledger_predict complete: {result}")
        return 0
    if args.pipeline == "ledger_backfill":
        result = run_ledger_backfill(args)
        print(f"ledger_backfill complete: {result}")
        return 0
    if args.pipeline == "ledger_weight":
        result = run_ledger_weight(args)
        print(f"ledger_weight complete: {result}")
        return 0
    if args.pipeline == "ledger_fuse":
        result = run_ledger_fuse(args)
        print(f"ledger_fuse complete: {result}")
        return 0
    if args.pipeline == "ledger_classifier":
        result = run_ledger_classifier(args)
        print(f"ledger_classifier complete: {result}")
        return 0
    if args.pipeline == "ledger_full":
        result = run_ledger_full(args)
        print(f"ledger_full complete: {result}")
        return 0
    if args.pipeline == "ledger_smoke":
        result = run_ledger_smoke(args)
        print(f"ledger_smoke complete: {result}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
