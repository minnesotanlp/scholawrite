# Architecture Decisions

This document records key architectural decisions made during the codebase refactoring to eliminate duplication while preserving intentional design choices.

## Scope

This refactoring applies ONLY to `src/scholawrite/` (our augmentation framework). The following directories are **external research code from minnesotanlp** and were intentionally NOT modified:

- `gpt4o/` - GPT-4o classification/generation experiments
- `scholawrite_finetune/` - LLaMA and BERT fine-tuning code
- `meta_inference/` - Meta instruction inference code
- `analysis/` - Original dataset analysis scripts

## Decision 1: Consolidated Label Parsing

**Problem**: `process_label()` was duplicated across 6 files in the external directories.

**Decision**: Created `src/scholawrite/labels.py` with:
- `WRITING_INTENTIONS`: Canonical 15-label taxonomy constant
- `parse_label()`: Unified function to normalize LLM outputs to valid labels
- `is_valid_label()`: Validation helper

**Rationale**: The label taxonomy is a core domain concept. Having a single source of truth prevents drift and makes the taxonomy explicit.

**Usage**:
```python
from scholawrite.labels import parse_label, WRITING_INTENTIONS

# Normalize verbose LLM output
label = parse_label("The intention is Clarity because...")  # Returns "Clarity"

# Handle invalid output
label = parse_label("gibberish", fallback="Unknown")  # Returns "Unknown"
```

## Decision 2: Consolidated Classification Metrics

**Problem**: `calculate_metrics()` was duplicated across 4+ files in the analysis/finetune directories.

**Decision**: Added `compute_classification_metrics()` to `src/scholawrite/metrics.py`.

**Rationale**: `metrics.py` already contained causal signature metrics. Classification metrics are a natural fit. The function computes accuracy, macro F1, micro F1, and per-class metrics without side effects (no printing, no file I/O).

**Usage**:
```python
from scholawrite.metrics import compute_classification_metrics

result = compute_classification_metrics(y_true, y_pred, verbose=False)
# Returns: {"accuracy": 0.85, "macro_f1": 0.82, "micro_f1": 0.85, "per_class": {...}}
```

## Decision 3: Renamed Placeholder Generation

**Problem**: `generate_placeholder_text()` name didn't clarify its purpose vs. LLM-powered generation.

**Decision**: Renamed to `generate_deterministic_placeholder()` with deprecated alias for backwards compatibility.

**Rationale**: The name now explicitly indicates:
1. Output is **deterministic** (same seed = same output)
2. It generates **placeholder** content, not production-quality text
3. Distinct from `agentic.py`'s LLM-powered generation

**Two Generation Paths**:

| Path | Function | Use Case |
|------|----------|----------|
| Deterministic | `injection.generate_deterministic_placeholder()` | Tests, fallbacks, development |
| LLM-Powered | `agentic.run_causal_agentic_loop()` | Production augmented builds |

**Backwards Compatibility**:
```python
# Old code still works (deprecated alias)
from scholawrite.injection import generate_placeholder_text

# New preferred import
from scholawrite.injection import generate_deterministic_placeholder
```

## Decision 4: Module Responsibility Boundaries

Each module has a clear single responsibility documented in its module docstring:

| Module | Responsibility |
|--------|---------------|
| `text.py` | Text manipulation (normalization, hashing, validation) |
| `labels.py` | Label parsing and taxonomy management |
| `metrics.py` | Causal signatures and classification metrics |
| `injection.py` | Injection point detection and placeholder generation |
| `agentic.py` | LLM-powered generation orchestration |

**Cross-cutting concerns**:
- `has_prompt_leakage()` exists in both `text.py` and `injection.py`
  - `text.py`: Comprehensive multi-layer detection for general use
  - `injection.py`: Simple pattern check for injection processing
  - Documented in `tests/test_architecture.py` as intentional

## Decision 5: Architecture Tests

Added `tests/test_architecture.py` with:
1. **Duplicate function detection**: Fails if same function is defined in multiple modules
2. **Module responsibility validation**: Ensures key modules have docstrings
3. **Label module tests**: Validates `parse_label()` behavior
4. **Metrics module tests**: Validates `compute_classification_metrics()` behavior
5. **Injection module tests**: Validates placeholder generation

Run architecture tests:
```bash
uv run python -m pytest tests/test_architecture.py -v
```

## Future Considerations

1. **Consolidate `has_prompt_leakage`**: Could merge into single location with configurable strictness
2. **External code migration**: If minnesotanlp code needs our shared utilities, add `scholawrite` as dependency
3. **Type annotations**: Consider adding stricter typing to shared modules

## Validation

After refactoring, verify:
```bash
# All architecture tests pass
uv run python -m pytest tests/test_architecture.py -v

# No duplicate functions (except allowed)
grep -r "^def process_label" src/scholawrite/  # Should find nothing
grep -r "^def calculate_metrics" src/scholawrite/  # Should find only metrics.py

# Full test suite passes
uv run python -m pytest tests/ -v
```
