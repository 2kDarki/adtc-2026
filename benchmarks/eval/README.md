# Evaluation Dataset Pipeline

Reusable tooling for generating, validating, and managing evaluation datasets for LLM benchmarking across arbitrary domains.

Built for the [Africa Deep Tech Challenge (ADTC) 2026](https://africatechchallenge.org).

---

## Quick Start

```bash
# Validate a dataset
python -m benchmarks.eval.scripts.validate_dataset benchmarks/eval/examples/coding.json

# Compute statistics
python -m benchmarks.eval.scripts.generate_stats benchmarks/eval/examples/coding.json

# Use as a library
from benchmarks.eval.models import EvalDataset
from benchmarks.eval.validate import validate_dataset
from benchmarks.eval.stats import compute_stats

dataset = EvalDataset.from_dict(json.loads(open("dataset.json").read()))
report = validate_dataset(dataset)
stats = compute_stats(dataset)
```

---

## Directory Structure

```
benchmarks/eval/
├── README.md                 # This file
├── schema.json               # JSON Schema for evaluation items
├── __init__.py               # Package init
├── models.py                 # Data models (dataclasses)
├── validate.py               # Validation engine
├── stats.py                  # Dataset statistics
├── generators/               # Evaluation item generators
│   ├── __init__.py           # BaseGenerator + ManualGenerator, SyntheticGenerator, CSVGenerator
├── scripts/
│   ├── validate_dataset.py   # CLI: validate datasets
│   └── generate_stats.py     # CLI: compute statistics
├── templates/                # Templates for synthetic generation (future)
└── examples/                 # Example datasets from different domains
    ├── coding.json           # Coding assistant examples
    ├── health.json           # Healthcare assistant examples
    └── agriculture.json      # Agriculture assistant examples
```

---

## Schema

Each evaluation item conforms to `schema.json`. Key fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Globally unique ID (format: `<domain>-<category>-<seq>`) |
| `category` | string | yes | Top-level topic area |
| `subcategory` | string | no | Finer-grained classification |
| `difficulty` | enum | yes | `easy`, `medium`, `hard`, `expert` |
| `question` | string | yes | The prompt presented to the LLM |
| `expected_answer` | string | yes | Reference answer |
| `rubric` | array | yes | Weighted scoring criteria |
| `language` | string | yes | ISO 639-1 code |
| `source` | object | yes | Provenance metadata |
| `tags` | array | no | Free-form tags |
| `notes` | string | no | Internal maintainer notes |
| `metadata` | object | no | Extensible key-value store |
| `created_at` | datetime | yes | ISO 8601 creation timestamp |
| `version` | integer | no | Schema version (default: 1) |

### Rubric Format

Each rubric entry has:

```json
{
  "criterion": "Mentions Plasmodium parasite",
  "weight": 0.3,
  "required": true
}
```

- `weight`: 0-1, all weights should sum to 1.0
- `required`: if true, the answer MUST satisfy this criterion

### Source Provenance

The `source` field tracks where each item came from:

```json
{
  "type": "document",
  "document": "WHO Malaria Report 2025.pdf",
  "page": 12,
  "author": "World Health Organization",
  "publication_date": "2025-03-15"
}
```

Source types: `manual`, `document`, `synthetic`, `csv`, `web`

---

## Validation

The validator checks:

- Schema conformance (required fields, types)
- Duplicate IDs
- Duplicate questions (warning)
- Empty required fields
- Rubric integrity (non-empty, weights sum to ~1.0)
- Invalid difficulty values
- Category allowlist (optional)
- Source field consistency

```bash
# Basic validation
python -m benchmarks.eval.scripts.validate_dataset dataset.json

# With category allowlist
python -m benchmarks.eval.scripts.validate_dataset dataset.json --categories algorithms,debugging

# JSON output
python -m benchmarks.eval.scripts.validate_dataset dataset.json --json
```

---

## Statistics

```bash
# Terminal report
python -m benchmarks.eval.scripts.generate_stats dataset.json

# JSON output
python -m benchmarks.eval.scripts.generate_stats dataset.json --json
```

Reports include:
- Total items, categories, subcategories
- Difficulty and language distributions
- Duplicate detection
- Average question/answer lengths
- Tag frequency

---

## Generators

Generators produce evaluation items from various sources. All inherit from `BaseGenerator`.

| Generator | Source | Use Case |
|-----------|--------|----------|
| `ManualGenerator` | JSON file | Manually curated items |
| `SyntheticGenerator` | Templates | Template-based generation (LLM placeholder) |
| `CSVGenerator` | CSV file | Bulk import from spreadsheets |

### Adding a New Generator

```python
from benchmarks.eval.generators import BaseGenerator
from benchmarks.eval.models import EvalItem

class MyGenerator(BaseGenerator):
    name = "my_generator"
    description = "Generates items from my custom source"

    def generate(self, **kwargs) -> list[EvalItem]:
        # Your generation logic here
        return [...]
```

Register it in `generators/__init__.py`:

```python
GENERATORS["my_generator"] = MyGenerator
```

---

## Design Decisions

### Why JSON Schema?

JSON Schema provides machine-readable validation, IDE support, and compatibility with existing tooling. It's extensible without breaking changes via `additionalProperties: false` on nested objects.

### Why Rubrics Instead of Exact Matching?

LLM outputs vary in wording while being semantically correct. Rubrics allow fuzzy scoring based on whether key concepts are present, which is more robust than exact string matching.

### Why Immutable Dataclasses?

Evaluation items should not be mutated after creation. Immutability prevents accidental modification and makes items hashable for set operations (deduplication).

### Why Separate Generators?

Different evaluation sources (manual curation, CSV bulk import, synthetic generation) have fundamentally different inputs and logic. A generator interface keeps each source isolated and testable.

---

## Extensibility Points

1. **New generators**: Subclass `BaseGenerator`, implement `generate()`
2. **New source types**: Add values to `SourceType` enum in `models.py`
3. **New validation checks**: Add methods to `validate.py`
4. **New statistics**: Extend `DatasetStats` in `stats.py`
5. **Metadata**: Use the `metadata` field for domain-specific data without schema changes

---

## Known Limitations

- SyntheticGenerator is a placeholder (no actual LLM integration yet)
- No automatic scoring — rubrics are consumed by external evaluators
- No dataset versioning/diff tool (stretch goal)
- No YAML/HTML support (stretch goals)

---

## Future Improvements

- LLM-powered synthetic generation
- Automatic scoring against rubrics
- Dataset diff tool for version comparison
- YAML input support
- HTML report generation
- Category coverage visualization
- Integration with `lm-evaluation-harness`
