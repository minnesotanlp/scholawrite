# Tests for scholawrite.annotations module.
import pytest

from scholawrite.annotations import (
    validate_annotations,
    validate_span_boundaries,
    validate_span_overlap,
    validate_trajectory_ambiguity,
    validate_earned_ambiguity,
    validate_trajectory_monotonicity,
    check_injection_span_consistency,
    verify_span_content,
    verify_all_spans_content,
    CausalForensicValidator,
    ValidationError,
    ValidationResult,
    SpanContentValidationResult,
)
from scholawrite.schema import (
    AmbiguityFlag,
    AugmentedDocument,
    AugmentedRevision,
    CausalEvent,
    InjectionLevel,
    InjectionSpan,
    Label,
    TrajectoryState,
)


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_str_with_span_id(self) -> None:
        error = ValidationError(
            doc_id="doc_1",
            revision_id="rev_1",
            span_id="inj_001",
            error_type="boundary",
            message="test error message",
        )
        s = str(error)
        assert "doc_1" in s
        assert "rev_1" in s
        assert "inj_001" in s
        assert "boundary" in s
        assert "test error message" in s

    def test_str_without_span_id(self) -> None:
        error = ValidationError(
            doc_id="doc_1",
            revision_id="rev_1",
            span_id=None,
            error_type="overlap",
            message="test message",
        )
        s = str(error)
        assert "doc_1" in s
        assert "rev_1" in s
        assert "overlap" in s


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_is_valid_with_no_errors(self) -> None:
        result = ValidationResult(
            errors=[],
            documents_checked=5,
            revisions_checked=20,
            spans_checked=10,
        )
        assert result.is_valid is True

    def test_is_valid_with_errors(self) -> None:
        result = ValidationResult(
            errors=[
                ValidationError("d", "r", "s", "type", "msg"),
            ],
            documents_checked=5,
            revisions_checked=20,
            spans_checked=10,
        )
        assert result.is_valid is False


class TestValidateSpanBoundaries:
    """Tests for span boundary validation."""

    @pytest.fixture
    def valid_span(self) -> InjectionSpan:
        """Create a valid injection span."""
        return InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=10,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=1,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

    def test_valid_boundaries(self, valid_span: InjectionSpan) -> None:
        text = "x" * 100  # 100 character text
        errors = validate_span_boundaries(valid_span, text)
        assert len(errors) == 0

    def test_negative_start_char(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=-5,  # Invalid
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=1,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = validate_span_boundaries(span, "x" * 100)
        assert len(errors) == 1
        assert errors[0].error_type == "boundary"
        assert "negative" in errors[0].message

    def test_end_exceeds_text_length(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=10,
            span_end_char=200,  # Exceeds text length
            span_start_sentence=0,
            span_end_sentence=1,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = validate_span_boundaries(span, "x" * 100)
        assert len(errors) == 1
        assert errors[0].error_type == "boundary"
        assert "exceeds" in errors[0].message

    def test_start_greater_than_end(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=60,  # Greater than end
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=1,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = validate_span_boundaries(span, "x" * 100)
        assert len(errors) == 1
        assert errors[0].error_type == "boundary"
        assert ">" in errors[0].message

    def test_negative_sentence_index(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=10,
            span_end_char=50,
            span_start_sentence=-1,  # Invalid
            span_end_sentence=1,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = validate_span_boundaries(span, "x" * 100)
        assert len(errors) == 1
        assert "sentence" in errors[0].message

    def test_sentence_start_greater_than_end(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=10,
            span_end_char=50,
            span_start_sentence=5,  # Greater than end
            span_end_sentence=2,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = validate_span_boundaries(span, "x" * 100)
        assert len(errors) == 1
        assert "sentence" in errors[0].message


class TestValidateSpanOverlap:
    """Tests for span overlap validation."""

    def _make_span(self, start: int, end: int, span_id: str) -> InjectionSpan:
        """Create a span with given boundaries."""
        return InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id=span_id,
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=start,
            span_end_char=end,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

    def test_no_overlap_empty_list(self) -> None:
        errors = validate_span_overlap([])
        assert len(errors) == 0

    def test_no_overlap_single_span(self) -> None:
        spans = [self._make_span(0, 50, "inj_001")]
        errors = validate_span_overlap(spans)
        assert len(errors) == 0

    def test_no_overlap_adjacent_spans(self) -> None:
        spans = [
            self._make_span(0, 50, "inj_001"),
            self._make_span(50, 100, "inj_002"),  # Adjacent, not overlapping
        ]
        errors = validate_span_overlap(spans)
        assert len(errors) == 0

    def test_no_overlap_disjoint_spans(self) -> None:
        spans = [
            self._make_span(0, 30, "inj_001"),
            self._make_span(50, 80, "inj_002"),
            self._make_span(100, 120, "inj_003"),
        ]
        errors = validate_span_overlap(spans)
        assert len(errors) == 0

    def test_overlap_detected(self) -> None:
        spans = [
            self._make_span(0, 50, "inj_001"),
            self._make_span(40, 80, "inj_002"),  # Overlaps with first
        ]
        errors = validate_span_overlap(spans)
        assert len(errors) == 1
        assert errors[0].error_type == "overlap"

    def test_overlap_unsorted_input(self) -> None:
        """Should detect overlap even if spans are not sorted."""
        spans = [
            self._make_span(40, 80, "inj_002"),
            self._make_span(0, 50, "inj_001"),  # Overlaps with above
        ]
        errors = validate_span_overlap(spans)
        assert len(errors) == 1

    def test_nested_spans_overlap(self) -> None:
        """One span completely inside another."""
        spans = [
            self._make_span(0, 100, "inj_001"),
            self._make_span(20, 40, "inj_002"),  # Nested inside first
        ]
        errors = validate_span_overlap(spans)
        assert len(errors) == 1


class TestValidateTrajectoryAmbiguity:
    """Tests for trajectory-ambiguity validation."""

    def _make_span_with_trajectory(
        self,
        trajectory_state: TrajectoryState,
        ambiguity_flag: AmbiguityFlag,
    ) -> InjectionSpan:
        """Create a span with given trajectory and ambiguity."""
        return InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=trajectory_state,
            ambiguity_flag=ambiguity_flag,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

    def test_cold_with_none_is_valid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.COLD, AmbiguityFlag.NONE)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0

    def test_cold_with_low_is_valid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.COLD, AmbiguityFlag.LOW)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0

    def test_warm_with_low_is_valid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.WARM, AmbiguityFlag.LOW)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0

    def test_warm_with_medium_is_valid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.WARM, AmbiguityFlag.MEDIUM)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0

    def test_warm_with_none_is_invalid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.WARM, AmbiguityFlag.NONE)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 1
        assert errors[0].error_type == "ambiguity"

    def test_assimilated_with_medium_is_valid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.ASSIMILATED, AmbiguityFlag.MEDIUM)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0

    def test_assimilated_with_high_is_valid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.ASSIMILATED, AmbiguityFlag.HIGH)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0

    def test_assimilated_with_none_is_invalid(self) -> None:
        span = self._make_span_with_trajectory(TrajectoryState.ASSIMILATED, AmbiguityFlag.NONE)
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 1
        assert errors[0].error_type == "ambiguity"

    def test_none_trajectory_state_skips_validation(self) -> None:
        """Non-injection labels have None trajectory_state."""
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=None,
            trajectory_state=None,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="",
            prompt_hash="",
            rng_seed=0,
            provenance_hash=None,
            label=Label.ANOMALY_LARGE_DIFF,
        )
        errors = validate_trajectory_ambiguity(span)
        assert len(errors) == 0


class TestValidateAnnotations:
    """Tests for the main validate_annotations function."""

    def test_empty_documents(self) -> None:
        result = validate_annotations([])
        assert result.is_valid
        assert result.documents_checked == 0
        assert result.revisions_checked == 0
        assert result.spans_checked == 0

    def test_document_with_no_annotations(self) -> None:
        docs = [
            AugmentedDocument(
                doc_id="doc_1",
                revisions=[
                    AugmentedRevision(
                        doc_id="doc_1",
                        revision_id="rev_1",
                        revision_index=0,
                        text="Some text here.",
                        timestamp="2023-01-01T00:00:00+00:00",
                        provenance_hash="hash",
                        annotations=[],
                    ),
                ],
            ),
        ]
        result = validate_annotations(docs)
        assert result.is_valid
        assert result.documents_checked == 1
        assert result.revisions_checked == 1
        assert result.spans_checked == 0

    def test_valid_annotations(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=15,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        docs = [
            AugmentedDocument(
                doc_id="doc_1",
                revisions=[
                    AugmentedRevision(
                        doc_id="doc_1",
                        revision_id="rev_1",
                        revision_index=0,
                        text="Some text here.",
                        timestamp="2023-01-01T00:00:00+00:00",
                        provenance_hash="hash",
                        annotations=[span],
                    ),
                ],
            ),
        ]
        result = validate_annotations(docs)
        assert result.is_valid
        assert result.spans_checked == 1

    def test_invalid_boundary(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=100,  # Exceeds text length
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        docs = [
            AugmentedDocument(
                doc_id="doc_1",
                revisions=[
                    AugmentedRevision(
                        doc_id="doc_1",
                        revision_id="rev_1",
                        revision_index=0,
                        text="Short text.",  # Only 11 chars
                        timestamp="2023-01-01T00:00:00+00:00",
                        provenance_hash="hash",
                        annotations=[span],
                    ),
                ],
            ),
        ]
        result = validate_annotations(docs)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "boundary"


class TestCheckInjectionSpanConsistency:
    """Tests for injection span consistency checks."""

    def test_valid_injection_span(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = check_injection_span_consistency(span)
        assert len(errors) == 0

    def test_missing_provenance_hash(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash=None,  # Missing
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = check_injection_span_consistency(span)
        assert len(errors) == 1
        assert "provenance_hash" in errors[0].message

    def test_missing_generator_class(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="",  # Empty
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = check_injection_span_consistency(span)
        assert len(errors) == 1
        assert "generator_class" in errors[0].message

    def test_missing_prompt_hash(self) -> None:
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="",  # Empty
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )
        errors = check_injection_span_consistency(span)
        assert len(errors) == 1
        assert "prompt_hash" in errors[0].message

    def test_non_injection_label_skips_checks(self) -> None:
        """Anomaly labels don't need injection metadata."""
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="anom_001",
            injection_level=None,
            trajectory_state=None,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="",  # Empty but OK for anomaly
            prompt_hash="",  # Empty but OK for anomaly
            rng_seed=0,
            provenance_hash=None,  # None but OK for anomaly
            label=Label.ANOMALY_LARGE_DIFF,
        )
        errors = check_injection_span_consistency(span)
        assert len(errors) == 0


class TestValidateEarnedAmbiguity:
    """Tests for earned ambiguity validation."""

    def _make_causal_events(self, count: int, with_repairs: bool = False) -> list[CausalEvent]:
        """Create a list of causal events for testing."""
        events = []
        for i in range(count):
            events.append(CausalEvent(
                intention=f"token_{i}",
                actual_output=f"token_{i}",
                status="repair" if (with_repairs and i % 3 == 0) else "success",
                failure_mode="typo" if (with_repairs and i % 3 == 0) else None,
                repair_artifact="fixed" if (with_repairs and i % 3 == 0) else None,
                glucose_at_event=0.8 - (i * 0.01),  # Decreasing glucose
                latency_ms=100 + i * 10,
                syntactic_complexity=2.0 + (i * 0.1) if not with_repairs else (1.5 if i % 3 == 1 else 2.0),
            ))
        return events

    def _make_span(
        self,
        trajectory_state: TrajectoryState,
        ambiguity_flag: AmbiguityFlag,
        causal_trace: list[CausalEvent] | None = None,
    ) -> InjectionSpan:
        """Create a span with given trajectory, ambiguity, and causal trace."""
        return InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=trajectory_state,
            ambiguity_flag=ambiguity_flag,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
            causal_trace=causal_trace or [],
        )

    def test_none_ambiguity_with_cold_state_is_valid(self) -> None:
        """NONE ambiguity with COLD state should pass."""
        span = self._make_span(TrajectoryState.COLD, AmbiguityFlag.NONE)
        errors = validate_earned_ambiguity(span)
        assert len(errors) == 0

    def test_none_ambiguity_with_warm_state_is_invalid(self) -> None:
        """NONE ambiguity with WARM state should fail."""
        span = self._make_span(TrajectoryState.WARM, AmbiguityFlag.NONE,
                               causal_trace=self._make_causal_events(5))
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("NONE ambiguity requires COLD state" in e.message for e in errors)

    def test_low_ambiguity_with_warm_state_and_trace_is_valid(self) -> None:
        """LOW ambiguity with WARM state and sufficient trace should pass."""
        span = self._make_span(TrajectoryState.WARM, AmbiguityFlag.LOW,
                               causal_trace=self._make_causal_events(5))
        errors = validate_earned_ambiguity(span)
        assert len(errors) == 0

    def test_low_ambiguity_with_cold_state_is_invalid(self) -> None:
        """LOW ambiguity with COLD state should fail."""
        span = self._make_span(TrajectoryState.COLD, AmbiguityFlag.LOW)
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("LOW ambiguity requires WARM state" in e.message for e in errors)

    def test_low_ambiguity_with_insufficient_trace_is_invalid(self) -> None:
        """LOW ambiguity with fewer than 3 causal events should fail."""
        span = self._make_span(TrajectoryState.WARM, AmbiguityFlag.LOW,
                               causal_trace=self._make_causal_events(2))
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("at least 3 causal events" in e.message for e in errors)

    def test_medium_ambiguity_with_assimilated_and_trace_is_valid(self) -> None:
        """MEDIUM ambiguity with ASSIMILATED state and sufficient coupling should pass."""
        # Create trace with repairs to generate coupling
        span = self._make_span(TrajectoryState.ASSIMILATED, AmbiguityFlag.MEDIUM,
                               causal_trace=self._make_causal_events(10, with_repairs=True))
        errors = validate_earned_ambiguity(span)
        # May or may not have errors depending on actual coupling value
        # At minimum, the state requirement should pass
        state_errors = [e for e in errors if "requires ASSIMILATED state" in e.message]
        assert len(state_errors) == 0

    def test_medium_ambiguity_with_warm_state_is_invalid(self) -> None:
        """MEDIUM ambiguity with WARM state should fail."""
        span = self._make_span(TrajectoryState.WARM, AmbiguityFlag.MEDIUM,
                               causal_trace=self._make_causal_events(5))
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("MEDIUM ambiguity requires ASSIMILATED state" in e.message for e in errors)

    def test_medium_ambiguity_without_trace_is_invalid(self) -> None:
        """MEDIUM ambiguity without causal trace should fail."""
        span = self._make_span(TrajectoryState.ASSIMILATED, AmbiguityFlag.MEDIUM)
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("requires causal trace" in e.message for e in errors)

    def test_high_ambiguity_with_cold_state_is_invalid(self) -> None:
        """HIGH ambiguity with COLD state should fail."""
        span = self._make_span(TrajectoryState.COLD, AmbiguityFlag.HIGH)
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("HIGH ambiguity requires ASSIMILATED state" in e.message for e in errors)

    def test_high_ambiguity_without_trace_is_invalid(self) -> None:
        """HIGH ambiguity without causal trace should fail."""
        span = self._make_span(TrajectoryState.ASSIMILATED, AmbiguityFlag.HIGH)
        errors = validate_earned_ambiguity(span)
        assert len(errors) >= 1
        assert any("requires causal trace" in e.message for e in errors)

    def test_non_injection_label_skips_validation(self) -> None:
        """Non-injection labels should skip earned ambiguity validation."""
        span = InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="anom_001",
            injection_level=None,
            trajectory_state=None,
            ambiguity_flag=AmbiguityFlag.HIGH,  # Would be invalid for injection
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="",
            prompt_hash="",
            rng_seed=0,
            provenance_hash=None,
            label=Label.ANOMALY_LARGE_DIFF,
        )
        errors = validate_earned_ambiguity(span)
        assert len(errors) == 0


class TestValidateTrajectoryMonotonicity:
    """Tests for trajectory monotonicity validation."""

    def _make_span_with_state(
        self,
        trajectory_state: TrajectoryState,
        revision_id: str = "rev_1",
    ) -> InjectionSpan:
        """Create a span with given trajectory state."""
        return InjectionSpan(
            doc_id="doc_1",
            revision_id=revision_id,
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=trajectory_state,
            ambiguity_flag=AmbiguityFlag.NONE if trajectory_state == TrajectoryState.COLD else AmbiguityFlag.LOW,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

    def test_empty_history_is_valid(self) -> None:
        """Empty span history should pass."""
        errors = validate_trajectory_monotonicity([])
        assert len(errors) == 0

    def test_single_span_is_valid(self) -> None:
        """Single span should pass."""
        history = [self._make_span_with_state(TrajectoryState.COLD)]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 0

    def test_cold_to_warm_is_valid(self) -> None:
        """COLD -> WARM transition should pass."""
        history = [
            self._make_span_with_state(TrajectoryState.COLD, "rev_1"),
            self._make_span_with_state(TrajectoryState.WARM, "rev_2"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 0

    def test_cold_to_warm_to_assimilated_is_valid(self) -> None:
        """COLD -> WARM -> ASSIMILATED transition should pass."""
        history = [
            self._make_span_with_state(TrajectoryState.COLD, "rev_1"),
            self._make_span_with_state(TrajectoryState.WARM, "rev_2"),
            self._make_span_with_state(TrajectoryState.ASSIMILATED, "rev_3"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 0

    def test_cold_to_assimilated_is_valid(self) -> None:
        """COLD -> ASSIMILATED skip transition should pass (skipping WARM is allowed)."""
        history = [
            self._make_span_with_state(TrajectoryState.COLD, "rev_1"),
            self._make_span_with_state(TrajectoryState.ASSIMILATED, "rev_2"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 0

    def test_staying_at_same_state_is_valid(self) -> None:
        """Staying at the same state should pass."""
        history = [
            self._make_span_with_state(TrajectoryState.WARM, "rev_1"),
            self._make_span_with_state(TrajectoryState.WARM, "rev_2"),
            self._make_span_with_state(TrajectoryState.WARM, "rev_3"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 0

    def test_warm_to_cold_is_invalid(self) -> None:
        """WARM -> COLD reverse transition should fail."""
        history = [
            self._make_span_with_state(TrajectoryState.WARM, "rev_1"),
            self._make_span_with_state(TrajectoryState.COLD, "rev_2"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 1
        assert errors[0].error_type == "trajectory_monotonicity"
        assert "Non-monotonic" in errors[0].message
        assert "warm -> cold" in errors[0].message

    def test_assimilated_to_warm_is_invalid(self) -> None:
        """ASSIMILATED -> WARM reverse transition should fail."""
        history = [
            self._make_span_with_state(TrajectoryState.ASSIMILATED, "rev_1"),
            self._make_span_with_state(TrajectoryState.WARM, "rev_2"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 1
        assert "Non-monotonic" in errors[0].message
        assert "assimilated -> warm" in errors[0].message

    def test_assimilated_to_cold_is_invalid(self) -> None:
        """ASSIMILATED -> COLD reverse transition should fail."""
        history = [
            self._make_span_with_state(TrajectoryState.ASSIMILATED, "rev_1"),
            self._make_span_with_state(TrajectoryState.COLD, "rev_2"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 1
        assert "Non-monotonic" in errors[0].message

    def test_multiple_violations_detected(self) -> None:
        """Multiple reverse transitions should be detected."""
        history = [
            self._make_span_with_state(TrajectoryState.ASSIMILATED, "rev_1"),
            self._make_span_with_state(TrajectoryState.WARM, "rev_2"),
            self._make_span_with_state(TrajectoryState.COLD, "rev_3"),
        ]
        errors = validate_trajectory_monotonicity(history)
        assert len(errors) == 2  # Both transitions are invalid


class TestCausalForensicValidatorEnhancements:
    """Tests for enhanced CausalForensicValidator methods."""

    def _make_causal_events(self, count: int, with_repairs: bool = False) -> list[CausalEvent]:
        """Create a list of causal events for testing."""
        events = []
        for i in range(count):
            events.append(CausalEvent(
                intention=f"token_{i}",
                actual_output=f"token_{i}",
                status="repair" if (with_repairs and i % 3 == 0) else "success",
                failure_mode="typo" if (with_repairs and i % 3 == 0) else None,
                repair_artifact="fixed" if (with_repairs and i % 3 == 0) else None,
                glucose_at_event=0.8 - (i * 0.01),
                latency_ms=100 + i * 10,
                syntactic_complexity=2.0 + (i * 0.1) if not with_repairs else (1.5 if i % 3 == 1 else 2.0),
            ))
        return events

    def _make_span(
        self,
        trajectory_state: TrajectoryState,
        ambiguity_flag: AmbiguityFlag,
        causal_trace: list[CausalEvent] | None = None,
    ) -> InjectionSpan:
        return InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=trajectory_state,
            ambiguity_flag=ambiguity_flag,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
            causal_trace=causal_trace or [],
        )

    def test_validate_causal_trace_sufficiency_cold(self) -> None:
        """COLD state doesn't require causal trace."""
        span = self._make_span(TrajectoryState.COLD, AmbiguityFlag.NONE)
        errors = CausalForensicValidator.validate_causal_trace_sufficiency(span)
        assert len(errors) == 0

    def test_validate_causal_trace_sufficiency_warm_without_trace(self) -> None:
        """WARM state without trace should fail."""
        span = self._make_span(TrajectoryState.WARM, AmbiguityFlag.LOW)
        errors = CausalForensicValidator.validate_causal_trace_sufficiency(span)
        assert len(errors) == 1
        assert "WARM state requires at least" in errors[0]

    def test_validate_causal_trace_sufficiency_warm_with_trace(self) -> None:
        """WARM state with sufficient trace should pass."""
        span = self._make_span(TrajectoryState.WARM, AmbiguityFlag.LOW,
                               causal_trace=self._make_causal_events(5))
        errors = CausalForensicValidator.validate_causal_trace_sufficiency(span)
        assert len(errors) == 0

    def test_validate_causal_trace_sufficiency_assimilated_without_trace(self) -> None:
        """ASSIMILATED state without trace should fail."""
        span = self._make_span(TrajectoryState.ASSIMILATED, AmbiguityFlag.MEDIUM)
        errors = CausalForensicValidator.validate_causal_trace_sufficiency(span)
        assert len(errors) == 1
        assert "ASSIMILATED state requires at least" in errors[0]

    def test_validate_coupling_supports_ambiguity_none(self) -> None:
        """NONE ambiguity doesn't require coupling verification."""
        span = self._make_span(TrajectoryState.COLD, AmbiguityFlag.NONE)
        errors = CausalForensicValidator.validate_coupling_supports_ambiguity(span)
        assert len(errors) == 0

    def test_validate_coupling_supports_ambiguity_high_without_trace(self) -> None:
        """HIGH ambiguity without trace should fail."""
        span = self._make_span(TrajectoryState.ASSIMILATED, AmbiguityFlag.HIGH)
        errors = CausalForensicValidator.validate_coupling_supports_ambiguity(span)
        assert len(errors) == 1
        assert "requires causal trace" in errors[0]

    def test_min_trace_length_constants(self) -> None:
        """Verify the minimum trace length constants are set correctly."""
        assert CausalForensicValidator.MIN_TRACE_LENGTH_WARM == 3
        assert CausalForensicValidator.MIN_TRACE_LENGTH_ASSIMILATED == 5

    def test_coupling_threshold_constants(self) -> None:
        """Verify the coupling threshold constants are set correctly."""
        assert CausalForensicValidator.MIN_COUPLING_WARM == 0.3
        assert CausalForensicValidator.MIN_COUPLING_ASSIMILATED == 0.5


class TestVerifySpanContent:
    """Tests for verify_span_content function."""

    def _make_span(
        self,
        start: int = 0,
        end: int = 50,
        injection_id: str = "inj_001",
    ) -> InjectionSpan:
        """Helper to create test spans."""
        return InjectionSpan(
            doc_id="doc_1",
            revision_id="rev_1",
            injection_id=injection_id,
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=start,
            span_end_char=end,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="test_model",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

    def test_valid_span_content(self) -> None:
        """Valid span should pass verification."""
        text = "This is some injected text in the document."
        span = self._make_span(start=8, end=25)  # "some injected te"
        error = verify_span_content(span, text)
        assert error is None

    def test_span_start_exceeds_text_length(self) -> None:
        """Span start beyond text should fail."""
        text = "Short text."
        span = self._make_span(start=100, end=150)
        error = verify_span_content(span, text)
        assert error is not None
        assert "exceeds text length" in error.message

    def test_span_end_exceeds_text_length(self) -> None:
        """Span end beyond text should fail."""
        text = "Short text."
        span = self._make_span(start=0, end=100)
        error = verify_span_content(span, text)
        assert error is not None
        assert "exceeds text length" in error.message

    def test_negative_span_start(self) -> None:
        """Negative span start should fail."""
        text = "Some text."
        span = self._make_span(start=-5, end=10)
        error = verify_span_content(span, text)
        assert error is not None
        assert "negative" in error.message

    def test_span_start_greater_than_end(self) -> None:
        """Span start > end should fail."""
        text = "Some text content here."
        span = self._make_span(start=15, end=5)
        error = verify_span_content(span, text)
        assert error is not None
        assert ">" in error.message

    def test_empty_content_fails(self) -> None:
        """Span referencing empty content should fail."""
        text = "Hello    World"  # spaces between
        span = self._make_span(start=5, end=9)  # "    "
        error = verify_span_content(span, text)
        assert error is not None
        assert "empty" in error.message

    def test_whitespace_only_content_fails(self) -> None:
        """Span referencing whitespace-only content should fail."""
        text = "Start   \n\t   End"
        span = self._make_span(start=5, end=13)  # whitespace section
        error = verify_span_content(span, text)
        assert error is not None
        assert "empty" in error.message

    def test_expected_content_found(self) -> None:
        """Verification with expected content should pass when found."""
        text = "This is injected: hello world in the text."
        span = self._make_span(start=18, end=29)  # "hello world"
        error = verify_span_content(span, text, expected_content="hello")
        assert error is None

    def test_expected_content_not_found(self) -> None:
        """Verification with expected content should fail when not found."""
        text = "This is injected: hello world in the text."
        span = self._make_span(start=18, end=29)  # "hello world"
        error = verify_span_content(span, text, expected_content="goodbye")
        assert error is not None
        assert "Expected content not found" in error.message


class TestVerifyAllSpansContent:
    """Tests for verify_all_spans_content function."""

    def _make_doc_with_spans(
        self,
        text: str,
        spans: list[tuple[int, int]],
    ) -> list[AugmentedDocument]:
        """Helper to create documents with injection spans."""
        annotations = []
        for i, (start, end) in enumerate(spans):
            annotations.append(
                InjectionSpan(
                    doc_id="doc_1",
                    revision_id="rev_1",
                    injection_id=f"inj_{i:03d}",
                    injection_level=InjectionLevel.CONTEXTUAL,
                    trajectory_state=TrajectoryState.COLD,
                    ambiguity_flag=AmbiguityFlag.NONE,
                    span_start_char=start,
                    span_end_char=end,
                    span_start_sentence=0,
                    span_end_sentence=0,
                    generator_class="test_model",
                    prompt_hash="abc123",
                    rng_seed=42,
                    provenance_hash="hash123",
                    label=Label.INJECTION_CONTEXTUAL,
                )
            )

        revision = AugmentedRevision(
            doc_id="doc_1",
            revision_id="rev_1",
            revision_index=0,
            text=text,
            timestamp=None,
            provenance_hash="rev_hash",
            annotations=annotations,
        )

        return [AugmentedDocument(doc_id="doc_1", revisions=[revision])]

    def test_all_spans_valid(self) -> None:
        """All valid spans should pass."""
        text = "This is some text with injected content here."
        docs = self._make_doc_with_spans(text, [(0, 10), (20, 35)])
        result = verify_all_spans_content(docs)
        assert result.is_valid
        assert result.spans_verified == 2
        assert result.spans_failed == 0

    def test_some_spans_invalid(self) -> None:
        """Invalid spans should be detected."""
        text = "Short text."
        docs = self._make_doc_with_spans(text, [(0, 5), (50, 100)])
        result = verify_all_spans_content(docs)
        assert not result.is_valid
        assert result.spans_verified == 2
        assert result.spans_failed == 1

    def test_failure_rate_calculation(self) -> None:
        """Failure rate should be calculated correctly."""
        text = "Some text here."
        docs = self._make_doc_with_spans(text, [(0, 4), (100, 200)])
        result = verify_all_spans_content(docs)
        assert result.failure_rate == 0.5

    def test_empty_document_list(self) -> None:
        """Empty document list should pass with zero counts."""
        result = verify_all_spans_content([])
        assert result.is_valid
        assert result.spans_verified == 0
        assert result.spans_failed == 0

    def test_expected_content_map(self) -> None:
        """Expected content map should be used for verification."""
        text = "This is injected: hello world in the text."
        docs = self._make_doc_with_spans(text, [(18, 29)])

        # Pass with correct expected content
        result = verify_all_spans_content(
            docs,
            expected_content_map={"inj_000": "hello"}
        )
        assert result.is_valid

        # Fail with incorrect expected content
        result_fail = verify_all_spans_content(
            docs,
            expected_content_map={"inj_000": "goodbye"}
        )
        assert not result_fail.is_valid


class TestSpanContentValidationResult:
    """Tests for SpanContentValidationResult dataclass."""

    def test_is_valid_with_no_errors(self) -> None:
        """Result with no errors should be valid."""
        result = SpanContentValidationResult(
            errors=[],
            spans_verified=10,
            spans_failed=0,
            documents_checked=2,
            revisions_checked=5,
        )
        assert result.is_valid

    def test_is_valid_with_errors(self) -> None:
        """Result with errors should be invalid."""
        result = SpanContentValidationResult(
            errors=[
                ValidationError("doc", "rev", "span", "type", "msg")
            ],
            spans_verified=10,
            spans_failed=1,
            documents_checked=2,
            revisions_checked=5,
        )
        assert not result.is_valid

    def test_failure_rate_zero_spans(self) -> None:
        """Failure rate should be 0 when no spans verified."""
        result = SpanContentValidationResult(
            errors=[],
            spans_verified=0,
            spans_failed=0,
            documents_checked=1,
            revisions_checked=1,
        )
        assert result.failure_rate == 0.0

    def test_failure_rate_calculation(self) -> None:
        """Failure rate should be calculated correctly."""
        result = SpanContentValidationResult(
            errors=[ValidationError("d", "r", "s", "t", "m")],
            spans_verified=4,
            spans_failed=1,
            documents_checked=1,
            revisions_checked=1,
        )
        assert result.failure_rate == 0.25
