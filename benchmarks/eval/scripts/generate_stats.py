#!/usr/bin/env python3
"""CLI entry point: compute and display dataset statistics.

Usage:
    python -m benchmarks.eval.scripts.generate_stats <dataset.json>
    python -m benchmarks.eval.scripts.generate_stats <dataset.json> --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from benchmarks.eval.models import EvalDataset
from benchmarks.eval.stats import compute_stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute statistics for an evaluation dataset.")
    parser.add_argument("dataset", type=Path, help="Path to the dataset JSON file")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of terminal report")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"error: file not found: {args.dataset}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(args.dataset.read_text())
    dataset = EvalDataset.from_dict(data)
    stats = compute_stats(dataset)

    if args.json:
        print(json.dumps(stats.to_dict(), indent=2))
    else:
        print(stats.terminal_report())


if __name__ == "__main__":
    main()
