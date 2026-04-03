"""Causal signature primitives, classification metrics, and threshold constants.

Handles two distinct types of metrics:
1. Causal signature metrics for forensic validation (locality, coupling, plausibility)
2. Classification metrics for model evaluation (accuracy, F1, confusion matrix)

DOES NOT contain:
- Label parsing -> lives in labels.py
- Text manipulation -> lives in text.py
"""
from __future__ import annotations

from statistics import correlation
from typing import Iterable, List, Tuple, Dict, Any, Optional
from .schema import CausalEvent

# Causal Coupling Thresholds (see docs/THRESHOLDS.md)
COUPLING_PLAUSIBILITY_THRESHOLD = 0.5
COUPLING_ASSIMILATED_VALIDATION = 0.55
COUPLING_STRONG_THRESHOLD = 0.6
COUPLING_ASSIMILATED_THRESHOLD = 0.7
COUPLING_WARM_MINIMUM = 0.4
COUPLING_ANOMALY_THRESHOLD = 0.2

# Locality Thresholds (human repair distance: 1.0-3.5 tokens)
LOCALITY_HUMAN_MIN = 1.0
LOCALITY_HUMAN_MAX = 3.5
LOCALITY_WARM_MAX = 4.5
LOCALITY_ANOMALY_THRESHOLD = 4.5

# Edit Classification
SUBSTANTIAL_EDIT_RATIO = 0.20

# Detection Thresholds
NCD_DEFAULT_THRESHOLD = 0.45
NCD_HARDENING_DELTA = 0.10
JACCARD_LARGE_DIFF_THRESHOLD = 0.30
TRUNCATION_THRESHOLD = 0.40

# Trace Validation
MIN_TRACE_LENGTH_COUPLING = 10
MIN_TRACE_LENGTH_METRICS = 5
GLUCOSE_INCREASE_TOLERANCE = 0.0001

# Embodied Simulation
GLUCOSE_INITIAL = 1.0
GLUCOSE_FLOOR = 0.05
GLUCOSE_DEPLETION_RATE = 0.9992
GLUCOSE_LEXICAL_STARVATION = 0.65
FATIGUE_DIVISOR = 12000.0
SYNTACTIC_COLLAPSE_BASE = 4.0
SYNTACTIC_COLLAPSE_GLUCOSE_FACTOR = 3.5
HIGH_SYNTACTIC_DEMAND = 5.0

__all__ = [
    # Metrics functions
    "auc", "f1", "span_iou", "compute_causal_signatures",
    "compute_classification_metrics",
    # Coupling thresholds
    "COUPLING_PLAUSIBILITY_THRESHOLD", "COUPLING_ASSIMILATED_VALIDATION",
    "COUPLING_STRONG_THRESHOLD", "COUPLING_ASSIMILATED_THRESHOLD",
    "COUPLING_WARM_MINIMUM", "COUPLING_ANOMALY_THRESHOLD",
    # Locality thresholds
    "LOCALITY_HUMAN_MIN", "LOCALITY_HUMAN_MAX", "LOCALITY_WARM_MAX",
    "LOCALITY_ANOMALY_THRESHOLD",
    # Edit thresholds
    "SUBSTANTIAL_EDIT_RATIO",
    # Detection thresholds
    "NCD_DEFAULT_THRESHOLD", "NCD_HARDENING_DELTA",
    "JACCARD_LARGE_DIFF_THRESHOLD", "TRUNCATION_THRESHOLD",
    # Trace thresholds
    "MIN_TRACE_LENGTH_COUPLING", "MIN_TRACE_LENGTH_METRICS",
    "GLUCOSE_INCREASE_TOLERANCE",
    # Embodied simulation thresholds
    "GLUCOSE_INITIAL", "GLUCOSE_FLOOR", "GLUCOSE_DEPLETION_RATE",
    "GLUCOSE_LEXICAL_STARVATION", "FATIGUE_DIVISOR",
    "SYNTACTIC_COLLAPSE_BASE", "SYNTACTIC_COLLAPSE_GLUCOSE_FACTOR",
    "HIGH_SYNTACTIC_DEMAND",
]

def compute_causal_signatures(trace: List[CausalEvent]) -> Dict[str, float]:
    """Compute repair locality, resource coupling, and plausibility from a causal trace."""
    if not trace:
        return {"locality": 0.0, "coupling": 0.0, "plausibility": 0.0}

    failure_indices = [i for i, e in enumerate(trace) if e.status != "success"]
    repair_indices = [i for i, e in enumerate(trace) if e.repair_artifact]

    locality = 0.0
    if failure_indices and repair_indices:
        distances = []
        for f in failure_indices:
            next_repairs = [r for r in repair_indices if r >= f]
            if next_repairs:
                distances.append(min(next_repairs) - f + 1)
        locality = sum(distances) / len(distances) if distances else 0.0

    failure_flags = [1 if e.status != "success" else 0 for e in trace]
    complexities = [e.syntactic_complexity for e in trace]

    coupling = 0.0
    if len(trace) > MIN_TRACE_LENGTH_METRICS and sum(failure_flags) > 0:
        try:
            coupling = correlation(failure_flags[:-1], complexities[1:])
        except (ValueError, TypeError, ZeroDivisionError):
            coupling = 0.0

    plausibility = 1.0 if (
        LOCALITY_HUMAN_MIN <= locality <= LOCALITY_HUMAN_MAX
        and abs(coupling) > COUPLING_PLAUSIBILITY_THRESHOLD
    ) else 0.0

    return {
        "locality": round(locality, 2),
        "coupling": round(coupling, 3),
        "plausibility": plausibility
    }

def auc(y_true: Iterable[float], y_score: Iterable[float]) -> float:
    """Compute Area Under the Receiver Operating Characteristic Curve (ROC AUC)."""
    pairs = list(zip(y_score, y_true))
    if not pairs: return 0.0
    pos = sum(1 for _, y in pairs if y > 0)
    neg = len(pairs) - pos
    if pos == 0 or neg == 0: return 0.0
    pairs.sort(key=lambda x: x[0])
    ranks, i = [0.0] * len(pairs), 0
    while i < len(pairs):
        j = i + 1
        while j < len(pairs) and pairs[j][0] == pairs[i][0]: j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j): ranks[k] = avg_rank
        i = j
    sum_ranks_pos = sum(rank for rank, (_, y) in zip(ranks, pairs) if y > 0)
    return (sum_ranks_pos - (pos * (pos + 1)) / 2.0) / (pos * neg)

def f1(y_true: Iterable[int], y_pred: Iterable[int]) -> float:
    """Compute F1 score."""
    tp, fp, fn = 0, 0, 0
    for yt, yp in zip(y_true, y_pred):
        if yp and yt: tp += 1
        elif yp and not yt: fp += 1
        elif yt and not yp: fn += 1
    denom = (2 * tp + fp + fn)
    return (2 * tp) / denom if denom > 0 else 0.0

def span_iou(pred_spans: Iterable[Tuple[int, int]], true_spans: Iterable[Tuple[int, int]]) -> float:
    """Compute Intersection over Union for character spans."""
    def merge(sps):
        sps = sorted([(s, e) for s, e in sps if e > s])
        if not sps: return []
        res = [sps[0]]
        for s, e in sps[1:]:
            ls, le = res[-1]
            if s <= le: res[-1] = (ls, max(le, e))
            else: res.append((s, e))
        return res
    mp, mt = merge(pred_spans), merge(true_spans)
    if not mp and not mt: return 1.0
    if not mp or not mt: return 0.0
    inter, i, j = 0, 0, 0
    while i < len(mp) and j < len(mt):
        s, e = max(mp[i][0], mt[j][0]), min(mp[i][1], mt[j][1])
        if e > s: inter += e - s
        if mp[i][1] <= mt[j][1]: i += 1
        else: j += 1
    union = sum(e-s for s,e in mp) + sum(e-s for s,e in mt) - inter
    return inter / union if union > 0 else 0.0


def compute_classification_metrics(
    y_true: List[Any],
    y_pred: List[Any],
    labels: Optional[List[str]] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Compute classification metrics for model evaluation.

    Consolidates the scattered calculate_metrics functions from:
    - analysis/classification_stats.py
    - scholawrite_finetune/bert_finetune/small_model_inference.py
    - scholawrite_finetune/bert_finetune/small_model_classifier.py
    - scholawrite_finetune/bert_finetune/small_model_analysis.py

    Args:
        y_true: Ground truth labels.
        y_pred: Predicted labels.
        labels: Optional list of label names for ordering. If None, derived from y_true.
        verbose: If True, print metrics to stdout. Defaults to True.

    Returns:
        Dict containing accuracy, macro_f1, micro_f1, and per-class metrics.

    Note:
        For confusion matrix visualization, use sklearn directly with matplotlib.
        This function focuses on computing numeric metrics without side effects.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}")

    if not y_true:
        return {"accuracy": 0.0, "macro_f1": 0.0, "micro_f1": 0.0, "per_class": {}}

    # Compute accuracy
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / len(y_true)

    # Get all unique labels
    all_labels = labels or sorted(set(y_true) | set(y_pred))

    # Compute per-class precision, recall, F1
    per_class: Dict[str, Dict[str, float]] = {}
    f1_scores: List[float] = []

    for label in all_labels:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == label and yp == label)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != label and yp == label)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == label and yp != label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[str(label)] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1_score, 4),
            "support": sum(1 for yt in y_true if yt == label),
        }
        f1_scores.append(f1_score)

    # Macro F1: average of per-class F1 scores
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    # Micro F1: same as accuracy for multiclass single-label classification
    micro_f1 = accuracy

    if verbose:
        print(f"accuracy: {accuracy:.4f}")
        print(f"macro_f1: {macro_f1:.4f}")
        print(f"micro_f1: {micro_f1:.4f}")

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_f1": round(micro_f1, 4),
        "per_class": per_class,
    }
