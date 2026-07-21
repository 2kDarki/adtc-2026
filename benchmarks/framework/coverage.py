"""Coverage analysis for benchmark suites.

Reports category distribution, difficulty distribution, language coverage,
question counts, duplicate detection, and identifies weak areas.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .models import EvalDataset


@dataclass
class CoverageReport:
    """Coverage analysis for a single dataset or across multiple datasets."""

    total_items: int
    categories: dict[str, int]
    subcategories: dict[str, int]
    difficulty_distribution: dict[str, int]
    language_distribution: dict[str, int]
    duplicate_ids: list[str]
    duplicate_questions: list[str]
    avg_question_length: float
    avg_answer_length: float
    avg_rubric_criteria: float
    uncovered_categories: list[str]  # categories with 0 items
    tag_frequency: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "categories": self.categories,
            "subcategories": self.subcategories,
            "difficulty_distribution": self.difficulty_distribution,
            "language_distribution": self.language_distribution,
            "duplicate_ids": self.duplicate_ids,
            "duplicate_questions": self.duplicate_questions,
            "avg_question_length": round(self.avg_question_length, 1),
            "avg_answer_length": round(self.avg_answer_length, 1),
            "avg_rubric_criteria": round(self.avg_rubric_criteria, 1),
            "uncovered_categories": self.uncovered_categories,
            "tag_frequency": self.tag_frequency,
        }

    def terminal_report(self) -> str:
        lines = [
            "Coverage Analysis",
            "=" * 50,
            f"  Total items: {self.total_items}",
            "",
            "  Categories:",
        ]
        for cat, count in sorted(self.categories.items(), key=lambda x: -x[1]):
            lines.append(f"    {cat:<35} {count}")

        if self.subcategories:
            lines += ["", "  Subcategories:"]
            for sub, count in sorted(self.subcategories.items(), key=lambda x: -x[1]):
                lines.append(f"    {sub:<35} {count}")

        lines += ["", "  Difficulty distribution:"]
        for diff, count in sorted(self.difficulty_distribution.items()):
            lines.append(f"    {diff:<35} {count}")

        lines += ["", "  Language distribution:"]
        for lang, count in sorted(self.language_distribution.items(), key=lambda x: -x[1]):
            lines.append(f"    {lang:<35} {count}")

        lines += [
            "",
            f"  Avg question length:  {self.avg_question_length:.0f} chars",
            f"  Avg answer length:    {self.avg_answer_length:.0f} chars",
            f"  Avg rubric criteria:  {self.avg_rubric_criteria:.1f}",
        ]

        if self.duplicate_ids:
            lines += ["", f"  Duplicate IDs: {len(self.duplicate_ids)}"]
        if self.duplicate_questions:
            lines += [f"  Duplicate questions: {len(self.duplicate_questions)}"]

        if self.uncovered_categories:
            lines += ["", "  WARNING: Categories with no items:"]
            for cat in self.uncovered_categories:
                lines.append(f"    - {cat}")

        if self.tag_frequency:
            lines += ["", "  Top tags:"]
            for tag, count in sorted(self.tag_frequency.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"    {tag:<35} {count}")

        return "\n".join(lines)


def analyze_coverage(
    datasets: list[EvalDataset],
    expected_categories: list[str] | None = None,
) -> CoverageReport:
    """Analyze coverage across one or more datasets."""
    categories: Counter[str] = Counter()
    subcategories: Counter[str] = Counter()
    difficulties: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    seen_ids: dict[str, int] = {}
    seen_questions: dict[str, int] = {}
    duplicate_ids: list[str] = []
    duplicate_questions: list[str] = []
    total_q_len = 0
    total_a_len = 0
    total_rubric = 0
    total_items = 0

    for dataset in datasets:
        for item in dataset.items:
            total_items += 1
            categories[item.category] += 1
            if item.subcategory:
                subcategories[item.subcategory] += 1
            difficulties[item.difficulty.value] += 1
            languages[item.language] += 1
            for tag in item.tags:
                tags[tag] += 1

            if item.id in seen_ids:
                duplicate_ids.append(item.id)
            seen_ids[item.id] = seen_ids.get(item.id, 0) + 1

            q_key = item.question.strip().lower()
            if q_key in seen_questions:
                duplicate_questions.append(item.id)
            seen_questions[q_key] = seen_questions.get(q_key, 0) + 1

            total_q_len += len(item.question)
            total_a_len += len(item.expected_answer)
            total_rubric += len(item.rubric)

    n = max(total_items, 1)

    # Find uncovered categories
    uncovered: list[str] = []
    if expected_categories:
        uncovered = [c for c in expected_categories if c not in categories]

    return CoverageReport(
        total_items=total_items,
        categories=dict(categories),
        subcategories=dict(subcategories),
        difficulty_distribution=dict(difficulties),
        language_distribution=dict(languages),
        duplicate_ids=duplicate_ids,
        duplicate_questions=duplicate_questions,
        avg_question_length=total_q_len / n,
        avg_answer_length=total_a_len / n,
        avg_rubric_criteria=total_rubric / n,
        uncovered_categories=uncovered,
        tag_frequency=dict(tags),
    )
