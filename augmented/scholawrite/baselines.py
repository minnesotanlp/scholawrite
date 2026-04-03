"""Baseline detection methods including NCD and causal coupling analysis."""
from __future__ import annotations

import zlib
from typing import Dict, Sequence
from .metrics import auc, f1, compute_causal_signatures, NCD_DEFAULT_THRESHOLD
from .schema import AugmentedDocument

__all__ = ["run_baselines", "detect_ncd_anomalies"]

def run_baselines(docs: Sequence[AugmentedDocument], threshold: float = NCD_DEFAULT_THRESHOLD) -> Dict[str, float]:
    """Execute baseline suite including Causal Coupling AUC."""
    y_true, y_ncd, y_coupling = [], [], []

    for doc in docs:
        prev_text = ""
        for rev in doc.revisions:
            has_inj = any(ann.label.is_injection() for ann in rev.annotations)
            y_true.append(1 if has_inj else 0)

            # 1. Statistical Baseline (NCD)
            score = _compression_discontinuity(prev_text, rev.text) if prev_text else 0.0
            y_ncd.append(score)

            # 2. Causal Baseline (Resource Coupling)
            coupling_score = 0.0
            for ann in rev.annotations:
                if ann.label.is_injection() and ann.causal_trace:
                    sigs = compute_causal_signatures(ann.causal_trace)
                    coupling_score = max(coupling_score, abs(sigs["coupling"]))
            y_coupling.append(coupling_score)

            prev_text = rev.text

    return {
        "ncd_auc": round(auc(y_true, y_ncd), 4),
        "causal_coupling_auc": round(auc(y_true, y_coupling), 4),
        "overall_f1": round(f1(y_true, [1 if s > threshold else 0 for s in y_ncd]), 4)
    }

def detect_ncd_anomalies(prev_text: str, curr_text: str, threshold: float = NCD_DEFAULT_THRESHOLD) -> bool:
    """High-performance NCD-based anomaly detector.

    Uses Normalized Compression Distance to detect discontinuities
    between consecutive revisions that may indicate injection.

    Args:
        prev_text: Previous revision text
        curr_text: Current revision text
        threshold: NCD threshold (default: NCD_DEFAULT_THRESHOLD = 0.45)
                  Empirically tuned to balance precision/recall.

    Returns:
        True if NCD exceeds threshold, indicating potential anomaly.

    See docs/THRESHOLDS.md, Section "Detection Thresholds".
    """
    return _compression_discontinuity(prev_text, curr_text) > threshold

def _compression_discontinuity(a: str, b: str) -> float:
    """Normalized Compression Distance between two strings."""
    def get_len(t): return len(zlib.compress(t.encode("utf-8")))
    ca, cb = get_len(a), get_len(b)
    cab = get_len(a + " " + b)
    if max(ca, cb) == 0: return 0.0
    return min(max((cab - min(ca, cb)) / max(ca, cb), 0.0), 1.0)
