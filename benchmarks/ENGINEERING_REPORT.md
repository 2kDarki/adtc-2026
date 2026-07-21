# Engineering Report: Benchmark Suite Framework

## Overview

This report documents the architectural decisions, trade-offs, and implementation details of the modular benchmark suite framework built for ADTC 2026.

---

## Architectural Decisions

### 1. Plugin-Based Suite Discovery

**Decision**: Suites are discovered by scanning the `suites/` directory for `suite.json` files, not registered in code.

**Rationale**:
- Adding a new suite requires zero framework changes
- Contributors only need to create a directory with the right structure
- No merge conflicts from centralized registration
- Community contributions are isolated to their own directories

**Rejected alternatives**:
- Central registry file: Would cause merge conflicts, adds maintenance burden
- Python entry points: Overly complex for this use case
- Database-backed registry: Adds operational complexity

### 2. Directory-Based Versioning

**Decision**: Each suite version is a separate directory (`v1/`, `v2/`), not metadata in a single file.

**Rationale**:
- Historical reports remain reproducible — the `v1/` directory never changes
- Easy to compare versions side-by-side
- Git history naturally tracks version changes
- No risk of accidental overwrites

**Trade-off**: More disk space (full copy per version). Acceptable for evaluation datasets (<1MB each).

### 3. Immutable Data Models

**Decision**: Use `frozen=True` dataclasses for all core models.

**Rationale**:
- Prevents accidental mutation of evaluation items
- Items are hashable for set operations (deduplication)
- Clear contract: once created, an item doesn't change
- Supports concurrent reads safely

**Trade-off**: Requires new instances for updates. This is intentional — versioning handles changes.

### 4. Rubric-Based Scoring

**Decision**: Use weighted rubrics instead of exact matching or LLM judging.

**Rationale**:
- LLM outputs vary in wording while being semantically correct
- Rubrics allow partial credit based on concept presence
- Weighted criteria enable nuanced evaluation
- `required` flag allows hard constraints

**Trade-off**: Requires human rubric design. This is a feature, not a bug — expert curation improves quality.

### 5. Separate Framework and Suites

**Decision**: Core framework in `framework/`, suites in `suites/`, legacy eval in `eval/`.

**Rationale**:
- Clear separation of concerns
- Framework can evolve independently of suites
- Existing `eval/` code continues to work (backwards compatible)
- Suites can be contributed without understanding framework internals

### 6. Results as JSON Files

**Decision**: Store results as JSON files in `results/<suite>/<version>/`, not a database.

**Rationale**:
- Simple, portable, version-controllable
- No operational complexity (hosting, backups, migrations)
- Git-friendly for team collaboration
- Sufficient for expected scale (<10K runs per suite)

**Trade-off**: No concurrent writes, no SQL queries. Can add database later if needed.

---

## Rejected Alternatives

### Centralized Suite Registry

**Why rejected**: Would require all contributors to modify a shared file, causing merge conflicts and review bottlenecks. Directory-based discovery is more scalable.

### ORM/Database Backend

**Why rejected**: JSON files are sufficient for the expected dataset and result sizes. A database adds deployment complexity without benefit at this scale.

### LLM-as-Judge Integration

**Why rejected**: This ticket explicitly excludes LLM integration. The scorer is a placeholder that can be extended later. Focus is on infrastructure, not evaluation logic.

### REST API

**Why rejected**: The framework is a CLI tool and library, not a service. A REST API would add deployment complexity. Can be added later as a thin wrapper.

---

## Trade-offs

| Decision | Pro | Con |
|----------|-----|-----|
| Directory-based discovery | Zero-config, community-friendly | Requires consistent directory structure |
| Immutable dataclasses | Safe, hashable, concurrent-safe | More verbose for updates |
| JSON file storage | Simple, portable, git-friendly | No concurrent writes, no indexing |
| Rubric-based scoring | Flexible, handles LLM variation | Requires human rubric design |
| Separate framework/suites | Clean separation, backwards compat | Slightly more complex directory structure |
| No database | Zero operational complexity | Limited query capabilities |

---

## Scalability Analysis

**Dataset size**: Each suite has <100 items. JSON files handle this efficiently (<1ms load time).

**Suite count**: Auto-discovery scans directories. With 100 suites, scan takes <50ms. Not a bottleneck.

**Result storage**: Each run saves ~10KB JSON. 10,000 runs = ~100MB. Easily manageable.

**Concurrent access**: Single-writer assumption is acceptable for CLI tool. Multiple terminals can read simultaneously.

---

## Compatibility Considerations

**Backwards compatible**:
- Existing `eval/` code works unchanged
- `EvalItem` schema is shared between `eval/` and `framework/`
- CLI commands are additive, not replacing

**Migration path**:
- Existing `benchmarks/eval/examples/*.json` can be moved into suite directories
- No data transformation required
- Schema is identical

---

## Maintenance Strategy

**Framework changes**: Rare after initial implementation. Core models are stable. Extensions happen at the edges (new reporters, new scorers).

**Suite maintenance**: Each suite is maintained by its owners. Framework changes don't require suite updates (backwards compatible schema).

**Versioning**: Framework uses semantic versioning. Breaking changes increment major version. Suites version independently.

---

## Future Roadmap

### Short-term (next sprint)
- [ ] Add dataset diff tool for version comparison
- [ ] Add YAML input support
- [ ] Add HTML report generation
- [ ] Add suite health checks (missing categories, low item counts)

### Medium-term
- [ ] Integrate LLM-powered scoring
- [ ] Add concurrent evaluation support
- [ ] Add suite dependency resolution
- [ ] Add cross-suite comparison reports

### Long-term
- [ ] REST API for remote evaluation
- [ ] Database backend for large-scale results
- [ ] Integration with lm-evaluation-harness
- [ ] Multimodal benchmark support
- [ ] Agentic workflow evaluation

---

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `framework/__init__.py` | ~5 | Package init |
| `framework/models.py` | ~170 | Core data models |
| `framework/registry.py` | ~100 | Suite discovery |
| `framework/loader.py` | ~40 | Dataset loading |
| `framework/validator.py` | ~120 | Validation engine |
| `framework/scorer.py` | ~160 | Scoring engine |
| `framework/reporter.py` | ~150 | Report generation |
| `framework/engine.py` | ~140 | Unified evaluation engine |
| `framework/coverage.py` | ~130 | Coverage analysis |
| `framework/results.py` | ~90 | Historical results |
| `framework/cli.py` | ~90 | CLI entry point |
| `suites/*/v1/` | ~400 | 5 example suites |
| `templates/suite/` | ~50 | Contributor template |
| `README.md` | ~180 | Documentation |
| `ENGINEERING_REPORT.md` | ~250 | This report |

Total: ~2,075 lines of implementation + documentation.

---

## Conclusion

The framework achieves its goals of being modular, extensible, and production-quality:

- **No suite requires framework changes** — discovery is automatic
- **Multiple versions coexist** — directory-based versioning
- **Historical results preserved** — never overwrite
- **Unified interface** — single CLI for all operations
- **Extensible** — new reporters, scorers, suites added without core changes

The architecture is suitable for long-term evolution because it separates stable core (models, schema) from evolving edges (suites, reporters, scorers).
