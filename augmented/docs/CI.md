# Continuous Integration

## Overview

CI enforces determinism, data integrity, and terminology compliance across the ScholaWrite-Augmented pipeline. All checks run on every push and pull request.

## Pipeline Stages

### 1) Environment Setup

```bash
uv sync
uv run python scripts/env_capture.py  # Record environment metadata
```

### 2) Lint and Validate

```bash
# Schema and offset validation
uv run python scripts/lint_data.py

# PII scan (blocks release if findings detected)
uv run python scripts/lint_data.py --pii-scan

# Annotation validation (offsets, non-overlap, ambiguity constraints)
uv run python scripts/validate_annotations.py
```

### 3) Unit Tests

```bash
uv run python -m pytest tests/ -v
```

Required test files:
- `tests/test_io.py` — seed ingestion and normalization
- `tests/test_schema.py` — schema validation and serialization
- `tests/test_time.py` — timestamp normalization and deltas
- `tests/test_injection.py` — injection determinism and metadata
- `tests/test_trajectories.py` — trajectory state transitions
- `tests/test_annotations.py` — offset validity and ambiguity constraints
- `tests/test_augment.py` — deterministic output hashes
- `tests/test_anomalies.py` — disjoint label validation
- `tests/test_metrics.py` — metric computation correctness
- `tests/test_harm.py` — harm summary integrity
- `tests/test_pii.py` — PII scan rules and output format
- `tests/test_smoke.py` — end-to-end subset validation

### 4) Smoke Test

```bash
uv run python scripts/smoke_test.py
```

Runs the full pipeline on a small fixture subset to verify end-to-end correctness without requiring the full seed dataset.

### 5) Checksum Verification

```bash
uv run python scripts/hash_artifacts.py --verify
```

Compares computed checksums against `data/augmented/checksums.txt` to detect nondeterminism.

## Failure Policy

- Any test failure blocks merge.
- Any PII finding blocks release.
- Checksum mismatch requires investigation (nondeterminism or environment drift).
- Lint errors (schema, offsets, labels) block merge.

## Local Reproduction

To run the full CI pipeline locally:

```bash
bash scripts/run_all.sh
```

This executes all stages in dependency order and halts on first failure.

## Environment Requirements

- Python 3.11+
- `uv` package manager
- No external API calls during CI (all generation is pre-computed)
- See `docs/REPRODUCIBILITY.md` for pinned dependency versions
