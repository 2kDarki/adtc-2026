"""Unified evaluation engine.

Supports execution modes:
- Single suite: evaluate coding
- Multiple suites: evaluate coding,reasoning
- All suites: evaluate --all
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .loader import load_dataset, load_suite_metadata
from .registry import SuiteRegistry
from .validator import validate_dataset
from .scorer import Scorer, SuiteScore
from .reporter import get_reporter, report_to_file
from .coverage import analyze_coverage
from .results import ResultsStore
from .models import BenchmarkRun


class EvaluationEngine:
    """Unified evaluation engine for benchmark suites."""

    def __init__(
        self,
        suites_dir: Path | str | None = None,
        results_dir: Path | str | None = None,
    ) -> None:
        self.registry = SuiteRegistry(suites_dir)
        self.results = ResultsStore(results_dir)
        self.scorer = Scorer()

    def list_suites(self) -> str:
        """List all available suites."""
        suites = self.registry.list_suites()
        if not suites:
            return "No benchmark suites found."

        lines = ["Available benchmark suites:", ""]
        for meta in sorted(suites, key=lambda m: m.id):
            lines.append(f"  {meta.id:<20} v{meta.version:<8} {meta.name}")
            lines.append(f"  {'':20} {meta.description[:60]}")
            lines.append(f"  {'':20} Languages: {', '.join(meta.languages)}")
            lines.append("")
        return "\n".join(lines)

    def describe(self, suite_id: str) -> str:
        """Describe a specific suite."""
        return self.registry.describe(suite_id)

    def validate(self, suite_id: str, version: str | None = None) -> str:
        """Validate a suite's dataset."""
        result = self.registry.get_suite(suite_id, version)
        if result is None:
            return f"Suite '{suite_id}' not found."

        path, meta = result
        dataset = load_dataset(path)
        report = validate_dataset(dataset)
        return f"Suite: {meta.id} v{meta.version}\n\n{report.summary()}"

    def coverage(self, suite_ids: list[str] | None = None) -> str:
        """Generate coverage report for one or more suites."""
        datasets = []
        for sid in (suite_ids or []):
            result = self.registry.get_suite(sid)
            if result is not None:
                path, _ = result
                datasets.append(load_dataset(path))

        if not datasets:
            # Load all suites
            for path, meta in self.registry.discover().values():
                try:
                    datasets.append(load_dataset(path))
                except FileNotFoundError:
                    continue

        if not datasets:
            return "No datasets found."

        report = analyze_coverage(datasets)
        return report.terminal_report()

    def evaluate(
        self,
        suite_ids: list[str] | None = None,
        model_name: str = "unknown",
        model_answers: dict[str, dict[str, str]] | None = None,
        output_format: str = "terminal",
        output_path: str | Path | None = None,
    ) -> str:
        """Evaluate one or more suites.

        Args:
            suite_ids: List of suite IDs to evaluate. None = all suites.
            model_name: Name of the model being evaluated.
            model_answers: Dict of {suite_id: {item_id: answer}} mapping.
            output_format: Output format (terminal, json, markdown).
            output_path: Optional path to write the report.

        Returns:
            The report string.
        """
        # Resolve suites to evaluate
        if suite_ids is None:
            # All suites
            all_suites = self.registry.list_suites()
            suite_ids = [m.id for m in all_suites]

        if not suite_ids:
            return "No suites specified and none found."

        scores: list[SuiteScore] = []
        metadata_list = []

        for sid in suite_ids:
            result = self.registry.get_suite(sid)
            if result is None:
                print(f"Warning: suite '{sid}' not found, skipping.")
                continue

            path, meta = result
            metadata_list.append(meta)

            try:
                dataset = load_dataset(path)
            except FileNotFoundError:
                print(f"Warning: no dataset.json in suite '{sid}', skipping.")
                continue

            # Validate first
            val_report = validate_dataset(dataset)
            if not val_report.is_valid:
                print(f"Warning: suite '{sid}' has validation errors, skipping.")
                continue

            # Get model answers for this suite
            answers = (model_answers or {}).get(sid, {})

            # Score
            score = self.scorer.score_dataset(dataset, answers, model_name)
            scores.append(score)

        if not scores:
            return "No suites could be evaluated."

        # Generate report
        reporter = get_reporter(output_format)
        report = reporter.report(scores, metadata_list)

        # Save to file if requested
        if output_path:
            report_to_file(report, output_path)

        # Save to historical results
        for score in scores:
            run = BenchmarkRun(
                run_id=uuid.uuid4().hex[:12],
                suite_id=score.suite_id,
                suite_version=score.suite_version,
                model_name=model_name,
                scores=score.to_dict(),
                metadata={"output_format": output_format},
            )
            self.results.save(run)

        return report

    def history(self, suite_id: str, version: str) -> str:
        """Show historical runs for a suite version."""
        runs = self.results.list_runs(suite_id, version)
        if not runs:
            return f"No historical runs found for {suite_id} {version}."

        lines = [f"Historical runs for {suite_id} v{version}:", ""]
        for r in runs:
            lines.append(f"  {r['run_id']:<15} {r['timestamp']:<25} {r['model_name']:<20} score={r['overall_score']:.2%}")
        return "\n".join(lines)
