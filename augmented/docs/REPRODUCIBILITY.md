# Reproducibility

## Objective

The ScholaWrite-Augmented pipeline is designed to produce **bitwise-identical outputs** given the same inputs, environment, and RNG seeds. This document provides full rebuild instructions and explains the determinism guarantees.

## Prerequisites

- Python 3.11+
- `uv` package manager
- Access to the ScholaWrite seed dataset (`minnesotanlp/scholawrite` on Hugging Face)
- Sufficient disk space for seed + augmented artifacts

## Full Rebuild Instructions

### Step 1: Environment Setup

```bash
# Install dependencies
uv sync

# Capture environment metadata
uv run python scripts/env_capture.py
# Writes: data/augmented/env.json
```

### Step 2: Seed Data Ingestion

```bash
# Download seed data from Hugging Face (manual step)
# Place in: data/seed/raw/hf_scholawrite/

# Normalize seed data into canonical schema
uv run python scripts/ingest_seed.py
# Writes: data/seed/normalized/*.jsonl
```

### Step 3: Injection Generation

```bash
# Generate injection candidates (deterministic RNG)
uv run python scripts/generate_injections.py
# Writes: data/injections/raw/*.jsonl
```

### Step 4: Augmentation

```bash
# Build augmented dataset with trajectories and annotations
uv run python scripts/build_augmented_dataset.py
# Writes: data/augmented/documents.jsonl
#          data/augmented/annotations.jsonl
#          data/augmented/stats.json
```

### Step 5: Process Anomalies

```bash
# Generate process-anomaly negative controls
uv run python scripts/generate_anomalies.py
# Writes: data/augmented/anomalies.jsonl
```

### Step 6: Validation

```bash
# Validate annotations (offsets, non-overlap, ambiguity)
uv run python scripts/validate_annotations.py

# Full data lint including PII scan
uv run python scripts/lint_data.py --pii-scan
```

### Step 7: Checksums and Manifests

```bash
# Generate artifact checksums
uv run python scripts/hash_artifacts.py
# Writes: data/augmented/checksums.txt

# Record failures
uv run python scripts/record_failures.py
# Writes: data/augmented/failures.jsonl
```

### Step 8: Baselines and Harm Analysis

```bash
# Run baseline methods
uv run python scripts/run_baselines.py
# Writes: results/baselines/doc_level.json
#          results/baselines/span_level.json
#          results/baselines/summary.csv

# Run harm analysis
uv run python scripts/run_harm.py
# Writes: results/harm/summary.csv
#          results/harm/by_level.csv
```

### One-Command Rebuild

```bash
bash scripts/run_all.sh
```

This script executes all steps in dependency order and halts on first failure.

## Determinism Guarantees

### RNG Seeds
- All stochastic operations use explicitly recorded seeds.
- Seeds are stored in `data/augmented/run_manifest.json`.
- The manifest also records the code version (git SHA) and artifact checksums.

### Text Normalization
- All text processing uses `src/scholawrite/text.py` exclusively.
- Normalization is rule-based with no external model calls.
- Character offsets are computed post-normalization.

### ID Generation
- Document, revision, and injection IDs are deterministic hashes.
- ID logic is centralized in `src/scholawrite/ids.py`.
- IDs include a version prefix for future compatibility.

### Ordering
- Seed documents are sorted by timestamp then revision index.
- Injection candidates are processed in stable ID order.
- Output JSONL files preserve insertion order.

## Verification

After a rebuild, verify determinism:

```bash
# Compare checksums
uv run python scripts/hash_artifacts.py --verify

# Run full test suite
uv run python -m pytest tests/ -v

# Run smoke test
uv run python scripts/smoke_test.py
```

If checksums differ, check:
1. Python version matches `data/augmented/env.json`.
2. Package versions match (use `uv sync` with lockfile).
3. Seed data is identical (compare against expected hash).
4. No environment-dependent operations (locale, filesystem ordering).

## Run Manifest Schema

`data/augmented/run_manifest.json` contains:

```json
{
  "git_sha": "abc123...",
  "python_version": "3.11.x",
  "uv_version": "x.y.z",
  "rng_seeds": {
    "injection_generation": 42,
    "augmentation": 42,
    "anomaly_generation": 42,
    "splits": 42
  },
  "checksums": {
    "documents.jsonl": "sha256:...",
    "annotations.jsonl": "sha256:...",
    "anomalies.jsonl": "sha256:..."
  },
  "timestamp": "2026-01-24T00:00:00Z"
}
```

## Splits

Deterministic train/validation/test splits are stored in `data/splits/splits.json`. Splits are generated with a fixed seed and recorded in the run manifest. Split hashes are verified during CI.

## PII Scan

A PII scan must pass before any release:

```bash
uv run python scripts/pii_scan.py
# or
uv run python scripts/lint_data.py --pii-scan
```

Any findings block release. See `docs/PROTOCOL.md` Section 11 for the PII scan output schema.
