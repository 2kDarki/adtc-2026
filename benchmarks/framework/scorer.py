"""Scorer — scores model outputs against rubrics.

Supports rubric-based scoring where each criterion is evaluated independently.
Actual LLM judging is a placeholder — the architecture supports plugging in
automated scoring later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import EvalItem, EvalDataset, RubricCriterion


@dataclass
class ScoredCriterion:
    """Score for a single rubric criterion."""
    criterion: str
    weight: float
    score: float  # 0.0 to 1.0
    required: bool = False
    passed: bool = True
    notes: str = ""


@dataclass
class ItemScore:
    """Score for a single evaluation item."""
    item_id: str
    category: str
    difficulty: str
    criteria_scores: list[ScoredCriterion]
    total_score: float  # weighted sum, 0.0 to 1.0
    passed: bool  # all required criteria passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "difficulty": self.difficulty,
            "total_score": round(self.total_score, 4),
            "passed": self.passed,
            "criteria": [
                {
                    "criterion": c.criterion,
                    "weight": c.weight,
                    "score": round(c.score, 4),
                    "required": c.required,
                    "passed": c.passed,
                    "notes": c.notes,
                }
                for c in self.criteria_scores
            ],
        }


@dataclass
class SuiteScore:
    """Aggregated scores for an entire suite."""
    suite_id: str
    suite_version: str
    model_name: str
    item_scores: list[ItemScore]
    overall_score: float  # average of item scores, 0.0 to 1.0
    category_scores: dict[str, float]  # per-category averages
    passed_count: int
    total_count: int
    pass_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "model_name": self.model_name,
            "overall_score": round(self.overall_score, 4),
            "category_scores": {k: round(v, 4) for k, v in self.category_scores.items()},
            "passed": self.passed_count,
            "total": self.total_count,
            "pass_rate": round(self.pass_rate, 4),
            "items": [s.to_dict() for s in self.item_scores],
        }


class Scorer:
    """Scores evaluation items against model outputs.

    In the current implementation, scoring is done by comparing the model's
    response against the expected_answer using rubric criteria. The actual
    comparison is a placeholder that can be replaced with LLM judging.
    """

    def __init__(self, rubric_threshold: float = 0.5) -> None:
        """Initialize scorer.

        Args:
            rubric_threshold: Minimum score for a criterion to be considered passed.
        """
        self.rubric_threshold = rubric_threshold

    def score_item(self, item: EvalItem, model_answer: str) -> ItemScore:
        """Score a single item's model answer against its rubric.

        This is a placeholder implementation. In production, this would use
        an LLM judge or semantic similarity to evaluate each criterion.
        """
        criteria_scores = []
        for rubric in item.rubric:
            # Placeholder: simple keyword/substring matching
            score = self._evaluate_criterion(model_answer, item.expected_answer, rubric)
            passed = score >= self.rubric_threshold
            if rubric.required and not passed:
                passed = False
            criteria_scores.append(ScoredCriterion(
                criterion=rubric.criterion,
                weight=rubric.weight,
                score=score,
                required=rubric.required,
                passed=passed,
            ))

        total_score = sum(c.score * c.weight for c in criteria_scores)
        passed = all(c.passed for c in criteria_scores)

        return ItemScore(
            item_id=item.id,
            category=item.category,
            difficulty=item.difficulty.value,
            criteria_scores=criteria_scores,
            total_score=total_score,
            passed=passed,
        )

    def score_dataset(
        self, dataset: EvalDataset, model_answers: dict[str, str], model_name: str = "unknown"
    ) -> SuiteScore:
        """Score all items in a dataset.

        Args:
            dataset: The evaluation dataset.
            model_answers: Dict mapping item_id to model's answer string.
            model_name: Name of the model being evaluated.
        """
        item_scores = []
        for item in dataset.items:
            answer = model_answers.get(item.id, "")
            item_scores.append(self.score_item(item, answer))

        if not item_scores:
            return SuiteScore(
                suite_id=dataset.domain,
                suite_version=dataset.version,
                model_name=model_name,
                item_scores=[],
                overall_score=0.0,
                category_scores={},
                passed_count=0,
                total_count=0,
                pass_rate=0.0,
            )

        overall = sum(s.total_score for s in item_scores) / len(item_scores)

        # Per-category averages
        cat_totals: dict[str, list[float]] = {}
        for s in item_scores:
            cat_totals.setdefault(s.category, []).append(s.total_score)
        category_scores = {cat: sum(scores) / len(scores) for cat, scores in cat_totals.items()}

        passed = sum(1 for s in item_scores if s.passed)

        return SuiteScore(
            suite_id=dataset.domain,
            suite_version=dataset.version,
            model_name=model_name,
            item_scores=item_scores,
            overall_score=overall,
            category_scores=category_scores,
            passed_count=passed,
            total_count=len(item_scores),
            pass_rate=passed / len(item_scores),
        )

    def _evaluate_criterion(self, model_answer: str, expected: str, rubric: RubricCriterion) -> float:
        """Placeholder criterion evaluation.

        In production, this would use LLM judging or semantic similarity.
        Currently returns a simple heuristic score.
        """
        model_lower = model_answer.lower()
        criterion_lower = rubric.criterion.lower()

        # Simple heuristic: check if key phrases from expected answer appear
        expected_words = set(expected.lower().split())
        model_words = set(model_lower.split())
        if not expected_words:
            return 0.0

        overlap = len(expected_words & model_words) / len(expected_words)
        return min(overlap * 1.5, 1.0)  # Boost overlap, cap at 1.0
