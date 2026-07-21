# ADTC Benchmark Suite Framework

Modular benchmarking platform for LLM evaluation across multiple independent domains.

Built for the [Africa Deep Tech Challenge (ADTC) 2026](https://africatechchallenge.org).

---

## Quick Start

```bash
# List available suites
python -m benchmarks.framework.cli list

# Describe a suite
python -m benchmarks.framework.cli describe coding

# Validate a suite
python -m benchmarks.framework.cli validate coding

# Evaluate all suites
python -m benchmarks.framework.cli evaluate --all --model "my-model"

# Coverage analysis
python -m benchmarks.framework.cli coverage
```

---

## Architecture

```
benchmarks/
├── framework/                 # Core framework
│   ├── models.py              # Data models (EvalItem, SuiteMetadata, BenchmarkRun)
│   ├── registry.py            # Auto-discovery of suites
│   ├── loader.py              # Loads datasets from suite directories
│   ├── validator.py           # Validates datasets against schema
│   ├── scorer.py              # Scores model outputs against rubrics
│   ├── reporter.py            # Generates reports (terminal, JSON, markdown)
│   ├── engine.py              # Unified evaluation engine
│   ├── coverage.py            # Coverage analysis
│   ├── results.py             # Historical results storage
│   └── cli.py                 # CLI entry point
├── suites/                    # Benchmark suites (plugins)
│   ├── reasoning/v1/
│   ├── coding/v1/
│   ├── agriculture/v1/
│   ├── health/v1/
│   └── africa/v1/
├── templates/
│   └── suite/                 # Starter template for new suites
├── eval/                      # Legacy evaluation pipeline (backwards compatible)
├── README.md                  # This file
└── ENGINEERING_REPORT.md      # Design decisions and trade-offs
```

---

## How Suites Work

Each suite is a directory under `suites/<id>/v<version>/` containing:

- `suite.json` — metadata (id, name, version, categories, languages, maintainers)
- `dataset.json` — evaluation items (using the eval schema)
- `README.md` — suite documentation

The framework **automatically discovers** suites by scanning this directory structure. No registration required.

### Adding a New Suite

1. Copy `templates/suite/` to `suites/<your-id>/v1/`
2. Edit `suite.json` with your metadata
3. Add items to `dataset.json`
4. Validate: `python -m benchmarks.framework.cli validate <your-id>`

That's it. The framework discovers and loads it automatically.

---

## Versioning

Each suite supports multiple versions. Historical benchmark reports remain reproducible:

```
suites/
    coding/
        v1/          # Version 1.0.0
        v2/          # Version 2.0.0 (when ready)
```

Results are stored per-version and never overwrite history:

```
results/
    coding/
        v1/
            abc123.json     # Run from 2026-07-21
            def456.json     # Run from 2026-07-22
```

---

## Evaluation Engine

```bash
# Single suite
python -m benchmarks.framework.cli evaluate coding --model "qwen2.5-7b"

# Multiple suites
python -m benchmarks.framework.cli evaluate coding reasoning --model "my-model"

# All suites
python -m benchmarks.framework.cli evaluate --all --model "my-model"

# JSON output
python -m benchmarks.framework.cli evaluate coding --format json --output results.json

# Markdown output
python -m benchmarks.framework.cli evaluate coding --format markdown --output report.md
```

---

## Scoring

Scoring uses rubric-based evaluation. Each item has weighted criteria:

```json
{
  "criterion": "Mentions Plasmodium parasite",
  "weight": 0.3,
  "required": true
}
```

- `weight`: 0-1, all weights sum to 1.0
- `required`: must pass to receive any credit

The scorer evaluates each criterion independently and produces:
- Per-item scores (weighted sum)
- Per-category averages
- Overall suite score
- Pass/fail status

---

## Coverage Analysis

```bash
# Full coverage report
python -m benchmarks.framework.cli coverage

# Specific suites
python -m benchmarks.framework.cli coverage coding agriculture
```

Reports include:
- Category distribution
- Difficulty distribution
- Language coverage
- Duplicate detection
- Uncovered categories
- Average question/answer lengths

---

## Historical Results

```bash
# Show history for a suite
python -m benchmarks.framework.cli history coding v1
```

Each evaluation run saves results with:
- Run ID
- Timestamp
- Model name
- Scores
- Metadata

Results are never overwritten. Comparison between runs is supported.

---

## Extension Points

The framework is designed for extensibility:

| Component | How to Extend |
|-----------|---------------|
| **New suites** | Add `suites/<id>/v1/` directory |
| **New reporters** | Subclass `BaseReporter` in `reporter.py` |
| **New scorers** | Subclass `Scorer` in `scorer.py` |
| **New source types** | Add to `SourceType` enum in `models.py` |
| **New difficulty levels** | Add to `Difficulty` enum in `models.py` |

### Future Capabilities (Architecture-Ready)

- Multimodal benchmarks (images, documents)
- Tool-use evaluation
- Function calling assessment
- Speech evaluation
- Agentic workflow testing
- RAG evaluation

The `metadata` field on items and the `EvalItem` schema support these without breaking changes.

---

## Design Principles

1. **Plugin architecture** — suites are discovered, not hardcoded
2. **Versioned everything** — suites, results, schema versions
3. **Never overwrite** — historical data is immutable
4. **Domain-agnostic** — framework knows nothing about specific evaluation domains
5. **Backwards compatible** — existing `eval/` code continues to work

---

## See Also

- [ENGINEERING_REPORT.md](ENGINEERING_REPORT.md) — Detailed design decisions
- [eval/README.md](eval/README.md) — Legacy evaluation pipeline
- [templates/suite/](templates/suite/) — Starter template for new suites
