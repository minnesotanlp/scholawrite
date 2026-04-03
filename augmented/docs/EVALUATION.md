# Evaluation Suite (Process-Integrity)

This evaluation suite measures **process integrity signals**, not origin or authorship.
All metrics and tasks must comply with `docs/TERMINOLOGY.md`.

## Tasks
1) **Span Boundary Localization**
   - Input: revision text + revision metadata.
   - Output: predicted spans.
   - Metric: Span IoU, token-level F1.

2) **Revision Discontinuity Detection**
   - Input: revision history only.
   - Output: discontinuity score per revision.
   - Metric: AUC, F1 (thresholded).

3) **Trajectory Prediction**
   - Input: injection span + revision sequence.
   - Output: cold / warm / assimilated.
   - Metric: accuracy, macro-F1.

## Required Outputs
Prediction JSONL schema:
```json
{
  "doc_id": "doc_x",
  "revision_id": "rev_y",
  "injection_id": "inj_z",
  "predicted_spans": [[10, 50], [80, 95]],
  "discontinuity_score": 0.73,
  "trajectory_state": "warm"
}
```

## Gold Data
Gold annotations come from `data/gold/gold_annotations.jsonl` (see `docs/GOLD_SUBSET.md`).

## Reporting
Report all metrics with:
- mean + 95% CI (bootstrap where possible)
- disaggregated by injection level and model class
