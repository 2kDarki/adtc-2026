#!/usr/bin/env python3
"""CLI entry point for the benchmark suite framework.

Usage:
    python -m benchmarks.framework.cli list
    python -m benchmarks.framework.cli describe <suite>
    python -m benchmarks.framework.cli validate <suite>
    python -m benchmarks.framework.cli evaluate <suite> [--model NAME] [--format FORMAT]
    python -m benchmarks.framework.cli evaluate --all [--model NAME]
    python -m benchmarks.framework.cli coverage [<suite>...]
    python -m benchmarks.framework.cli history <suite> <version>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure parent directory is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from benchmarks.framework.engine import EvaluationEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ADTC Benchmark Suite Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list
    sub.add_parser("list", help="List available benchmark suites")

    # describe
    p_desc = sub.add_parser("describe", help="Describe a benchmark suite")
    p_desc.add_argument("suite", help="Suite ID")

    # validate
    p_val = sub.add_parser("validate", help="Validate a suite's dataset")
    p_val.add_argument("suite", help="Suite ID")
    p_val.add_argument("--version", default=None, help="Suite version (default: latest)")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate suite(s)")
    p_eval.add_argument("suites", nargs="*", help="Suite IDs (empty = all)")
    p_eval.add_argument("--all", action="store_true", help="Evaluate all suites")
    p_eval.add_argument("--model", default="unknown", help="Model name")
    p_eval.add_argument("--format", default="terminal", choices=["terminal", "json", "markdown"])
    p_eval.add_argument("--output", default=None, help="Output file path")

    # coverage
    p_cov = sub.add_parser("coverage", help="Coverage analysis")
    p_cov.add_argument("suites", nargs="*", help="Suite IDs (empty = all)")

    # history
    p_hist = sub.add_parser("history", help="Show historical runs")
    p_hist.add_argument("suite", help="Suite ID")
    p_hist.add_argument("version", help="Suite version")

    args = parser.parse_args()
    engine = EvaluationEngine()

    if args.command == "list":
        print(engine.list_suites())

    elif args.command == "describe":
        print(engine.describe(args.suite))

    elif args.command == "validate":
        print(engine.validate(args.suite, args.version))

    elif args.command == "evaluate":
        suite_ids = args.suites if args.suites else None
        if args.all:
            suite_ids = None
        if not suite_ids and not args.all:
            print("error: specify suite IDs or use --all", file=sys.stderr)
            sys.exit(1)
        result = engine.evaluate(
            suite_ids=suite_ids,
            model_name=args.model,
            output_format=args.format,
            output_path=args.output,
        )
        print(result)

    elif args.command == "coverage":
        result = engine.coverage(args.suites if args.suites else None)
        print(result)

    elif args.command == "history":
        print(engine.history(args.suite, args.version))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
