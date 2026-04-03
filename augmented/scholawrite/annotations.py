"""Forensic validation for causal traces and biometric signatures."""
from __future__ import annotations

from statistics import mean, stdev
from typing import Dict, List, Iterable, Optional
from dataclasses import dataclass
from .schema import (
    AmbiguityFlag,
    AugmentedDocument,
    AugmentedRevision,
    InjectionSpan,
    TrajectoryState,
)
from .injection import detect_prompt_leakage

__all__ = [
    "ValidationError",
    "ValidationResult",
    "CausalForensicValidator",
    "validate_annotations",
    "validate_revision",
    "validate_span_boundaries",
    "validate_span_overlap",
    "validate_trajectory_ambiguity",
    "check_injection_span_consistency",
    "validate_earned_ambiguity",
    "validate_trajectory_monotonicity",
    "validate_span_leakage",
    "validate_all_leakage",
    "LeakageValidationResult",
    "verify_span_content",
    "verify_all_spans_content",
    "SpanContentValidationResult",
    "compute_boundary_erosion",
]


@dataclass(frozen=True)
class ValidationError:
    """A validation error with context information."""
    doc_id: str
    revision_id: str
    span_id: Optional[str]
    error_type: str
    message: str

    def __str__(self) -> str:
        return f"{self.doc_id}/{self.revision_id}/{self.span_id}: [{self.error_type}] {self.message}"

@dataclass(frozen=True)
class ValidationResult:
    """Result of validation with errors and statistics."""
    errors: List[ValidationError]
    documents_checked: int
    revisions_checked: int
    spans_checked: int

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

class CausalForensicValidator:
    """Validates that trajectory labels are earned by measurable causal signatures."""

    MIN_TRACE_LENGTH_WARM = 3
    MIN_TRACE_LENGTH_ASSIMILATED = 5
    MIN_COUPLING_WARM = 0.3
    MIN_COUPLING_ASSIMILATED = 0.5

    @staticmethod
    def validate_earned_label(span: InjectionSpan) -> List[str]:
        """Validate that a span's trajectory label is supported by causal evidence."""
        errors = []
        if span.trajectory_state == TrajectoryState.COLD:
            return []
        if not span.causal_trace:
            return ["Missing causal trace sidecar"]

        x = [1 if e.status == "repair" else 0 for e in span.causal_trace[:-1]]
        y = [e.syntactic_complexity for e in span.causal_trace[1:]]

        coupling = 0.0
        if len(x) > 5:
            try:
                mu_x, mu_y = mean(x), mean(y)
                std_x, std_y = stdev(x), stdev(y)
                if std_x > 0 and std_y > 0:
                    coupling = sum((xi - mu_x) * (yi - mu_y) for xi, yi in zip(x, y)) / ((len(x)-1) * std_x * std_y)
            except (ValueError, ZeroDivisionError, TypeError):
                pass

        if span.trajectory_state == TrajectoryState.WARM:
            if len(span.causal_trace) < CausalForensicValidator.MIN_TRACE_LENGTH_WARM:
                errors.append(
                    f"WARM trajectory requires at least {CausalForensicValidator.MIN_TRACE_LENGTH_WARM} "
                    f"causal events, got {len(span.causal_trace)}"
                )
            if abs(coupling) < CausalForensicValidator.MIN_COUPLING_WARM and len(x) > 5:
                errors.append(
                    f"WARM trajectory requires coupling >= {CausalForensicValidator.MIN_COUPLING_WARM}, "
                    f"got {coupling:.3f}"
                )

        if span.trajectory_state == TrajectoryState.ASSIMILATED:
            if span.ambiguity_flag == AmbiguityFlag.NONE:
                errors.append("ASSIMILATED trajectory invalid: cannot have ambiguity_flag=NONE")
            if len(span.causal_trace) < CausalForensicValidator.MIN_TRACE_LENGTH_ASSIMILATED:
                errors.append(
                    f"ASSIMILATED trajectory requires at least {CausalForensicValidator.MIN_TRACE_LENGTH_ASSIMILATED} "
                    f"causal events, got {len(span.causal_trace)}"
                )
            if abs(coupling) < 0.55:
                errors.append(f"ASSIMILATED label invalid: weak coupling r={coupling:.2f} (min 0.55)")

            gs = [e.glucose_at_event for e in span.causal_trace]
            for i in range(len(gs)-1):
                if gs[i+1] > gs[i] + 0.0001:
                    errors.append(f"Causal impossibility: glucose increased at step {i+1}")
                    break

        return errors

    @staticmethod
    def validate_causal_trace_sufficiency(span: InjectionSpan) -> List[str]:
        """Validate that causal trace length supports the trajectory state."""
        errors = []

        if span.trajectory_state == TrajectoryState.COLD:
            return errors

        if span.trajectory_state == TrajectoryState.WARM:
            if not span.causal_trace or len(span.causal_trace) < CausalForensicValidator.MIN_TRACE_LENGTH_WARM:
                trace_len = len(span.causal_trace) if span.causal_trace else 0
                errors.append(
                    f"WARM state requires at least {CausalForensicValidator.MIN_TRACE_LENGTH_WARM} "
                    f"causal events, got {trace_len}"
                )

        if span.trajectory_state == TrajectoryState.ASSIMILATED:
            if not span.causal_trace or len(span.causal_trace) < CausalForensicValidator.MIN_TRACE_LENGTH_ASSIMILATED:
                trace_len = len(span.causal_trace) if span.causal_trace else 0
                errors.append(
                    f"ASSIMILATED state requires at least {CausalForensicValidator.MIN_TRACE_LENGTH_ASSIMILATED} "
                    f"causal events, got {trace_len}"
                )

        return errors

    @staticmethod
    def validate_coupling_supports_ambiguity(span: InjectionSpan) -> List[str]:
        """Validate that coupling values support the claimed ambiguity level."""
        errors = []
        from .metrics import compute_causal_signatures

        if not span.causal_trace:
            if span.ambiguity_flag in (AmbiguityFlag.MEDIUM, AmbiguityFlag.HIGH):
                errors.append(
                    f"{span.ambiguity_flag.value.upper()} ambiguity requires causal trace for coupling verification"
                )
            return errors

        sigs = compute_causal_signatures(span.causal_trace)
        coupling = abs(sigs.get("coupling", 0.0))

        if span.ambiguity_flag == AmbiguityFlag.HIGH:
            if coupling < CausalForensicValidator.MIN_COUPLING_ASSIMILATED:
                errors.append(
                    f"HIGH ambiguity requires coupling >= {CausalForensicValidator.MIN_COUPLING_ASSIMILATED}, "
                    f"got {coupling:.3f}"
                )
        elif span.ambiguity_flag == AmbiguityFlag.MEDIUM:
            if coupling < CausalForensicValidator.MIN_COUPLING_WARM:
                errors.append(
                    f"MEDIUM ambiguity requires coupling >= {CausalForensicValidator.MIN_COUPLING_WARM}, "
                    f"got {coupling:.3f}"
                )

        return errors

def validate_revision(rev: AugmentedRevision) -> List[ValidationError]:
    """Validate a single revision's spans for boundary and causal constraints."""
    errors = []
    for span in rev.annotations:
        if span.span_start_char < 0 or span.span_end_char > len(rev.text):
            errors.append(ValidationError(rev.doc_id, rev.revision_id, span.injection_id, "boundary", "Offset out of bounds"))
        if span.label.is_injection():
            for err_msg in CausalForensicValidator.validate_earned_label(span):
                errors.append(ValidationError(rev.doc_id, rev.revision_id, span.injection_id, "causal_integrity", err_msg))
    return errors

def validate_span_boundaries(span: InjectionSpan, text: str) -> List[ValidationError]:
    """Validate that span boundaries are within text bounds."""
    errors = []

    if span.span_start_char < 0:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "boundary", f"span_start_char is negative: {span.span_start_char}"
        ))
    if span.span_end_char > len(text):
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "boundary", f"span_end_char ({span.span_end_char}) exceeds text length ({len(text)})"
        ))
    if span.span_start_char > span.span_end_char:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "boundary", f"span_start_char ({span.span_start_char}) > span_end_char ({span.span_end_char})"
        ))
    if span.span_start_sentence < 0:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "boundary", f"span_start_sentence is negative: {span.span_start_sentence}"
        ))
    if span.span_start_sentence > span.span_end_sentence:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "boundary", f"span_start_sentence ({span.span_start_sentence}) > span_end_sentence ({span.span_end_sentence})"
        ))

    return errors


def validate_span_overlap(spans: List[InjectionSpan]) -> List[ValidationError]:
    """Check if any spans overlap with each other."""
    errors = []
    if len(spans) < 2:
        return errors

    sorted_spans = sorted(spans, key=lambda s: s.span_start_char)
    for i in range(len(sorted_spans) - 1):
        curr = sorted_spans[i]
        next_span = sorted_spans[i + 1]
        if curr.span_end_char > next_span.span_start_char:
            errors.append(ValidationError(
                curr.doc_id, curr.revision_id, None,
                "overlap", f"Spans {curr.injection_id} and {next_span.injection_id} overlap"
            ))

    return errors


def validate_trajectory_ambiguity(span: InjectionSpan) -> List[ValidationError]:
    """Validate that trajectory state and ambiguity flag are consistent."""
    errors = []

    if span.trajectory_state is None:
        return errors

    if span.trajectory_state == TrajectoryState.WARM:
        if span.ambiguity_flag == AmbiguityFlag.NONE:
            errors.append(ValidationError(
                span.doc_id, span.revision_id, span.injection_id,
                "ambiguity", "WARM trajectory requires ambiguity_flag >= LOW, got NONE"
            ))
    elif span.trajectory_state == TrajectoryState.ASSIMILATED:
        if span.ambiguity_flag in (AmbiguityFlag.NONE, AmbiguityFlag.LOW):
            errors.append(ValidationError(
                span.doc_id, span.revision_id, span.injection_id,
                "ambiguity", f"ASSIMILATED trajectory requires ambiguity_flag >= MEDIUM, got {span.ambiguity_flag.value}"
            ))

    return errors


def check_injection_span_consistency(span: InjectionSpan) -> List[ValidationError]:
    """Check that injection spans have required metadata fields."""
    errors = []

    if not span.label.is_injection():
        return errors

    if not span.provenance_hash:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "consistency", "Injection span missing provenance_hash"
        ))
    if not span.generator_class:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "consistency", "Injection span missing generator_class"
        ))
    if not span.prompt_hash:
        errors.append(ValidationError(
            span.doc_id, span.revision_id, span.injection_id,
            "consistency", "Injection span missing prompt_hash"
        ))

    return errors


def _find_span_in_revision(
    injection_id: str,
    revision: AugmentedRevision
) -> Optional[InjectionSpan]:
    """Find a span by injection_id in a revision."""
    for s in revision.annotations:
        if s.injection_id == injection_id:
            return s
    return None


def compute_boundary_erosion(
    original_span: InjectionSpan,
    subsequent_revisions: List[AugmentedRevision]
) -> float:
    """Compute boundary erosion ratio across subsequent revisions.

    Boundary erosion measures how much the span's boundaries have shifted
    relative to its original size. Higher erosion indicates greater
    integration with surrounding human text.

    Returns a ratio where 0.0 = no erosion, 1.0 = complete boundary shift.
    """
    if not subsequent_revisions:
        return 0.0

    original_size = original_span.span_end_char - original_span.span_start_char
    if original_size <= 0:
        return 0.0

    total_shift = 0
    spans_found = 0

    for rev in subsequent_revisions:
        later_span = _find_span_in_revision(original_span.injection_id, rev)
        if later_span is None:
            continue

        spans_found += 1
        start_shift = abs(later_span.span_start_char - original_span.span_start_char)
        end_shift = abs(later_span.span_end_char - original_span.span_end_char)
        total_shift += start_shift + end_shift

    if spans_found == 0:
        return 0.0

    avg_shift = total_shift / spans_found
    return min(1.0, avg_shift / original_size)


def validate_earned_ambiguity(
    span: InjectionSpan,
    subsequent_revisions: Optional[List[AugmentedRevision]] = None
) -> List[ValidationError]:
    """Verify ambiguity flag is earned through causal evidence and boundary evolution.

    Validates that the ambiguity level is supported by causal trace evidence
    and, when subsequent_revisions are provided, by actual boundary erosion
    across the revision history.
    """
    errors = []

    if not span.label.is_injection():
        return errors

    from .metrics import compute_causal_signatures

    state_name = span.trajectory_state.value if span.trajectory_state else 'None'

    if span.ambiguity_flag == AmbiguityFlag.NONE:
        if span.trajectory_state != TrajectoryState.COLD:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message=f"NONE ambiguity requires COLD state, got {state_name}"
            ))

    elif span.ambiguity_flag == AmbiguityFlag.LOW:
        if span.trajectory_state != TrajectoryState.WARM:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message=f"LOW ambiguity requires WARM state, got {state_name}"
            ))
        trace_len = len(span.causal_trace) if span.causal_trace else 0
        if trace_len < 3:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message=f"LOW ambiguity requires at least 3 causal events, got {trace_len}"
            ))

    elif span.ambiguity_flag == AmbiguityFlag.MEDIUM:
        if span.trajectory_state != TrajectoryState.ASSIMILATED:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message=f"MEDIUM ambiguity requires ASSIMILATED state, got {state_name}"
            ))
        if span.causal_trace:
            sigs = compute_causal_signatures(span.causal_trace)
            coupling = abs(sigs.get("coupling", 0.0))
            if coupling < CausalForensicValidator.MIN_COUPLING_WARM:
                errors.append(ValidationError(
                    doc_id=span.doc_id,
                    revision_id=span.revision_id,
                    span_id=span.injection_id,
                    error_type="earned_ambiguity",
                    message=f"MEDIUM ambiguity requires coupling >= {CausalForensicValidator.MIN_COUPLING_WARM}, got {coupling:.3f}"
                ))
        else:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message="MEDIUM ambiguity requires causal trace for coupling verification"
            ))

        if subsequent_revisions:
            erosion = compute_boundary_erosion(span, subsequent_revisions)
            if erosion < 0.1:
                errors.append(ValidationError(
                    doc_id=span.doc_id,
                    revision_id=span.revision_id,
                    span_id=span.injection_id,
                    error_type="earned_ambiguity",
                    message=f"MEDIUM ambiguity requires boundary erosion >= 0.1, got {erosion:.3f}"
                ))

    elif span.ambiguity_flag == AmbiguityFlag.HIGH:
        if span.trajectory_state != TrajectoryState.ASSIMILATED:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message=f"HIGH ambiguity requires ASSIMILATED state, got {state_name}"
            ))
        if span.causal_trace:
            sigs = compute_causal_signatures(span.causal_trace)
            coupling = abs(sigs.get("coupling", 0.0))
            if coupling < CausalForensicValidator.MIN_COUPLING_ASSIMILATED:
                errors.append(ValidationError(
                    doc_id=span.doc_id,
                    revision_id=span.revision_id,
                    span_id=span.injection_id,
                    error_type="earned_ambiguity",
                    message=f"HIGH ambiguity requires coupling >= {CausalForensicValidator.MIN_COUPLING_ASSIMILATED}, got {coupling:.3f}"
                ))
        else:
            errors.append(ValidationError(
                doc_id=span.doc_id,
                revision_id=span.revision_id,
                span_id=span.injection_id,
                error_type="earned_ambiguity",
                message="HIGH ambiguity requires causal trace for coupling verification"
            ))

        if subsequent_revisions:
            erosion = compute_boundary_erosion(span, subsequent_revisions)
            if erosion < 0.25:
                errors.append(ValidationError(
                    doc_id=span.doc_id,
                    revision_id=span.revision_id,
                    span_id=span.injection_id,
                    error_type="earned_ambiguity",
                    message=f"HIGH ambiguity requires boundary erosion >= 0.25, got {erosion:.3f}"
                ))

    return errors


def validate_trajectory_monotonicity(
    span_history: List[InjectionSpan]
) -> List[ValidationError]:
    """Validate that trajectory transitions follow COLD -> WARM -> ASSIMILATED order."""
    errors = []

    if len(span_history) < 2:
        return errors

    state_order = {
        TrajectoryState.COLD: 0,
        TrajectoryState.WARM: 1,
        TrajectoryState.ASSIMILATED: 2,
    }

    for i in range(len(span_history) - 1):
        curr_span = span_history[i]
        next_span = span_history[i + 1]

        if curr_span.trajectory_state is None or next_span.trajectory_state is None:
            continue

        curr_order = state_order.get(curr_span.trajectory_state, -1)
        next_order = state_order.get(next_span.trajectory_state, -1)

        if next_order < curr_order:
            errors.append(ValidationError(
                doc_id=next_span.doc_id,
                revision_id=next_span.revision_id,
                span_id=next_span.injection_id,
                error_type="trajectory_monotonicity",
                message=(
                    f"Non-monotonic trajectory transition: "
                    f"{curr_span.trajectory_state.value} -> {next_span.trajectory_state.value} "
                    f"(expected COLD -> WARM -> ASSIMILATED only)"
                )
            ))

    return errors


@dataclass(frozen=True)
class LeakageValidationResult:
    """Result of leakage validation with pattern statistics."""
    errors: List[ValidationError]
    spans_checked: int
    spans_with_leakage: int
    pattern_counts: Dict[str, int]

    @property
    def is_clean(self) -> bool:
        return len(self.errors) == 0


def validate_span_leakage(span: InjectionSpan, text: str) -> List[ValidationError]:
    """Validate that injected span content does not contain prompt leakage."""
    errors = []

    if not span.label.is_injection():
        return errors

    if span.span_start_char < 0 or span.span_end_char > len(text):
        return errors

    span_text = text[span.span_start_char:span.span_end_char]
    if not span_text.strip():
        return errors

    for pattern in detect_prompt_leakage(span_text):
        errors.append(ValidationError(
            doc_id=span.doc_id,
            revision_id=span.revision_id,
            span_id=span.injection_id,
            error_type="prompt_leakage",
            message=f"Detected LLM artifact pattern: {pattern}"
        ))

    return errors


def validate_all_leakage(docs: Iterable[AugmentedDocument]) -> LeakageValidationResult:
    """Validate all documents for prompt leakage in injected content."""
    all_errors = []
    spans_checked = 0
    spans_with_leakage = 0
    pattern_counts: Dict[str, int] = {}

    for doc in docs:
        for rev in doc.revisions:
            for span in rev.annotations:
                if not span.label.is_injection():
                    continue

                spans_checked += 1
                if span.span_start_char < 0 or span.span_end_char > len(rev.text):
                    continue

                span_text = rev.text[span.span_start_char:span.span_end_char]
                detected = detect_prompt_leakage(span_text)

                if detected:
                    spans_with_leakage += 1
                    for pattern in detected:
                        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                        all_errors.append(ValidationError(
                            doc_id=span.doc_id,
                            revision_id=span.revision_id,
                            span_id=span.injection_id,
                            error_type="prompt_leakage",
                            message=f"Detected LLM artifact pattern: {pattern}"
                        ))

    return LeakageValidationResult(
        errors=all_errors,
        spans_checked=spans_checked,
        spans_with_leakage=spans_with_leakage,
        pattern_counts=pattern_counts,
    )


def validate_annotations(
    docs: Iterable[AugmentedDocument],
    check_leakage: bool = False,
) -> ValidationResult:
    """Validate annotations across all documents."""
    all_errors = []
    d_count, r_count, s_count = 0, 0, 0
    docs_list = list(docs)

    for doc in docs_list:
        d_count += 1
        span_history_by_id: Dict[str, List[InjectionSpan]] = {}
        revisions_by_index: Dict[int, AugmentedRevision] = {
            rev.revision_index: rev for rev in doc.revisions
        }

        for rev in doc.revisions:
            r_count += 1
            s_count += len(rev.annotations)
            all_errors.extend(validate_revision(rev))

            for span in rev.annotations:
                if span.label.is_injection():
                    subsequent = [
                        revisions_by_index[i]
                        for i in sorted(revisions_by_index.keys())
                        if i > rev.revision_index
                    ]
                    all_errors.extend(validate_earned_ambiguity(span, subsequent))

                    if span.injection_id not in span_history_by_id:
                        span_history_by_id[span.injection_id] = []
                    span_history_by_id[span.injection_id].append(span)

                    if check_leakage:
                        all_errors.extend(validate_span_leakage(span, rev.text))

        for history in span_history_by_id.values():
            all_errors.extend(validate_trajectory_monotonicity(history))

    return ValidationResult(all_errors, d_count, r_count, s_count)


def verify_span_content(
    span: InjectionSpan,
    text: str,
    expected_content: Optional[str] = None,
) -> Optional[ValidationError]:
    """Verify that a span references valid, non-empty content in the text."""
    if span.span_start_char >= len(text):
        return ValidationError(
            doc_id=span.doc_id, revision_id=span.revision_id, span_id=span.injection_id,
            error_type="span_content",
            message=f"Span start {span.span_start_char} exceeds text length {len(text)}"
        )
    if span.span_end_char > len(text):
        return ValidationError(
            doc_id=span.doc_id, revision_id=span.revision_id, span_id=span.injection_id,
            error_type="span_content",
            message=f"Span end {span.span_end_char} exceeds text length {len(text)}"
        )
    if span.span_start_char < 0:
        return ValidationError(
            doc_id=span.doc_id, revision_id=span.revision_id, span_id=span.injection_id,
            error_type="span_content",
            message=f"Span start {span.span_start_char} is negative"
        )
    if span.span_start_char > span.span_end_char:
        return ValidationError(
            doc_id=span.doc_id, revision_id=span.revision_id, span_id=span.injection_id,
            error_type="span_content",
            message=f"Span start ({span.span_start_char}) > span end ({span.span_end_char})"
        )

    content = text[span.span_start_char:span.span_end_char]
    if not content.strip():
        return ValidationError(
            doc_id=span.doc_id, revision_id=span.revision_id, span_id=span.injection_id,
            error_type="span_content",
            message="Span references empty or whitespace-only content"
        )
    if expected_content is not None and expected_content not in content:
        return ValidationError(
            doc_id=span.doc_id, revision_id=span.revision_id, span_id=span.injection_id,
            error_type="span_content",
            message=f"Expected content not found in span. Expected: '{expected_content[:50]}...'"
        )

    return None


@dataclass(frozen=True)
class SpanContentValidationResult:
    """Result of span content verification across all documents."""
    errors: List[ValidationError]
    spans_verified: int
    spans_failed: int
    documents_checked: int
    revisions_checked: int

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def failure_rate(self) -> float:
        return self.spans_failed / self.spans_verified if self.spans_verified else 0.0


def verify_all_spans_content(
    docs: Iterable[AugmentedDocument],
    expected_content_map: Optional[Dict[str, str]] = None,
) -> SpanContentValidationResult:
    """Verify that all injection spans reference valid content in their documents."""
    all_errors = []
    spans_verified = 0
    spans_failed = 0
    d_count = 0
    r_count = 0
    expected_map = expected_content_map or {}

    for doc in docs:
        d_count += 1
        for rev in doc.revisions:
            r_count += 1
            for span in rev.annotations:
                if not span.label.is_injection():
                    continue

                spans_verified += 1
                expected = expected_map.get(span.injection_id)
                error = verify_span_content(span, rev.text, expected)

                if error is not None:
                    all_errors.append(error)
                    spans_failed += 1

    return SpanContentValidationResult(
        errors=all_errors,
        spans_verified=spans_verified,
        spans_failed=spans_failed,
        documents_checked=d_count,
        revisions_checked=r_count,
    )
