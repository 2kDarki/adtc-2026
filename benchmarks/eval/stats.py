"""Dataset statistics and reporting.

Reports:
- Number of questions
- Categories and subcategories
- Difficulty distribution
- Language distribution
- Duplicate detection
- Average question length
- Average expected-answer length
- Rubric coverage
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .models import EvalDataset


@dataclass
class DatasetStats:
    """Computed statistics for an evaluation dataset."""

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
            "tag_frequency": self.tag_frequency,
        }

    def terminal_report(self) -> str:
        """Human-readable terminal report."""
        lines = [
            "Dataset Statistics",
            "=" * 40,
            f"  Total items:            {self.total_items}",
            "",
            "  Categories:",
        ]
        for cat, count in sorted(self.categories.items(), key=lambda x: -x[1]):
            lines.append(f"    {cat:<30} {count}")

        if self.subcategories:
            lines.append("")
            lines.append("  Subcategories:")
            for sub, count in sorted(self.subcategories.items(), key=lambda x: -x[1]):
                lines.append(f"    {sub:<30} {count}")

        lines += [
            "",
            "  Difficulty distribution:",
        ]
        for diff, count in sorted(self.difficulty_distribution.items()):
            lines.append(f"    {diff:<30} {count}")

        lines += [
            "",
            "  Language distribution:",
        ]
        for lang, count in sorted(self.language_distribution.items(), key=lambda x: -x[1]):
            lines.append(f"    {lang:<30} {count}")

        lines += [
            "",
            f"  Avg question length:    {self.avg_question_length:.0f} chars",
            f"  Avg answer length:      {self.avg_answer_length:.0f} chars",
            f"  Avg rubric criteria:    {self.avg_rubric_criteria:.1f}",
        ]

        if self.duplicate_ids:
            lines += [
                "",
                f"  Duplicate IDs:          {len(self.duplicate_ids)}",
            ]
            for d in self.duplicate_ids[:5]:
                lines.append(f"    - {d}")

        if self.duplicate_questions:
            lines += [
                "",
                f"  Duplicate questions:    {len(self.duplicate_questions)}",
            ]

        if self.tag_frequency:
            lines += [
                "",
                "  Top tags:",
            ]
            for tag, count in sorted(self.tag_frequency.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"    {tag:<30} {count}")

        return "\n".join(lines)


def compute_stats(dataset: EvalDataset) -> DatasetStats:
    """Compute statistics for a dataset."""
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

    for item in dataset.items:
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

    n = max(len(dataset.items), 1)

    return DatasetStats(
        total_items=len(dataset.items),
        categories=dict(categories),
        subcategories=dict(subcategories),
        difficulty_distribution=dict(difficulties),
        language_distribution=dict(languages),
        duplicate_ids=duplicate_ids,
        duplicate_questions=duplicate_questions,
        avg_question_length=total_q_len / n,
        avg_answer_length=total_a_len / n,
        avg_rubric_criteria=total_rubric / n,
        tag_frequency=dict(tags),
    )
