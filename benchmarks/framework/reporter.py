"""Reporter — generates reports from benchmark results.

Supports terminal, JSON, and markdown output formats.
Designed for extensibility — add new formats by subclassing BaseReporter.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import BenchmarkRun, SuiteMetadata
from .scorer import SuiteScore


class BaseReporter(ABC):
    """Abstract base class for reporters."""

    name: str = "base"
    extension: str = ".txt"

    @abstractmethod
    def report(self, scores: list[SuiteScore], metadata: list[SuiteMetadata] | None = None) -> str:
        ...


class TerminalReporter(BaseReporter):
    """Human-readable terminal output."""

    name = "terminal"
    extension = ".txt"

    def report(self, scores: list[SuiteScore], metadata: list[SuiteMetadata] | None = None) -> str:
        lines = [
            "ADTC Benchmark Results",
            "=" * 60,
            f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"  Suites evaluated: {len(scores)}",
            "",
        ]

        for score in scores:
            lines += [
                f"Suite: {score.suite_id} v{score.suite_version}",
                f"  Model:           {score.model_name}",
                f"  Overall score:   {score.overall_score:.2%}",
                f"  Pass rate:       {score.pass_rate:.2%} ({score.passed_count}/{score.total_count})",
                "",
                "  Category breakdown:",
            ]
            for cat, s in sorted(score.category_scores.items()):
                lines.append(f"    {cat:<30} {s:.2%}")

            lines += [
                "",
                "  Item details:",
            ]
            for item in score.item_scores:
                status = "PASS" if item.passed else "FAIL"
                lines.append(f"    [{status}] {item.item_id:<40} {item.total_score:.2%} ({item.difficulty})")

            lines.append("")

        # Overall summary
        if len(scores) > 1:
            avg = sum(s.overall_score for s in scores) / len(scores)
            lines += [
                "Overall Summary",
                "-" * 40,
                f"  Average score: {avg:.2%}",
                f"  Best suite:    {max(scores, key=lambda s: s.overall_score).suite_id}",
                f"  Worst suite:   {min(scores, key=lambda s: s.overall_score).suite_id}",
            ]

        return "\n".join(lines)


class JSONReporter(BaseReporter):
    """Machine-readable JSON output."""

    name = "json"
    extension = ".json"

    def report(self, scores: list[SuiteScore], metadata: list[SuiteMetadata] | None = None) -> str:
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "suite_count": len(scores),
            "suites": [s.to_dict() for s in scores],
        }
        if metadata:
            data["metadata"] = [m.to_dict() for m in metadata]
        return json.dumps(data, indent=2)


class MarkdownReporter(BaseReporter):
    """Markdown report output."""

    name = "markdown"
    extension = ".md"

    def report(self, scores: list[SuiteScore], metadata: list[SuiteMetadata] | None = None) -> str:
        lines = [
            "# ADTC Benchmark Results",
            "",
            f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Suites evaluated**: {len(scores)}",
            "",
        ]

        for score in scores:
            lines += [
                f"## {score.suite_id} v{score.suite_version}",
                "",
                f"- **Model**: {score.model_name}",
                f"- **Overall score**: {score.overall_score:.2%}",
                f"- **Pass rate**: {score.pass_rate:.2%} ({score.passed_count}/{score.total_count})",
                "",
                "### Category Breakdown",
                "",
                "| Category | Score |",
                "|----------|-------|",
            ]
            for cat, s in sorted(score.category_scores.items()):
                lines.append(f"| {cat} | {s:.2%} |")

            lines += [
                "",
                "### Item Results",
                "",
                "| Status | Item ID | Score | Difficulty |",
                "|--------|---------|-------|------------|",
            ]
            for item in score.item_scores:
                status = "PASS" if item.passed else "FAIL"
                lines.append(f"| {status} | {item.item_id} | {item.total_score:.2%} | {item.difficulty} |")

            lines.append("")

        return "\n".join(lines)


# Reporter registry
REPORTERS: dict[str, type[BaseReporter]] = {
    "terminal": TerminalReporter,
    "json": JSONReporter,
    "markdown": MarkdownReporter,
}


def get_reporter(name: str) -> BaseReporter:
    """Get a reporter by name."""
    if name not in REPORTERS:
        raise ValueError(f"Unknown reporter '{name}'. Available: {list(REPORTERS.keys())}")
    return REPORTERS[name]()


def report_to_file(report: str, path: Path | str) -> None:
    """Write a report to a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report)
