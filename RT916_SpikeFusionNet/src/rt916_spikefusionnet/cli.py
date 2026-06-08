from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from rt916_spikefusionnet import core
from rt916_spikefusionnet.policy import (
    PACKAGE_OUT_ROOT,
    PROFILE,
    assemble_dayahead_release_bundle,
    assemble_realtime_release_bundle,
    write_release_bundle,
)


TARGET_MAP = {
    "dayahead": "日前电价",
    "realtime": "实时电价",
}


def default_asof(start_ts: str) -> str:
    ts = pd.Timestamp(start_ts)
    return (ts.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=15)).strftime("%Y-%m-%d %H:%M:%S")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Formal release-safe CLI for RT916_SpikeFusionNet")
    parser.add_argument("--mode", default="run", choices=["run", "daily_backtest", "joint_da_rt", "release_bundle"])
    parser.add_argument("--target", default="dayahead", choices=["dayahead", "realtime", "all"])
    parser.add_argument("--start", required=True, help="Inclusive start timestamp, e.g. 2025-01-01 01:00:00")
    parser.add_argument("--end", required=True, help="Inclusive end timestamp, e.g. 2025-01-31 00:00:00")
    parser.add_argument("--mod", default="all", choices=["all", "stage1", "stage2", "stage3"])
    parser.add_argument("--asof", default=None, help="Optional asof timestamp for mode=run")
    parser.add_argument("--asof-hour", type=int, default=15)
    parser.add_argument("--force-policy-recompute", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def dry_run_payload(args: argparse.Namespace) -> dict[str, object]:
    return {
        "package_root": str(Path(__file__).resolve().parents[2]),
        "package_output_root": str(PACKAGE_OUT_ROOT),
        "mode": args.mode,
        "target": args.target,
        "start": args.start,
        "end": args.end,
        "mod": args.mod,
        "asof": args.asof or default_asof(args.start),
        "asof_hour": args.asof_hour,
        "force_policy_recompute": bool(args.force_policy_recompute),
        "release_safe_best_policy": PROFILE["release_safe"]["best_policy"],
        "release_safe_locked_from_experiment": PROFILE["release_safe"]["locked_from_experiment"],
    }


def run_release_bundle(args: argparse.Namespace) -> dict[str, object]:
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end)
    outputs: dict[str, object] = {"mode": "release_bundle", "target": args.target}
    if args.target in {"realtime", "all"}:
        rt_annual, rt_monthly, rt_sources = assemble_realtime_release_bundle(start_ts, end_ts)
        outputs["realtime"] = write_release_bundle("realtime", start_ts, end_ts, rt_annual, rt_monthly, rt_sources)
    if args.target in {"dayahead", "all"}:
        da_annual, da_monthly, da_policy, da_sources = assemble_dayahead_release_bundle(
            start_ts,
            end_ts,
            force_recompute=args.force_policy_recompute,
        )
        outputs["dayahead"] = write_release_bundle("dayahead", start_ts, end_ts, da_annual, da_monthly, da_sources, da_policy)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = dry_run_payload(args)
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.mode == "run":
        if args.target == "all":
            raise SystemExit("--target all is only supported for mode=release_bundle")
        result = core.run(
            target=TARGET_MAP[args.target],
            start_end_list=[args.start, args.end],
            mod=args.mod,
            asof_ts=args.asof or default_asof(args.start),
            enforce_asof_cutoff=True,
        )
        print(json.dumps({"mode": "run", "rows": int(len(result)), "output_root": str(PACKAGE_OUT_ROOT)}, ensure_ascii=False, indent=2))
        return 0

    if args.mode == "daily_backtest":
        if args.target == "all":
            raise SystemExit("--target all is only supported for mode=release_bundle")
        result = core.run_daily_asof_backtest(
            target=TARGET_MAP[args.target],
            start_end_list=[args.start, args.end],
            mod=args.mod,
            asof_hour=args.asof_hour,
            retrain_daily=False,
        )
        print(json.dumps({"mode": "daily_backtest", "rows": int(len(result)), "output_root": str(PACKAGE_OUT_ROOT)}, ensure_ascii=False, indent=2))
        return 0

    if args.mode == "joint_da_rt":
        result = core.run_joint_da_rt_daily_backtest(
            start_end_list=[args.start, args.end],
            mod=args.mod,
            asof_hour=args.asof_hour,
        )
        print(json.dumps({"mode": "joint_da_rt", "rows": int(len(result)), "output_root": str(PACKAGE_OUT_ROOT)}, ensure_ascii=False, indent=2))
        return 0

    outputs = run_release_bundle(args)
    print(json.dumps(outputs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
