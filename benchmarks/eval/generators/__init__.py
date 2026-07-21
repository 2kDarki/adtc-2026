"""Evaluation item generators.

Base class and implementations for generating evaluation items from
various sources. New generators subclass BaseGenerator and implement
generate().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import EvalItem, EvalDataset, Difficulty, SourceType, Source, RubricCriterion


class BaseGenerator(ABC):
    """Abstract base class for evaluation item generators."""

    name: str = "base"
    description: str = "Base generator (abstract)"

    @abstractmethod
    def generate(self, **kwargs: Any) -> list[EvalItem]:
        """Generate evaluation items. Subclasses must implement this."""
        ...

    def generate_dataset(
        self,
        name: str,
        domain: str,
        version: str = "0.1.0",
        description: str = "",
        **kwargs: Any,
    ) -> EvalDataset:
        """Generate a full dataset."""
        items = self.generate(**kwargs)
        return EvalDataset(
            name=name,
            domain=domain,
            version=version,
            description=description,
            items=items,
        )


class ManualGenerator(BaseGenerator):
    """Generator for manually curated evaluation items.

    Loads items from a JSON file. This is the simplest generator
    and serves as the reference implementation.
    """

    name = "manual"
    description = "Load evaluation items from a JSON file"

    def generate(self, *, path: str | Path, **kwargs: Any) -> list[EvalItem]:
        import json
        data = json.loads(Path(path).read_text())
        if isinstance(data, list):
            return [EvalItem.from_dict(item) for item in data]
        elif isinstance(data, dict) and "items" in data:
            return [EvalItem.from_dict(item) for item in data["items"]]
        else:
            raise ValueError(f"Expected list or dict with 'items' key, got {type(data)}")


class SyntheticGenerator(BaseGenerator):
    """Generator for synthetic evaluation items from templates.

    Takes a list of template dicts with question/answer patterns
    and generates items by filling in variations. Actual LLM integration
    is left as a placeholder.
    """

    name = "synthetic"
    description = "Generate items from templates (LLM integration placeholder)"

    def generate(
        self,
        *,
        templates: list[dict[str, Any]],
        category: str = "synthetic",
        difficulty: Difficulty = Difficulty.MEDIUM,
        language: str = "en",
        **kwargs: Any,
    ) -> list[EvalItem]:
        from datetime import datetime, timezone
        items = []
        for i, tmpl in enumerate(templates):
            rubric = [
                RubricCriterion(criterion=c["criterion"], weight=c.get("weight", 1.0 / max(len(tmpl.get("rubric", [])), 1)))
                for c in tmpl.get("rubric", [{"criterion": "matches template", "weight": 1.0}])
            ]
            item = EvalItem(
                id=f"synthetic-{category}-{i + 1:04d}",
                category=category,
                difficulty=difficulty,
                question=tmpl["question"],
                expected_answer=tmpl["expected_answer"],
                rubric=rubric,
                language=language,
                source=Source(type=SourceType.SYNTHETIC),
                tags=tmpl.get("tags", []),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            items.append(item)
        return items


class CSVGenerator(BaseGenerator):
    """Generator for evaluation items from CSV files.

    Expects columns: id, category, difficulty, question, expected_answer, language
    Optional columns: subcategory, tags (comma-separated), notes
    Rubric is not expected in CSV — a default rubric is assigned.
    """

    name = "csv"
    description = "Load evaluation items from a CSV file"

    def generate(self, *, path: str | Path, **kwargs: Any) -> list[EvalItem]:
        import csv
        from datetime import datetime, timezone

        items = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
                item = EvalItem(
                    id=row["id"],
                    category=row["category"],
                    subcategory=row.get("subcategory", ""),
                    difficulty=Difficulty(row.get("difficulty", "medium")),
                    question=row["question"],
                    expected_answer=row["expected_answer"],
                    rubric=[RubricCriterion(criterion="matches expected answer", weight=1.0)],
                    language=row.get("language", "en"),
                    tags=tags,
                    notes=row.get("notes", ""),
                    source=Source(type=SourceType.CSV),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                items.append(item)
        return items


# Registry of available generators
GENERATORS: dict[str, type[BaseGenerator]] = {
    "manual": ManualGenerator,
    "synthetic": SyntheticGenerator,
    "csv": CSVGenerator,
}


def get_generator(name: str) -> BaseGenerator:
    """Get a generator instance by name."""
    if name not in GENERATORS:
        raise ValueError(f"Unknown generator '{name}'. Available: {list(GENERATORS.keys())}")
    return GENERATORS[name]()
