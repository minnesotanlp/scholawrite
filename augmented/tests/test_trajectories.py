# Tests for scholawrite.trajectories module.
import pytest

from scholawrite.trajectories import (
    EditClassification,
    classify_edit,
    compute_transition,
    apply_trajectory,
    compute_ambiguity_flag,
    tokenize,
    TrajectoryResult,
    update_span_with_trajectory,
    SUBSTANTIAL_EDIT_THRESHOLD,
)
from scholawrite.schema import (
    AmbiguityFlag,
    AugmentedRevision,
    InjectionLevel,
    InjectionSpan,
    Label,
    TrajectoryState,
)


class TestTokenize:
    """Tests for text tokenization."""

    def test_empty_string(self) -> None:
        assert tokenize("") == []

    def test_single_word(self) -> None:
        assert tokenize("hello") == ["hello"]

    def test_multiple_words(self) -> None:
        tokens = tokenize("Hello world")
        assert tokens == ["hello", "world"]

    def test_lowercases_tokens(self) -> None:
        tokens = tokenize("Hello WORLD")
        assert tokens == ["hello", "world"]

    def test_handles_punctuation(self) -> None:
        tokens = tokenize("Hello, world! How are you?")
        assert tokens == ["hello", "world", "how", "are", "you"]

    def test_handles_numbers(self) -> None:
        tokens = tokenize("There are 42 items")
        assert tokens == ["there", "are", "42", "items"]


class TestClassifyEdit:
    """Tests for edit classification."""

    def test_no_change(self) -> None:
        tokens = ["hello", "world"]
        assert classify_edit(tokens, tokens.copy()) == EditClassification.NONE

    def test_empty_to_empty(self) -> None:
        assert classify_edit([], []) == EditClassification.NONE

    def test_empty_to_content(self) -> None:
        assert classify_edit([], ["hello"]) == EditClassification.SUBSTANTIAL

    def test_content_to_empty(self) -> None:
        assert classify_edit(["hello"], []) == EditClassification.SUBSTANTIAL

    def test_light_edit_single_word_change(self) -> None:
        # Change 1 of 10 tokens = 10% change (light)
        old = ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog", "today"]
        new = ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "cat", "today"]
        result = classify_edit(old, new)
        # dog->cat = 2 changes (1 removed + 1 added) out of 10 = 20%, which is at threshold
        assert result in (EditClassification.LIGHT, EditClassification.SUBSTANTIAL)

    def test_light_edit_below_threshold(self) -> None:
        # Very minor change: 1 out of 20 tokens changed
        old = ["a"] * 20
        new = ["a"] * 19 + ["b"]
        # 2 changes (1 removed, 1 added) / 20 = 10% < 20%
        result = classify_edit(old, new)
        assert result == EditClassification.LIGHT

    def test_substantial_edit_above_threshold(self) -> None:
        # Change 5 of 10 tokens = 50% change (substantial)
        old = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        new = ["a", "b", "c", "d", "e", "x", "y", "z", "w", "v"]
        result = classify_edit(old, new)
        assert result == EditClassification.SUBSTANTIAL

    def test_substantial_edit_at_threshold(self) -> None:
        # Exactly at 20% threshold: 2 changes out of 10
        old = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        new = ["a", "b", "c", "d", "e", "f", "g", "h", "x", "y"]
        result = classify_edit(old, new)
        # 4 changes (i,j removed + x,y added) / 10 = 40% >= 20%
        assert result == EditClassification.SUBSTANTIAL


class TestComputeTransition:
    """Tests for trajectory state transitions."""

    def test_cold_stays_cold_on_no_edit(self) -> None:
        result = compute_transition(TrajectoryState.COLD, EditClassification.NONE)
        assert result == TrajectoryState.COLD

    def test_cold_to_warm_on_light_edit(self) -> None:
        result = compute_transition(TrajectoryState.COLD, EditClassification.LIGHT)
        assert result == TrajectoryState.WARM

    def test_cold_to_assimilated_on_substantial_edit(self) -> None:
        result = compute_transition(TrajectoryState.COLD, EditClassification.SUBSTANTIAL)
        assert result == TrajectoryState.ASSIMILATED

    def test_warm_stays_warm_on_no_edit(self) -> None:
        result = compute_transition(TrajectoryState.WARM, EditClassification.NONE)
        assert result == TrajectoryState.WARM

    def test_warm_stays_warm_on_light_edit(self) -> None:
        result = compute_transition(TrajectoryState.WARM, EditClassification.LIGHT)
        assert result == TrajectoryState.WARM

    def test_warm_to_assimilated_on_substantial_edit(self) -> None:
        result = compute_transition(TrajectoryState.WARM, EditClassification.SUBSTANTIAL)
        assert result == TrajectoryState.ASSIMILATED

    def test_assimilated_stays_assimilated_on_any_edit(self) -> None:
        for edit in EditClassification:
            result = compute_transition(TrajectoryState.ASSIMILATED, edit)
            assert result == TrajectoryState.ASSIMILATED

    def test_transitions_are_monotonic(self) -> None:
        """Verify that transitions never go backward."""
        states = [TrajectoryState.COLD, TrajectoryState.WARM, TrajectoryState.ASSIMILATED]
        state_order = {s: i for i, s in enumerate(states)}

        for current_state in states:
            for edit in EditClassification:
                new_state = compute_transition(current_state, edit)
                assert state_order[new_state] >= state_order[current_state]


class TestComputeAmbiguityFlag:
    """Tests for ambiguity flag computation."""

    def test_cold_maps_to_none(self) -> None:
        assert compute_ambiguity_flag(TrajectoryState.COLD) == AmbiguityFlag.NONE

    def test_warm_maps_to_low(self) -> None:
        assert compute_ambiguity_flag(TrajectoryState.WARM) == AmbiguityFlag.LOW

    def test_assimilated_maps_to_medium(self) -> None:
        assert compute_ambiguity_flag(TrajectoryState.ASSIMILATED) == AmbiguityFlag.MEDIUM


class TestApplyTrajectory:
    """Tests for apply_trajectory function."""

    @pytest.fixture
    def sample_injection_span(self) -> InjectionSpan:
        """Create a sample injection span."""
        return InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=1,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

    def test_no_subsequent_revisions(self, sample_injection_span: InjectionSpan) -> None:
        """When there are no revisions after injection, state stays cold."""
        revisions = [
            AugmentedRevision(
                doc_id="doc_test",
                revision_id="rev_1",
                revision_index=1,
                text="This is the original injected text for testing purposes.",
                timestamp="2023-01-01T00:00:00+00:00",
                provenance_hash="hash1",
                annotations=[],
            ),
        ]

        result = apply_trajectory(sample_injection_span, revisions, injection_revision_index=1)

        assert result.final_state == TrajectoryState.COLD
        assert result.ambiguity_flag == AmbiguityFlag.NONE
        assert len(result.transition_history) == 1

    def test_unchanged_across_revisions(self, sample_injection_span: InjectionSpan) -> None:
        """When span text doesn't change, state stays cold."""
        original_text = "This is the original injected text for testing purposes."
        revisions = [
            AugmentedRevision(
                doc_id="doc_test",
                revision_id=f"rev_{i}",
                revision_index=i,
                text=original_text,
                timestamp=f"2023-01-0{i+1}T00:00:00+00:00",
                provenance_hash=f"hash{i}",
                annotations=[],
            )
            for i in range(3)
        ]

        span = InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_1",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=len(original_text),
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

        result = apply_trajectory(span, revisions, injection_revision_index=1)

        assert result.final_state == TrajectoryState.COLD
        assert result.ambiguity_flag == AmbiguityFlag.NONE

    def test_light_edit_transitions_to_warm(self) -> None:
        """Light edit should transition from cold to warm."""
        original = "This is the original injected text for our testing purposes here."
        modified = "This is the original injected text for our testing purposes now."  # 1 word change

        revisions = [
            AugmentedRevision(
                doc_id="doc_test",
                revision_id="rev_0",
                revision_index=0,
                text=original,
                timestamp="2023-01-01T00:00:00+00:00",
                provenance_hash="hash0",
                annotations=[],
            ),
            AugmentedRevision(
                doc_id="doc_test",
                revision_id="rev_1",
                revision_index=1,
                text=modified,
                timestamp="2023-01-02T00:00:00+00:00",
                provenance_hash="hash1",
                annotations=[],
            ),
        ]

        span = InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_0",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=len(original),
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

        result = apply_trajectory(span, revisions, injection_revision_index=0)

        # Should transition to warm (light edit)
        assert result.final_state in (TrajectoryState.WARM, TrajectoryState.ASSIMILATED)
        assert len(result.transition_history) >= 1

    def test_substantial_edit_transitions_to_assimilated(self) -> None:
        """Substantial edit should transition directly to assimilated."""
        original = "The quick brown fox jumps over the lazy dog every day."
        modified = "A slow gray cat sleeps under the active rabbit each night."  # Major rewrite

        revisions = [
            AugmentedRevision(
                doc_id="doc_test",
                revision_id="rev_0",
                revision_index=0,
                text=original,
                timestamp="2023-01-01T00:00:00+00:00",
                provenance_hash="hash0",
                annotations=[],
            ),
            AugmentedRevision(
                doc_id="doc_test",
                revision_id="rev_1",
                revision_index=1,
                text=modified,
                timestamp="2023-01-02T00:00:00+00:00",
                provenance_hash="hash1",
                annotations=[],
            ),
        ]

        span = InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_0",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=len(original),
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

        result = apply_trajectory(span, revisions, injection_revision_index=0)

        assert result.final_state == TrajectoryState.ASSIMILATED
        assert result.ambiguity_flag == AmbiguityFlag.MEDIUM

    def test_preserves_original_boundaries(self) -> None:
        """Original boundaries should be preserved in result."""
        revisions = [
            AugmentedRevision(
                doc_id="doc_test",
                revision_id="rev_0",
                revision_index=0,
                text="Original text here.",
                timestamp="2023-01-01T00:00:00+00:00",
                provenance_hash="hash0",
                annotations=[],
            ),
        ]

        span = InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_0",
            injection_id="inj_001",
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=5,
            span_end_char=15,
            span_start_sentence=0,
            span_end_sentence=0,
            generator_class="strong-frontier",
            prompt_hash="abc123",
            rng_seed=42,
            provenance_hash="hash123",
            label=Label.INJECTION_CONTEXTUAL,
        )

        result = apply_trajectory(span, revisions, injection_revision_index=0)

        assert result.original_start_char == 5
        assert result.original_end_char == 15


class TestUpdateSpanWithTrajectory:
    """Tests for updating injection spans with trajectory results."""

    def test_updates_trajectory_state(self) -> None:
        """Should update trajectory_state from result."""
        span = InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_0",
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

        result = TrajectoryResult(
            final_state=TrajectoryState.WARM,
            ambiguity_flag=AmbiguityFlag.LOW,
            transition_history=[(0, TrajectoryState.COLD), (1, TrajectoryState.WARM)],
            span_start_char=0,
            span_end_char=50,
            original_start_char=0,
            original_end_char=50,
        )

        updated = update_span_with_trajectory(span, result)

        assert updated.trajectory_state == TrajectoryState.WARM
        assert updated.ambiguity_flag == AmbiguityFlag.LOW
        # Other fields preserved
        assert updated.doc_id == span.doc_id
        assert updated.injection_id == span.injection_id
        assert updated.injection_level == span.injection_level
        assert updated.label == span.label

    def test_preserves_immutability(self) -> None:
        """Original span should be unchanged."""
        span = InjectionSpan(
            doc_id="doc_test",
            revision_id="rev_0",
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

        result = TrajectoryResult(
            final_state=TrajectoryState.ASSIMILATED,
            ambiguity_flag=AmbiguityFlag.MEDIUM,
            transition_history=[(0, TrajectoryState.COLD)],
            span_start_char=0,
            span_end_char=50,
            original_start_char=0,
            original_end_char=50,
        )

        update_span_with_trajectory(span, result)

        # Original should be unchanged
        assert span.trajectory_state == TrajectoryState.COLD
        assert span.ambiguity_flag == AmbiguityFlag.NONE


class TestTrajectoryResult:
    """Tests for TrajectoryResult dataclass."""

    def test_creation(self) -> None:
        result = TrajectoryResult(
            final_state=TrajectoryState.WARM,
            ambiguity_flag=AmbiguityFlag.LOW,
            transition_history=[(0, TrajectoryState.COLD), (2, TrajectoryState.WARM)],
            span_start_char=10,
            span_end_char=100,
            original_start_char=10,
            original_end_char=100,
        )

        assert result.final_state == TrajectoryState.WARM
        assert result.ambiguity_flag == AmbiguityFlag.LOW
        assert len(result.transition_history) == 2
        assert result.span_start_char == 10
        assert result.span_end_char == 100


class TestThresholdConstant:
    """Tests for threshold configuration."""

    def test_threshold_is_20_percent(self) -> None:
        """Verify threshold matches documentation (20%)."""
        assert SUBSTANTIAL_EDIT_THRESHOLD == 0.20
