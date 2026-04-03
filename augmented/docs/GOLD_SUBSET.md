# Human-Verified Gold Subset + IAA

This project includes a **human-verified gold subset** for process-integrity evaluation.
The gold subset is a small, representative sample used to calibrate evaluation metrics
and report inter-annotator agreement (IAA).

## Scope
- Gold subset focuses on **process-level events** (external insertions, boundary erosion).
- It does **not** label authorship or origin (see `docs/TERMINOLOGY.md`).

## Annotation Units
Each unit corresponds to a single injection span in a specific revision.
Annotators label:
- `span_start_char`, `span_end_char` (best-effort boundary)
- `trajectory_state` (cold/warm/assimilated)
- `ambiguity_flag` (none/low/medium/high)

## File Format
Annotations are stored as JSONL with one record per span:
```json
{
  "doc_id": "doc_x",
  "revision_id": "rev_y",
  "injection_id": "inj_z",
  "span_start_char": 123,
  "span_end_char": 456,
  "trajectory_state": "warm",
  "ambiguity_flag": "low",
  "annotator_id": "annotator_a"
}
```

## Workflow
1) Sample candidate spans:
```bash
uv run python scripts/prepare_gold_subset.py \
  --input data/augmented/annotations.jsonl \
  --output data/gold/gold_candidates.jsonl \
  --size 200 \
  --seed 42
```
2) Distribute `gold_candidates.jsonl` to annotators.
3) Collect `gold_annotations.jsonl` from each annotator.
4) Compute IAA:
```bash
uv run python scripts/iaa_compute.py \
  --inputs data/gold/annotator_a.jsonl,data/gold/annotator_b.jsonl \
  --report data/gold/iaa_report.json
```

## IAA Metrics
We report:
- Cohen’s Kappa for `trajectory_state`
- Cohen’s Kappa for `ambiguity_flag`
- Mean span IoU for boundary agreement

## Release
Gold subset is released as a separate artifact:
- `data/gold/gold_candidates.jsonl`
- `data/gold/gold_annotations.jsonl`
- `data/gold/iaa_report.json`
