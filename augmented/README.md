# ScholaWrite-Augmented

Revision-level benchmarks for hybrid human-AI writing detection.

## Overview

This package provides tools for:
- Forensic detection of AI-generated content in academic writing
- Causal process simulation with embodied cognition models
- Injection point detection and contextual augmentation
- Baseline detection methods (compression, stylometric, etc.)

## Installation

```bash
cd augmented
uv pip install -e ".[dev]"
```

## Usage

Run from the `augmented/` directory:

```bash
# Run tests
uv run python -m pytest tests/ -v

# Build augmented dataset
uv run python scripts/build_augmented_dataset.py --help

# Run smoke test
uv run python scripts/smoke_test.py
```

## Project Structure

```
augmented/
├── scholawrite/     # Python package
├── scripts/         # CLI tools
├── tests/           # Test suite
├── configs/         # Configuration files
├── docs/            # Documentation
├── data/            # Data directory (gitignored)
├── results/         # Output directory
└── pyproject.toml   # Package configuration
```

## Documentation

See `docs/` for detailed documentation:
- `ARCHITECTURE_DECISIONS.md` - Design decisions
- `THRESHOLDS.md` - Threshold calibration
- `PROTOCOL.md` - Data generation protocol
