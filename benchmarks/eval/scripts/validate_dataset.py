#!/usr/bin/env python3
"""CLI entry point: validate an evaluation dataset.

Usage:
    python -m benchmarks.eval.scripts.validate_dataset <dataset.json>
    python -m benchmarks.eval.scripts.validate_dataset <dataset.json> --categories algorithms,debugging
    python -m benchmarks.eval.scripts.validate_dataset <dataset.json> --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as script or module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from benchmarks.eval.validate import validate_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an evaluation dataset JSON file.")
    parser.add_argument("dataset", type=Path, help="Path to the dataset JSON file")
    parser.add_argument("--categories", type=str, default=None,
                        help="Comma-separated allowlist of valid categories")
    parser.add_argument("--json", action="store_true",
                        help="Output report as JSON instead of terminal text")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"error: file not found: {args.dataset}", file=sys.stderr)
        sys.exit(1)

    categories = args.categories.split(",") if args.categories else None
    report = validate_file(args.dataset, valid_categories=categories)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.summary())

    sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
