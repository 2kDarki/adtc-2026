"""Validation tool for evaluation datasets.

Checks:
- Valid schema conformance
- Duplicate IDs
- Duplicate questions
- Empty required fields
- Malformed rubrics (missing criteria, bad weights)
- Invalid difficulty values
- Invalid categories (optional allowlist)
- Missing metadata
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import EvalDataset, EvalItem, Difficulty


@dataclass
class ValidationIssue:
    """A single validation problem."""

    severity: str  # "error" or "warning"
    item_id: str | None
    field: str
    message: str

    def __str__(self) -> str:
        loc = f"[{self.item_id}] " if self.item_id else ""
        return f"{self.severity.upper()}: {loc}{self.field}: {self.message}"


@dataclass
class ValidationReport:
    """Complete validation report for a dataset."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, item_id: str | None, field: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", item_id, field, message))

    def add_warning(self, item_id: str | None, field: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", item_id, field, message))

    def summary(self) -> str:
        lines = [
            f"Validation Report: {len(self.errors)} errors, {len(self.warnings)} warnings",
            "",
        ]
        if not self.issues:
            lines.append("  All checks passed.")
        else:
            for issue in self.issues:
                lines.append(f"  {issue}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.is_valid,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [
                {
                    "severity": i.severity,
                    "item_id": i.item_id,
                    "field": i.field,
                    "message": i.message,
                }
                for i in self.issues
            ],
        }


def validate_dataset(dataset: EvalDataset, valid_categories: list[str] | None = None) -> ValidationReport:
    """Run all validation checks on a dataset. Returns a report."""
    report = ValidationReport()

    seen_ids: dict[str, int] = {}
    seen_questions: dict[str, int] = {}

    for idx, item in enumerate(dataset.items):
        iid = item.id or f"<index {idx}>"

        # Duplicate ID check
        if item.id in seen_ids:
            report.add_error(iid, "id", f"Duplicate ID '{item.id}' (first at index {seen_ids[item.id]})")
        seen_ids[item.id] = idx

        # Duplicate question check
        q_key = item.question.strip().lower()
        if q_key in seen_questions:
            report.add_warning(iid, "question", f"Duplicate question (first at index {seen_questions[q_key]})")
        seen_questions[q_key] = idx

        # Empty field checks
        if not item.id.strip():
            report.add_error(iid, "id", "Empty ID")
        if not item.category.strip():
            report.add_error(iid, "category", "Empty category")
        if not item.question.strip():
            report.add_error(iid, "question", "Empty question")
        if not item.expected_answer.strip():
            report.add_error(iid, "expected_answer", "Empty expected_answer")

        # Difficulty validation
        try:
            Difficulty(item.difficulty.value)
        except ValueError:
            report.add_error(iid, "difficulty", f"Invalid difficulty '{item.difficulty}'")

        # Category validation
        if valid_categories and item.category not in valid_categories:
            report.add_warning(iid, "category", f"Category '{item.category}' not in allowlist")

        # Rubric validation
        if not item.rubric:
            report.add_error(iid, "rubric", "Rubric is empty (at least one criterion required)")
        else:
            total_weight = sum(r.weight for r in item.rubric)
            if abs(total_weight - 1.0) > 0.01:
                report.add_warning(iid, "rubric", f"Rubric weights sum to {total_weight:.3f}, expected ~1.0")
            for r in item.rubric:
                if not r.criterion.strip():
                    report.add_error(iid, "rubric", "Empty criterion text")
                if r.weight <= 0:
                    report.add_error(iid, "rubric", f"Criterion weight must be > 0, got {r.weight}")

        # Language check
        if len(item.language) < 2:
            report.add_error(iid, "language", f"Language code too short: '{item.language}'")

        # Source validation
        if item.source.type.value == "document" and not item.source.document:
            report.add_warning(iid, "source.document", "Source type is 'document' but no document field set")
        if item.source.type.value == "web" and not item.source.url:
            report.add_warning(iid, "source.url", "Source type is 'web' but no url field set")

    return report


def validate_file(path: Path, valid_categories: list[str] | None = None) -> ValidationReport:
    """Load and validate a JSON dataset file."""
    data = json.loads(path.read_text())
    dataset = EvalDataset.from_dict(data)
    return validate_dataset(dataset, valid_categories)
