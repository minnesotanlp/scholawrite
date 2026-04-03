# ScholaWrite-Augmented: Release Notes

## Overview

ScholaWrite-Augmented is a revision-tracked scholarly writing dataset with annotated external insertion events, designed for **process-integrity research**. It augments the ScholaWrite seed dataset with synthetic injections at multiple sophistication levels, models boundary erosion over revision trajectories, and provides span-level annotations with explicit ambiguity flags.

This dataset does **not** label origin (human vs AI). See `docs/TERMINOLOGY.md` for the binding terminology contract.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/writerslogic/scholawrite-augmented.git
cd scholawrite-augmented

# Install dependencies
uv sync

# Verify installation
uv run python scripts/smoke_test.py
```

### Loading the Dataset

```python
import json

# Load augmented documents
with open("data/augmented/documents.jsonl") as f:
    documents = [json.loads(line) for line in f]

# Load span-level annotations
with open("data/augmented/annotations.jsonl") as f:
    annotations = [json.loads(line) for line in f]

# Load process-anomaly negative controls
with open("data/augmented/anomalies.jsonl") as f:
    anomalies = [json.loads(line) for line in f]
```

### Using the Library

```python
from scholawrite.io import load_seed
from scholawrite.schema import AugmentedDocument
from scholawrite.annotations import validate_annotations
from scholawrite.metrics import compute_span_iou, compute_f1

# Load and inspect seed data
seed_docs = load_seed("data/seed/normalized/")

# Validate annotations
errors = validate_annotations("data/augmented/annotations.jsonl")
assert len(errors) == 0, f"Validation errors: {errors}"
```

### Running Baselines

```bash
# Run all baselines
uv run python scripts/run_baselines.py

# Run harm analysis
uv run python scripts/run_harm.py

# Results are written to results/baselines/ and results/harm/
```

### Full Pipeline Rebuild

```bash
# Run the complete pipeline (deterministic)
bash scripts/run_all.sh

# Verify checksums match
diff data/augmented/checksums.txt expected_checksums.txt
```

## Dataset Structure

```
data/
├── seed/
│   ├── raw/hf_scholawrite/      # Original HF download
│   └── normalized/               # Canonical schema format
├── augmented/
│   ├── documents.jsonl           # Augmented revisions
│   ├── annotations.jsonl         # Span-level annotations
│   ├── anomalies.jsonl           # Process-anomaly controls
│   ├── failures.jsonl            # Rejected cases with reasons
│   ├── stats.json                # Dataset statistics
│   ├── checksums.txt             # Artifact checksums
│   ├── manifest.json             # Artifact list
│   ├── run_manifest.json         # Seeds, versions, checksums
│   └── env.json                  # Build environment
├── splits/
│   └── splits.json               # Deterministic train/val/test
└── injections/
    └── raw/                      # Pre-insertion injection candidates
```

## Key Concepts

| Concept | Description | Reference |
|---------|-------------|-----------|
| Injection Level | Sophistication of insertion (naive/topical/contextual) | `docs/INJECTION_LEVELS.md` |
| Trajectory | Boundary erosion over revisions (cold/warm/assimilated) | `docs/TRAJECTORIES.md` |
| Ambiguity Flag | Confidence in boundary determination (none/low/medium/high) | `docs/PROTOCOL.md` |
| Process Anomaly | Non-injective revision irregularity | `docs/LABEL_TAXONOMY.md` |

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/PROTOCOL.md` | Augmentation protocol and pipeline steps |
| `docs/DATA_CARD.md` | Dataset card with composition and intended use |
| `docs/TERMINOLOGY.md` | Binding terminology contract |
| `docs/LABEL_TAXONOMY.md` | Label namespaces and disjointness rules |
| `docs/TRAJECTORIES.md` | Trajectory definitions and erosion model |
| `docs/INJECTION_LEVELS.md` | Injection sophistication level definitions |
| `docs/ETHICS.md` | Ethical considerations and misuse risks |
| `docs/REPRODUCIBILITY.md` | Full rebuild instructions |
| `docs/ATTRIBUTION_AND_LICENSE.md` | Attribution, permissions, and license terms |
| `docs/CI.md` | CI pipeline configuration |

## Citation

When using this dataset, please cite both the original ScholaWrite paper and this augmented release:

```bibtex
@inproceedings{wang2025scholawrite,
  title     = {ScholaWrite: A Writing Process Study Dataset for Scholarly Writing},
  author    = {Wang, Seulgi and Lee, Yoonna and Volkov, Ilya and Chau, Tuyen Luan and Kang, Dongyeop},
  booktitle = {Proceedings of the Joint Conference of the 59th Annual Meeting of the Association for Computational Linguistics},
  year      = {2025}
}

@article{condrey2026scholawrite-augmented,
  title   = {Process Integrity Without Origin Labels: Cognitive Simulation for Hybrid Writing Verification},
  author  = {Condrey, David},
  journal = {ACL Findings},
  year    = {2026},
  url     = {https://github.com/writerslogic/scholawrite-augmented}
}
```

## Intended Use and Non-Use

**Intended**: research on process integrity, revision-trace analysis, benchmarking discontinuity methods.

**Not intended**: punitive enforcement, sole authorship determination, high-stakes decisions without human review, reverse identification of authors or papers.

See `docs/ETHICS.md` for full ethical considerations.

## Terms

This dataset inherits the ScholaWrite terms. See `docs/ATTRIBUTION_AND_LICENSE.md` for binding terms including restrictions on reverse identification and PII.
