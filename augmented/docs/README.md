---
license: apache-2.0
task_categories:
  - text-classification
  - text-generation
language:
  - en
tags:
  - writing-process
  - revision-tracking
  - process-integrity
  - scholarly-writing
size_categories:
  - 100K<n<1M
source_datasets:
  - minnesotanlp/scholawrite
---

# ScholaWrite-Augmented

**Process Integrity Benchmarks for Revision-Tracked Scholarly Writing**

## Dataset Description

ScholaWrite-Augmented is a revision-tracked scholarly writing dataset with annotated external insertion events, designed for **process-integrity research**. It augments the [ScholaWrite](https://huggingface.co/datasets/minnesotanlp/scholawrite) seed dataset with synthetic injections at multiple sophistication levels, models boundary erosion over revision trajectories, and provides span-level annotations with explicit ambiguity flags.

**This dataset does NOT label origin (human vs AI).** Instead, it studies whether the observable revision process is consistent with iterative human authorship, or whether it exhibits evidence of process-inconsistent external insertion.

- **Repository:** [github.com/writerslogic/scholawrite-augmented](https://github.com/writerslogic/scholawrite-augmented)
- **Paper:** Process Integrity Without Origin Labels: Cognitive Simulation for Hybrid Writing Verification

## Dataset Summary

| Statistic | Value |
|-----------|-------|
| Documents | 5 |
| Total Revisions | 126,246 |
| Injections | 237 |
| Trajectory States | COLD (50%), WARM (33%), ASSIMILATED (16%) |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Injection Level** | Sophistication of insertion: naive (no context), topical (domain only), contextual (full local context) |
| **Trajectory State** | Boundary erosion over revisions: COLD (unedited), WARM (partial integration), ASSIMILATED (full integration) |
| **Ambiguity Flag** | Confidence in boundary determination: NONE, LOW, MEDIUM, HIGH |
| **Causal Signatures** | Process metrics: repair locality, resource coupling, biometric plausibility |

## Dataset Structure

```
data/
├── documents.jsonl      # Augmented revisions with metadata
├── annotations.jsonl    # Span-level insertion annotations
├── anomalies.jsonl      # Process-anomaly negative controls
└── stats.json           # Dataset statistics
```

### Data Fields

**documents.jsonl:**
- `doc_id`: Document identifier
- `revision_id`: Unique revision identifier
- `revision_index`: Sequential revision number
- `text`: Normalized revision text
- `timestamp`: Revision timestamp (if available)
- `provenance_hash`: Content hash for verification
- `before_text`: Text before this revision
- `writing_intention`: Expert-annotated writing intention (15 classes)

**annotations.jsonl:**
- `doc_id`, `revision_id`: Location identifiers
- `injection_id`: Unique injection identifier
- `span_start_char`, `span_end_char`: Character offsets
- `span_start_sentence`, `span_end_sentence`: Sentence offsets
- `injection_level`: naive | topical | contextual
- `trajectory_state`: COLD | WARM | ASSIMILATED
- `ambiguity_flag`: NONE | LOW | MEDIUM | HIGH
- `generator_class`: Generator type (weak/mid/strong)
- `causal_trace`: Full causal event trace

## Usage

### Loading the Dataset

```python
from datasets import load_dataset

dataset = load_dataset("Writerslogic/scholawrite-augmented")

# Access documents
for doc in dataset["train"]:
    print(doc["doc_id"], doc["text"][:100])
```

### Loading Raw Files

```python
import json

# Load augmented documents
with open("data/documents.jsonl") as f:
    documents = [json.loads(line) for line in f]

# Load span-level annotations
with open("data/annotations.jsonl") as f:
    annotations = [json.loads(line) for line in f]
```

## Intended Use

- Research on process integrity and revision-trace analysis
- Benchmarking methods that surface revision discontinuities
- Studying boundary erosion and ambiguity in hybrid writing
- Evaluating causal signatures for process verification

## Non-Use / Out-of-Scope

This dataset **MUST NOT** be used for:

- Punitive or automated enforcement decisions
- Sole determination of authorship or tool use
- High-stakes decisions without human review
- Reverse identification of authors, papers, or institutions
- Surveillance of writers without consent
- Any framing as "AI detection"

## Ethical Considerations

This dataset is designed to study **process integrity**, not to enable surveillance or enforcement. Key principles:

1. **No origin labels**: We do not label text as "human" or "AI"
2. **Process over product**: We assess revision traces, not final text properties
3. **Ambiguity is valid**: Indeterminate cases are expected, not errors
4. **Assistance is compatible**: Legitimate tool use with iterative integration is process-consistent

See [ETHICS.md](https://github.com/writerslogic/scholawrite-augmented/blob/main/docs/ETHICS.md) for full ethical considerations.

## Terms and Attribution

This dataset is derived from **ScholaWrite** (MinnesotaNLP). Per the seed dataset terms:

- No reverse identification of authors, papers, or institutions
- No disclosure enabling identification
- No PII introduction
- Attribution to ScholaWrite required

## Citation

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

## License

Apache-2.0 (inherited from ScholaWrite), with additional terms from the seed dataset regarding reverse identification and permitted use.
