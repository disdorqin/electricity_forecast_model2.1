#!/usr/bin/env python
"""
Lightweight CLI argument validation for main.py range/single-date commands.

Does NOT run any model code. Only validates argument parsing and normalization.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.parser import build_parser, normalize_date_args


def _parse_argv(argv: list[str]) -> tuple:
    """
    Parse argv and normalize_date_args.
    Returns (args, error_or_None).
    Captures parser.error() which calls sys.exit(2) after printing to stderr.
    """
    parser = build_parser()
    # Capture stderr to check error messages
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        args = parser.parse_args(argv[1:])
        normalize_date_args(args, parser)
        sys.stderr = old_stderr
        return args, None
    except SystemExit:
        error_text = sys.stderr.getvalue()
        sys.stderr = old_stderr
        return None, error_text.strip()


def check(name: str, argv: list[str], checks: dict) -> bool:
    """Run a single test case."""
    args, error = _parse_argv(argv)
    if error:
        expected = checks.pop("expect_error", None)
        if expected:
            if expected in error:
                print(f"  PASS: {name} — correctly errored")
                return True
            else:
                print(f"  FAIL: {name} — expected '{expected}' in error, got: {error}")
                return False
        print(f"  FAIL: {name} — unexpected error: {error}")
        return False

    # Check expected attributes
    for attr, expected in checks.items():
        actual = getattr(args, attr, None)
        if actual != expected:
            print(f"  FAIL: {name} — {attr}={actual!r}, expected={expected!r}")
            return False

    print(f"  PASS: {name}")
    return True


def main() -> int:
    print("CHECK_CLI_RANGE_ARGS")
    print()

    all_pass = True

    # Test 1: single positional date
    all_pass &= check(
        "single positional date",
        ["main.py", "2026-02-24"],
        {"date": "2026-02-24", "pipeline": "ledger_full"},
    )

    # Test 2: two positional dates
    all_pass &= check(
        "two positional dates",
        ["main.py", "2026-02-24", "2026-02-28"],
        {"start": "2026-02-24", "end": "2026-02-28", "pipeline": "ledger_full_range"},
    )

    # Test 3: --start/--end auto-range
    all_pass &= check(
        "--start/--end auto-range",
        ["main.py", "--start", "2026-02-24", "--end", "2026-02-28"],
        {"start": "2026-02-24", "end": "2026-02-28", "pipeline": "ledger_full_range"},
    )

    # Test 4: explicit range pipeline
    all_pass &= check(
        "explicit range pipeline",
        ["main.py", "--pipeline", "ledger_full_range", "--start", "2026-02-24", "--end", "2026-02-28"],
        {"start": "2026-02-24", "end": "2026-02-28", "pipeline": "ledger_full_range"},
    )

    # Test 5: explicit single-day pipeline
    all_pass &= check(
        "explicit single-day pipeline",
        ["main.py", "--pipeline", "ledger_full", "--date", "2026-02-24"],
        {"date": "2026-02-24", "pipeline": "ledger_full"},
    )

    # Test 6: positional date + --date conflict
    all_pass &= check(
        "positional date + --date conflict",
        ["main.py", "2026-02-24", "--date", "2026-02-25"],
        {"expect_error": "Cannot use both positional date and --date"},
    )

    # Test 7: two positionals + --start/--end conflict
    all_pass &= check(
        "two positionals + --start/--end conflict",
        ["main.py", "2026-02-24", "2026-02-28", "--start", "2026-02-20", "--end", "2026-02-22"],
        {"expect_error": "Cannot use both positional dates and --start/--end"},
    )

    # Test 8: --date + --start conflict
    all_pass &= check(
        "--date + --start conflict",
        ["main.py", "--date", "2026-02-24", "--start", "2026-02-24", "--end", "2026-02-28"],
        {"expect_error": "Cannot use --date together with --start/--end"},
    )

    # Test 9: --start without --end
    all_pass &= check(
        "--start without --end",
        ["main.py", "--start", "2026-02-24"],
        {"expect_error": "Range mode requires both --start and --end"},
    )

    # Test 10: --end without --start
    all_pass &= check(
        "--end without --start",
        ["main.py", "--end", "2026-02-28"],
        {"expect_error": "Range mode requires both --start and --end"},
    )

    # Test 11: start > end
    all_pass &= check(
        "start > end",
        ["main.py", "--start", "2026-02-28", "--end", "2026-02-24"],
        {"expect_error": "must be <= --end"},
    )

    # Test 12: invalid date format
    all_pass &= check(
        "invalid date format",
        ["main.py", "2026-02-30"],
        {"expect_error": "Invalid date"},
    )

    # Test 13: --no-range-preflight works with range
    all_pass &= check(
        "--no-range-preflight with range",
        ["main.py", "--start", "2026-02-24", "--end", "2026-02-28", "--no-range-preflight"],
        {"start": "2026-02-24", "end": "2026-02-28", "pipeline": "ledger_full_range", "range_preflight": False},
    )

    # Test 14: --continue-on-error parsed
    all_pass &= check(
        "--continue-on-error",
        ["main.py", "2026-02-24", "2026-02-28", "--continue-on-error"],
        {"continue_on_error": True},
    )

    # Test 15: --skip-existing-final parsed
    all_pass &= check(
        "--skip-existing-final",
        ["main.py", "2026-02-24", "2026-02-28", "--skip-existing-final"],
        {"skip_existing_final": True},
    )

    print()
    if all_pass:
        print(f"RESULT: ALL {15} TESTS PASSED")
        return 0
    else:
        print(f"RESULT: SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
