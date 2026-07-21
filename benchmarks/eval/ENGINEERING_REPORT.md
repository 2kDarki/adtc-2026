# Engineering Report: Evaluation Dataset Pipeline

## Overview

This report documents the design decisions, trade-offs, and implementation details of the evaluation dataset generation pipeline built for ADTC 2026.

---

## Design Decisions

### 1. JSON Schema for Validation

**Decision**: Use JSON Schema Draft 2020-12 as the canonical validation format.

**Rationale**:
- Machine-readable, IDE-supportable, widely adopted
- Compatible with existing JSON tooling (jsonschema, AJV, etc.)
- Extensible via `additionalProperties: false` on nested objects
- Can be consumed by both Python and JavaScript tooling

**Rejected alternatives**:
- Pydantic models only: Tightly coupled to Python, harder to share with JS tooling
- YAML schema: Less standard tooling support
- Custom validation DSL: Unnecessary complexity for this use case

### 2. Immutable Dataclasses

**Decision**: Use `@dataclass(frozen=True)` for all models.

**Rationale**:
- Prevents accidental mutation of evaluation items
- Items are hashable (can be used in sets for deduplication)
- Clear, Pythonic API with type hints
- Serializable to/from JSON via `to_dict()` / `from_dict()`

**Trade-off**: Requires creating new instances for updates (not in-place modification). This is intentional — evaluation items should be versioned, not mutated.

### 3. Rubric-Based Scoring

**Decision**: Use weighted rubrics instead of exact-answer matching.

**Rationale**:
- LLM outputs vary in wording while being semantically correct
- Rubrics allow fuzzy scoring based on concept presence
- Weighted criteria enable partial credit
- `required` flag allows hard constraints (must mention Plasmodium)

**Trade-off**: Requires human judgment to design rubrics. This is acceptable — the pipeline is tooling for humans, not a replacement for expert curation.

### 4. Generator Abstraction

**Decision**: Abstract generators behind `BaseGenerator` with a `generate()` method.

**Rationale**:
- Different sources (manual, CSV, synthetic) have fundamentally different inputs
- New generators can be added without modifying existing code
- `generate_dataset()` method provides a consistent interface
- Registry pattern allows dynamic generator selection

**Trade-off**: Slightly more boilerplate for simple generators. The ManualGenerator example shows this is minimal.

### 5. Provenance as First-Class Concept

**Decision**: Every item must have a `source` object with `type` and optional provenance fields.

**Rationale**:
- Auditability: know where every evaluation item came from
- Reproducibility: can trace back to original documents
- Compliance: some competitions require source attribution
- Future-proofing: `type` field allows new source types without breaking changes

---

## Rejected Alternatives

### Using lm-evaluation-harness Directly

**Why rejected**: ADTC has specific requirements (rubric scoring, domain-agnostic design, provenance tracking) that don't align with lm-eval-harness's built-in tasks. This pipeline is complementary — it generates the evaluation items that lm-eval-harness could consume.

### Database Backend

**Why rejected**: JSON files are sufficient for the expected dataset sizes (<10K items). A database adds operational complexity (hosting, backups, migrations) without benefit at this scale. Can be added later if needed.

### REST API

**Why rejected**: The pipeline is a CLI tool and library, not a service. A REST API would add deployment complexity. The `validate_dataset` and `generate_stats` scripts provide a clean CLI interface.

---

## Trade-offs

| Decision | Pro | Con |
|----------|-----|-----|
| JSON files over database | Simple, portable, version-controllable | No concurrent writes, no indexing |
| Immutable dataclasses | Safe, hashable | More verbose for updates |
| Rubrics over exact match | Flexible, handles LLM variation | Requires human rubric design |
| Python-only (no JS) | Faster development, type safety | Can't consume from JS without conversion |
| No LLM integration yet | Keeps scope manageable | SyntheticGenerator is a placeholder |

---

## Assumptions

1. **Dataset size**: <10K items per dataset. JSON files are fine at this scale.
2. **Single-writer**: No concurrent modification of the same dataset file.
3. **Domain-agnostic**: The pipeline does not assume any specific evaluation domain.
4. **Human-in-the-loop**: Generators produce drafts; humans curate and refine.
5. ** rubric design**: Humans will design rubrics; the pipeline doesn't auto-generate them.

---

## Known Limitations

1. **No automatic scoring**: Rubrics are consumed by external evaluators, not scored by this pipeline.
2. **No dataset diff**: Version comparison is manual (stretch goal).
3. **No YAML/HTML**: Only JSON input/output (stretch goals).
4. **No concurrent access**: Multiple processes writing the same file could corrupt it.
5. **SyntheticGenerator is a placeholder**: No actual LLM integration.

---

## Future Improvements

### Short-term (next sprint)
- Add dataset diff tool for version comparison
- Add YAML input support
- Add HTML report generation

### Medium-term
- Integrate LLM-powered synthetic generation
- Add automatic scoring against rubrics
- Add category coverage visualization
- Add dataset merging/splitting tools

### Long-term
- REST API for remote dataset management
- Database backend for large-scale datasets
- Integration with lm-evaluation-harness
- Multi-language support (currently English only)
- Statistical significance testing for dataset quality

---

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `schema.json` | ~120 | JSON Schema for evaluation items |
| `models.py` | ~130 | Data models (EvalItem, EvalDataset, etc.) |
| `validate.py` | ~150 | Validation engine |
| `stats.py` | ~130 | Dataset statistics |
| `generators/__init__.py` | ~120 | Generator base class + implementations |
| `scripts/validate_dataset.py` | ~40 | CLI: validate datasets |
| `scripts/generate_stats.py` | ~35 | CLI: compute statistics |
| `README.md` | ~200 | Documentation |
| `examples/*.json` | ~250 | Example datasets (3 domains) |

Total: ~1,175 lines of implementation + documentation.
