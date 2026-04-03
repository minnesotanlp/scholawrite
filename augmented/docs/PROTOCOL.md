# Augmentation Protocol

## 1) Purpose
Create a reproducible, public benchmark for **process‑integrity analysis** in revision‑tracked scholarly writing by inserting externally generated content into ScholaWrite revisions and annotating insertion boundaries, trajectories, and ambiguity. This protocol does **not** label origin (human vs AI) and is bound by the terminology contract in `docs/TERMINOLOGY.md`.

## 2) Scope and Constraints
- Preserve original ScholaWrite revision order and content exactly.
- All modifications are **additive** and fully annotated.
- No binary “AI vs human” labels are created.
- All stochastic steps are seeded and recorded in the run manifest.
- All release terms in `docs/ATTRIBUTION_AND_LICENSE.md` are binding.

## 3) Inputs
- Seed dataset: ScholaWrite revisions (normalized via `scripts/ingest_seed.py`).
- Local seed snapshot: `data/seed/raw/hf_snapshot` (Hugging Face download).
- Injection generators: externally generated spans with recorded generator metadata.

## 4) Outputs (Canonical Artifacts)
- `data/augmented/documents.jsonl`: augmented revisions with metadata.
- `data/augmented/annotations.jsonl`: span‑level annotations.
- `data/augmented/stats.json`: dataset statistics.
- `data/augmented/checksums.txt`: checksums for all artifacts.
- `data/augmented/failures.jsonl`: rejected cases with reasons.
- `data/augmented/manifest.json`: run metadata + artifact list.
- `data/augmented/run_manifest.json`: seeds, code version, checksums.

## 5) Injection Levels (Definition)
Use the fixed level taxonomy (see `docs/LABEL_TAXONOMY.md` and `docs/INJECTION_LEVELS.md` for full definitions):
- **Naive**: topic‑agnostic or loosely related insertions. No document context provided to generator.
- **Topical**: same domain but context‑agnostic insertions. Domain/topic provided, not local context.
- **Contextual**: locally coherent insertions aligned to nearby discourse. Full local context provided.

Each injection records: `injection_level`, `generator_class`, `prompt_hash`, `rng_seed`.

See `docs/INJECTION_LEVELS.md` for detailed level semantics, generator requirements, and relationship to baselines.

## 6) Trajectory Types (Boundary Erosion)
Defined in `docs/TRAJECTORIES.md`:
- **Cold**: inserted once, no subsequent edits.
- **Warm**: inserted then lightly edited.
- **Assimilated**: inserted then revised across multiple revisions.

Trajectories must emit an **ambiguity flag** when boundaries erode.

## 7) Annotation Schema (Span‑Level)
Each annotation record must include:
- `doc_id`, `revision_id`, `injection_id`
- `span_start_char`, `span_end_char`
- `span_start_sentence`, `span_end_sentence`
- `injection_level`
- `trajectory_state` (cold/warm/assimilated)
- `ambiguity_flag` (none/low/medium/high)
- `generator_class`, `prompt_hash`, `rng_seed`
- `provenance_hash` (seed revision hash)

Offsets are computed **after** normalization using `src/scholawrite/text.py`.

## 8) Augmentation Pipeline (Deterministic)
1) Normalize seed data (`scripts/ingest_seed.py`).
2) Generate raw injections (`scripts/generate_injections.py`).
3) Apply trajectories and insertions (`scripts/build_augmented_dataset.py`).
4) Run PII scan and redaction checks (see Section 11).
5) Validate annotations (`scripts/validate_annotations.py`).
6) Record checksums and manifests (`scripts/hash_artifacts.py`).
7) Record failures (`scripts/record_failures.py`).

## 9) Validation Rules
- Offsets must map to exact text spans in normalized revisions.
- No overlapping spans within a single revision.
- Ambiguity flags required for warm/assimilated trajectories.
- Labels must be in `docs/LABEL_TAXONOMY.md`.
- Trajectory states and ambiguity flags are validated using causal signature analysis
  (see `validate_earned_ambiguity()` in `src/scholawrite/annotations.py`).

Validation is enforced by `scripts/validate_annotations.py` and `scripts/lint_data.py`.

## 10) Failure Handling
Any failed record is written to `data/augmented/failures.jsonl` with:
- `doc_id`, `revision_id`, `reason`, and pipeline stage.
Failures are not discarded or overwritten.

## 11) Privacy and Safety
- No personally identifying information is introduced by generation.
- Generated content is filtered for disallowed content before inclusion.
- The dataset is intended for research on process integrity, not enforcement.
- A PII scan must be run on all generated spans and outputs prior to release.
- Any potential reverse‑identification risk is treated as a release blocker.

## 11.1) PII Scan Output Schema
The PII scan must emit a JSONL report with one record per finding:
- `record_id` (doc_id or revision_id)
- `field` (e.g., text, metadata)
- `span_start`, `span_end`
- `snippet` (redacted context)
- `rule_id` (which detector fired)
- `severity` (low/medium/high)
- `action` (block/review)
- The dataset must comply with the ScholaWrite terms (no reverse identification; no disclosure enabling identification).

## 12) Attribution and Licensing
- Derived from ScholaWrite; see `docs/ATTRIBUTION_AND_LICENSE.md`.
- Release must mirror or comply with the original dataset license.

## 13) Reproducibility
- All stochastic steps are seeded.
- `data/augmented/run_manifest.json` records seeds, code version, and checksums.
- Rebuild steps are documented in `docs/REPRODUCIBILITY.md`.

## 14) Threshold Reference
All numerical thresholds used in causal signature validation, anomaly detection,
trajectory classification, and embodied simulation are documented with their
justifications in `docs/THRESHOLDS.md`. Key categories include:

- **Causal Coupling Thresholds**: Minimum Pearson correlation values for trajectory states
- **Locality Thresholds**: Token distance bounds for human repair patterns (1.0-3.5)
- **Edit Classification**: Substantial edit ratio (>= 20% token change)
- **Detection Thresholds**: NCD (0.45), Jaccard similarity (< 0.30 for anomaly)
- **Embodied Simulation**: Glucose depletion, fatigue, syntactic complexity parameters

When modifying any threshold value, update both the code constant and the
corresponding entry in `docs/THRESHOLDS.md`.
