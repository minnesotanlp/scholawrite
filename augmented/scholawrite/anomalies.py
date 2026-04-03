"""Anomaly detection for process signature violations in revision histories."""
from __future__ import annotations

from typing import List, Optional, Sequence
from .schema import (
    AmbiguityFlag,
    AugmentedDocument,
    AugmentedRevision,
    InjectionSpan,
    Label,
)
from .metrics import (
    compute_causal_signatures,
    LOCALITY_ANOMALY_THRESHOLD,
    COUPLING_ANOMALY_THRESHOLD,
    JACCARD_LARGE_DIFF_THRESHOLD,
    TRUNCATION_THRESHOLD,
)
from .text import compute_word_jaccard

__all__ = ["generate_anomalies", "_detect_revision_anomaly"]


def _detect_revision_anomaly(
    revisions: List[AugmentedRevision],
    index: int,
    deltas: List[Optional[float]]
) -> Optional[Label]:
    """Detect revision-level anomalies based on structural patterns."""
    if index <= 0 or index >= len(revisions):
        return None

    curr_rev = revisions[index]
    prev_rev = revisions[index - 1]
    delta = deltas[index] if index < len(deltas) else None

    if curr_rev.revision_index != prev_rev.revision_index + 1:
        return Label.ANOMALY_MISSING_REVISION

    if delta is not None and delta < 0:
        return Label.ANOMALY_TIMESTAMP_JITTER

    if prev_rev.text and curr_rev.text:
        if len(curr_rev.text) < len(prev_rev.text) * TRUNCATION_THRESHOLD:
            return Label.ANOMALY_TRUNCATION

    if prev_rev.text and curr_rev.text:
        similarity = compute_word_jaccard(prev_rev.text, curr_rev.text)
        if similarity < JACCARD_LARGE_DIFF_THRESHOLD:
            return Label.ANOMALY_LARGE_DIFF

    return None


def generate_anomalies(docs: Sequence[AugmentedDocument]) -> List[AugmentedDocument]:
    """
    Audit all injections for process signature violations.
    Anomalous injections are those where causal coupling is absent or broken.
    """
    anomaly_docs = []
    for doc in docs:
        updated_revisions = []
        for rev in doc.revisions:
            annotations = list(rev.annotations)

            # Check existing injections for biometrically impossible process signatures
            for span in rev.annotations:
                if not span.label.is_injection(): continue

                # 1. Causal Anomaly Detection
                # Validates that injection signatures fall within human baselines
                sigs = compute_causal_signatures(span.causal_trace)
                label = None

                # Locality > LOCALITY_ANOMALY_THRESHOLD (4.5) indicates spatially
                # disjoint repair patterns inconsistent with human cognition
                if sigs["locality"] > LOCALITY_ANOMALY_THRESHOLD:
                    label = Label.ANOMALY_PROCESS_VIOLATION
                # Coupling < COUPLING_ANOMALY_THRESHOLD (0.2) indicates absence
                # of human production signatures (resource coupling)
                elif abs(sigs["coupling"]) < COUPLING_ANOMALY_THRESHOLD:
                    label = Label.ANOMALY_NO_COUPLING

                if label:
                    annotations.append(InjectionSpan(
                        doc_id=rev.doc_id, revision_id=rev.revision_id, injection_id=f"anom_{span.injection_id[:8]}",
                        injection_level=None, trajectory_state=None, ambiguity_flag=AmbiguityFlag.HIGH,
                        span_start_char=span.span_start_char, span_end_char=span.span_end_char,
                        span_start_sentence=span.span_start_sentence, span_end_sentence=span.span_end_sentence,
                        generator_class="detector", prompt_hash="detector", rng_seed=0, provenance_hash=None,
                        label=label, causal_trace=span.causal_trace
                    ))

            updated_revisions.append(AugmentedRevision(
                doc_id=rev.doc_id,
                revision_id=rev.revision_id,
                revision_index=rev.revision_index,
                text=rev.text,
                timestamp=rev.timestamp,
                provenance_hash=rev.provenance_hash,
                annotations=annotations,
                before_text=getattr(rev, 'before_text', None),
                writing_intention=getattr(rev, 'writing_intention', None),
                high_level_category=getattr(rev, 'high_level_category', None),
            ))
        anomaly_docs.append(AugmentedDocument(doc.doc_id, updated_revisions))
    return anomaly_docs
