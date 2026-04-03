"""Disaggregated harm analysis for injection detection."""
from __future__ import annotations

from typing import Dict, Sequence
from .schema import AugmentedDocument, Label

__all__ = ["compute_harm"]


_NAIVE_TEMPLATES = [
    "This is a general academic statement.",
    "This empirical investigation corroborates",
    "methodological constraints delineated",
    "juxtaposition of these findings necessitates",
    "Operationalizing these variables requires",
    "substantive evidence presented here supports",
    "inherent heterogeneity within the dataset",
    "underlying ontological assumptions remain foundational",
    "paradigm shift toward more systematic",
    "epistemological biases can significantly skew",
    "synergistic effects of multi-scalar interventions",
    "notwithstanding the preliminary nature",
    "utilization of advanced computational models",
    "subsequent research must address these identified gaps",
    "necessitates a more nuanced approach",
    "implications for large-scale infrastructure deployment",
    "delineated boundaries of this study warrant",
    "analytical setup provides a stable baseline",
    "the research methodology employed",
    "scholarly analysis reveals",
    "academic literature suggests",
    "furthermore, it is evident that",
    "this approach demonstrates",
    "the findings indicate that",
    "in conclusion, this study",
]


def _detect_template_match(text: str) -> bool:
    """Detect if text contains naive injection template patterns."""
    text_lower = text.lower()
    for template in _NAIVE_TEMPLATES:
        if template.lower() in text_lower:
            return True
    return False


def compute_harm(docs: Sequence[AugmentedDocument]) -> Dict[str, float]:
    """Compute performance metrics disaggregated by anomaly type and injection level."""
    results: Dict[str, float] = {}

    # Tracking per subgroup
    anomaly_stats: Dict[Label, Dict[str, int]] = {}
    level_stats: Dict[str, Dict[str, int]] = {}
    state_stats: Dict[str, Dict[str, int]] = {}

    for doc in docs:
        for rev in doc.revisions:
            # Ground truth
            has_inj = any(ann.label.is_injection() for ann in rev.annotations)
            anom_label = next((ann.label for ann in rev.annotations if ann.label.is_anomaly()), None)

            # Prediction: template-based detection for naive injections
            is_pred = _detect_template_match(rev.text)

            # 1. Anomaly FPR (false positives when we detect injection but ground truth is anomaly only)
            if anom_label and not has_inj:
                if anom_label not in anomaly_stats:
                    anomaly_stats[anom_label] = {"total": 0, "fp": 0}
                anomaly_stats[anom_label]["total"] += 1
                if is_pred:
                    anomaly_stats[anom_label]["fp"] += 1

            # 2. Injection Sensitivity by level and state
            if has_inj:
                for ann in rev.annotations:
                    if not ann.label.is_injection():
                        continue

                    # Track by injection level
                    lvl = ann.injection_level.value if ann.injection_level else "unknown"
                    if lvl not in level_stats:
                        level_stats[lvl] = {"total": 0, "tp": 0}
                    level_stats[lvl]["total"] += 1
                    if is_pred:
                        level_stats[lvl]["tp"] += 1

                    # Track by trajectory state
                    state = ann.trajectory_state.value if ann.trajectory_state else "unknown"
                    if state not in state_stats:
                        state_stats[state] = {"total": 0, "tp": 0}
                    state_stats[state]["total"] += 1
                    if is_pred:
                        state_stats[state]["tp"] += 1

    # Aggregate FPR per anomaly type
    for label, stats in anomaly_stats.items():
        key = f"fpr_{label.value.replace('.', '_')}"
        results[key] = stats["fp"] / stats["total"] if stats["total"] > 0 else 0.0

    # Aggregate sensitivity per injection level
    for lvl, stats in level_stats.items():
        results[f"sensitivity_level_{lvl}"] = stats["tp"] / stats["total"] if stats["total"] > 0 else 0.0

    # Aggregate sensitivity per trajectory state
    for state, stats in state_stats.items():
        results[f"sensitivity_state_{state}"] = stats["tp"] / stats["total"] if stats["total"] > 0 else 0.0

    return results
