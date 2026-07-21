"""Data models for evaluation items.

These dataclasses mirror the JSON schema and provide type-safe access
to evaluation item fields. All models are immutable after creation
and serialize cleanly to/from JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class SourceType(str, Enum):
    MANUAL = "manual"
    DOCUMENT = "document"
    SYNTHETIC = "synthetic"
    CSV = "csv"
    WEB = "web"


@dataclass(frozen=True)
class RubricCriterion:
    """A single scoring criterion within a rubric."""

    criterion: str
    weight: float
    required: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.weight <= 1:
            raise ValueError(f"weight must be 0-1, got {self.weight}")


@dataclass(frozen=True)
class Source:
    """Provenance metadata for an evaluation item."""

    type: SourceType
    document: str | None = None
    page: int | None = None
    url: str | None = None
    publication: str | None = None
    author: str | None = None
    publication_date: str | None = None


@dataclass(frozen=True)
class EvalItem:
    """A single evaluation item."""

    id: str
    category: str
    difficulty: Difficulty
    question: str
    expected_answer: str
    rubric: list[RubricCriterion]
    language: str
    source: Source
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    subcategory: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str | None = None
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        d = asdict(self)
        d["difficulty"] = self.difficulty.value
        d["source"]["type"] = self.source.type.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalItem:
        """Deserialize from a dict (e.g. parsed JSON)."""
        source_data = data.get("source", {})
        rubric_data = data.get("rubric", [])

        return cls(
            id=data["id"],
            category=data["category"],
            subcategory=data.get("subcategory", ""),
            difficulty=Difficulty(data["difficulty"]),
            question=data["question"],
            expected_answer=data["expected_answer"],
            rubric=[RubricCriterion(**r) for r in rubric_data],
            tags=data.get("tags", []),
            language=data["language"],
            notes=data.get("notes", ""),
            source=Source(
                type=SourceType(source_data.get("type", "manual")),
                document=source_data.get("document"),
                page=source_data.get("page"),
                url=source_data.get("url"),
                publication=source_data.get("publication"),
                author=source_data.get("author"),
                publication_date=source_data.get("publication_date"),
            ),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at"),
            version=data.get("version", 1),
        )


@dataclass(frozen=True)
class EvalDataset:
    """A collection of evaluation items with dataset-level metadata."""

    name: str
    domain: str
    version: str
    items: list[EvalItem]
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "version": self.version,
            "description": self.description,
            "created_at": self.created_at,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalDataset:
        return cls(
            name=data["name"],
            domain=data["domain"],
            version=data["version"],
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            items=[EvalItem.from_dict(item) for item in data.get("items", [])],
        )
