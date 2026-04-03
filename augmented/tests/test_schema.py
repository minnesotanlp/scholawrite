# Tests for scholawrite.schema module.
from dataclasses import asdict

import pytest

from scholawrite.schema import (
    AmbiguityFlag,
    InjectionLevel,
    TrajectoryState,
    Label,
    SeedRevision,
    SeedDocument,
    InjectionSpan,
    AugmentedRevision,
    AugmentedDocument,
    RunManifest,
    SplitSpec,
)


class TestAmbiguityFlag:
    """Tests for AmbiguityFlag enum."""

    def test_enum_values(self) -> None:
        assert AmbiguityFlag.NONE.value == "none"
        assert AmbiguityFlag.LOW.value == "low"
        assert AmbiguityFlag.MEDIUM.value == "medium"
        assert AmbiguityFlag.HIGH.value == "high"

    def test_string_comparison(self) -> None:
        # AmbiguityFlag inherits from str, so should be comparable
        assert AmbiguityFlag.NONE == "none"
        assert AmbiguityFlag.LOW == "low"


class TestInjectionLevel:
    """Tests for InjectionLevel enum."""

    def test_enum_values(self) -> None:
        assert InjectionLevel.NAIVE.value == "naive"
        assert InjectionLevel.TOPICAL.value == "topical"
        assert InjectionLevel.CONTEXTUAL.value == "contextual"

    def test_string_comparison(self) -> None:
        assert InjectionLevel.NAIVE == "naive"
        assert InjectionLevel.CONTEXTUAL == "contextual"

    def test_all_levels_defined(self) -> None:
        # Ensure all three levels from LABEL_TAXONOMY.md are defined
        levels = {level.value for level in InjectionLevel}
        assert levels == {"naive", "topical", "contextual"}


class TestTrajectoryState:
    """Tests for TrajectoryState enum."""

    def test_enum_values(self) -> None:
        assert TrajectoryState.COLD.value == "cold"
        assert TrajectoryState.WARM.value == "warm"
        assert TrajectoryState.ASSIMILATED.value == "assimilated"

    def test_string_comparison(self) -> None:
        assert TrajectoryState.COLD == "cold"
        assert TrajectoryState.ASSIMILATED == "assimilated"

    def test_all_states_defined(self) -> None:
        # Ensure all three states from TRAJECTORIES.md are defined
        states = {state.value for state in TrajectoryState}
        assert states == {"cold", "warm", "assimilated"}


class TestLabel:
    """Tests for Label enum."""

    def test_injection_labels(self) -> None:
        assert Label.INJECTION_NAIVE.value == "injection.naive"
        assert Label.INJECTION_TOPICAL.value == "injection.topical"
        assert Label.INJECTION_CONTEXTUAL.value == "injection.contextual"

    def test_anomaly_labels(self) -> None:
        assert Label.ANOMALY_MISSING_REVISION.value == "anomaly.missing_revision"
        assert Label.ANOMALY_TIMESTAMP_JITTER.value == "anomaly.timestamp_jitter"
        assert Label.ANOMALY_TRUNCATION.value == "anomaly.truncation"
        assert Label.ANOMALY_LARGE_DIFF.value == "anomaly.large_diff"

    def test_assistance_labels(self) -> None:
        assert Label.ASSISTANCE_REVISION_ASSISTED.value == "assistance.revision_assisted"

    def test_is_injection_method(self) -> None:
        assert Label.INJECTION_NAIVE.is_injection() is True
        assert Label.INJECTION_TOPICAL.is_injection() is True
        assert Label.INJECTION_CONTEXTUAL.is_injection() is True
        assert Label.ANOMALY_MISSING_REVISION.is_injection() is False
        assert Label.ASSISTANCE_REVISION_ASSISTED.is_injection() is False

    def test_is_anomaly_method(self) -> None:
        assert Label.ANOMALY_MISSING_REVISION.is_anomaly() is True
        assert Label.ANOMALY_TIMESTAMP_JITTER.is_anomaly() is True
        assert Label.INJECTION_NAIVE.is_anomaly() is False
        assert Label.ASSISTANCE_REVISION_ASSISTED.is_anomaly() is False

    def test_is_assistance_method(self) -> None:
        assert Label.ASSISTANCE_REVISION_ASSISTED.is_assistance() is True
        assert Label.INJECTION_NAIVE.is_assistance() is False
        assert Label.ANOMALY_LARGE_DIFF.is_assistance() is False

    def test_all_labels_match_taxonomy(self) -> None:
        """Verify all labels from LABEL_TAXONOMY.md are present (plus process anomaly labels)."""
        expected_labels = {
            "injection.naive",
            "injection.topical",
            "injection.contextual",
            "anomaly.missing_revision",
            "anomaly.timestamp_jitter",
            "anomaly.truncation",
            "anomaly.large_diff",
            "anomaly.process_violation",
            "anomaly.no_resource_coupling",
            "assistance.revision_assisted",
        }
        actual_labels = {label.value for label in Label}
        assert actual_labels == expected_labels


class TestSeedRevision:
    """Tests for SeedRevision dataclass."""

    def test_creation(self) -> None:
        rev = SeedRevision(
            doc_id="doc_abc123",
            revision_id="rev_xyz789",
            revision_index=0,
            text="Hello world",
            timestamp="2023-01-01T00:00:00+00:00",
            provenance_hash="abc123def456",
        )
        assert rev.doc_id == "doc_abc123"
        assert rev.revision_id == "rev_xyz789"
        assert rev.revision_index == 0
        assert rev.text == "Hello world"

    def test_immutability(self) -> None:
        rev = SeedRevision(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            revision_index=0,
            text="test",
            timestamp=None,
            provenance_hash="hash",
        )
        with pytest.raises(AttributeError):
            rev.text = "changed"  # type: ignore

    def test_serialization(self) -> None:
        rev = SeedRevision(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            revision_index=0,
            text="test",
            timestamp="2023-01-01T00:00:00+00:00",
            provenance_hash="hash",
        )
        data = asdict(rev)
        assert data["doc_id"] == "doc_abc"
        assert data["text"] == "test"


class TestSeedDocument:
    """Tests for SeedDocument dataclass."""

    def test_creation_with_revisions(self) -> None:
        revisions = [
            SeedRevision(
                doc_id="doc_abc",
                revision_id=f"rev_{i}",
                revision_index=i,
                text=f"text {i}",
                timestamp=None,
                provenance_hash=f"hash_{i}",
            )
            for i in range(3)
        ]
        doc = SeedDocument(doc_id="doc_abc", revisions=revisions)
        assert doc.doc_id == "doc_abc"
        assert len(doc.revisions) == 3

    def test_empty_revisions(self) -> None:
        doc = SeedDocument(doc_id="doc_empty", revisions=[])
        assert doc.doc_id == "doc_empty"
        assert len(doc.revisions) == 0


class TestInjectionSpan:
    """Tests for InjectionSpan dataclass."""

    def test_creation_with_injection_label(self) -> None:
        span = InjectionSpan(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            injection_id="inj_123",
            label=Label.INJECTION_CONTEXTUAL,
            injection_level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.LOW,
            span_start_char=10,
            span_end_char=50,
            span_start_sentence=1,
            span_end_sentence=2,
            generator_class="gpt-4o",
            prompt_hash="prompt123",
            rng_seed=42,
            provenance_hash="prov123",
        )
        assert span.injection_level == InjectionLevel.CONTEXTUAL
        assert span.trajectory_state == TrajectoryState.COLD
        assert span.ambiguity_flag == AmbiguityFlag.LOW
        assert span.label == Label.INJECTION_CONTEXTUAL

    def test_creation_with_anomaly_label(self) -> None:
        """Anomaly labels require null injection_level and trajectory_state."""
        span = InjectionSpan(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            injection_id="inj_123",
            label=Label.ANOMALY_LARGE_DIFF,
            injection_level=None,
            trajectory_state=None,
            ambiguity_flag=AmbiguityFlag.MEDIUM,
            span_start_char=0,
            span_end_char=100,
            span_start_sentence=0,
            span_end_sentence=5,
            generator_class="detector",
            prompt_hash="hash",
            rng_seed=0,
            provenance_hash=None,
        )
        assert span.label == Label.ANOMALY_LARGE_DIFF
        assert span.injection_level is None
        assert span.trajectory_state is None

    def test_span_offsets(self) -> None:
        span = InjectionSpan(
            doc_id="doc",
            revision_id="rev",
            injection_id="inj",
            label=Label.INJECTION_NAIVE,
            injection_level=InjectionLevel.NAIVE,
            trajectory_state=TrajectoryState.WARM,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=100,
            span_end_char=200,
            span_start_sentence=5,
            span_end_sentence=10,
            generator_class="test",
            prompt_hash="hash",
            rng_seed=0,
            provenance_hash=None,
        )
        # End should be after start
        assert span.span_end_char > span.span_start_char
        assert span.span_end_sentence >= span.span_start_sentence

    def test_injection_label_requires_injection_level(self) -> None:
        """Injection labels must have injection_level set."""
        with pytest.raises(ValueError, match="injection_level required"):
            InjectionSpan(
                doc_id="doc",
                revision_id="rev",
                injection_id="inj",
                label=Label.INJECTION_NAIVE,
                injection_level=None,  # Invalid: should be set
                trajectory_state=TrajectoryState.COLD,
                ambiguity_flag=AmbiguityFlag.NONE,
                span_start_char=0,
                span_end_char=10,
                span_start_sentence=0,
                span_end_sentence=1,
                generator_class="test",
                prompt_hash="hash",
                rng_seed=0,
                provenance_hash=None,
            )

    def test_injection_label_requires_trajectory_state(self) -> None:
        """Injection labels must have trajectory_state set."""
        with pytest.raises(ValueError, match="trajectory_state required"):
            InjectionSpan(
                doc_id="doc",
                revision_id="rev",
                injection_id="inj",
                label=Label.INJECTION_CONTEXTUAL,
                injection_level=InjectionLevel.CONTEXTUAL,
                trajectory_state=None,  # Invalid: should be set
                ambiguity_flag=AmbiguityFlag.NONE,
                span_start_char=0,
                span_end_char=10,
                span_start_sentence=0,
                span_end_sentence=1,
                generator_class="test",
                prompt_hash="hash",
                rng_seed=0,
                provenance_hash=None,
            )

    def test_anomaly_label_rejects_injection_level(self) -> None:
        """Anomaly labels must have injection_level=None."""
        with pytest.raises(ValueError, match="injection_level must be None"):
            InjectionSpan(
                doc_id="doc",
                revision_id="rev",
                injection_id="inj",
                label=Label.ANOMALY_MISSING_REVISION,
                injection_level=InjectionLevel.NAIVE,  # Invalid: should be None
                trajectory_state=None,
                ambiguity_flag=AmbiguityFlag.NONE,
                span_start_char=0,
                span_end_char=10,
                span_start_sentence=0,
                span_end_sentence=1,
                generator_class="test",
                prompt_hash="hash",
                rng_seed=0,
                provenance_hash=None,
            )

    def test_anomaly_label_rejects_trajectory_state(self) -> None:
        """Anomaly labels must have trajectory_state=None."""
        with pytest.raises(ValueError, match="trajectory_state must be None"):
            InjectionSpan(
                doc_id="doc",
                revision_id="rev",
                injection_id="inj",
                label=Label.ANOMALY_TRUNCATION,
                injection_level=None,
                trajectory_state=TrajectoryState.COLD,  # Invalid: should be None
                ambiguity_flag=AmbiguityFlag.NONE,
                span_start_char=0,
                span_end_char=10,
                span_start_sentence=0,
                span_end_sentence=1,
                generator_class="test",
                prompt_hash="hash",
                rng_seed=0,
                provenance_hash=None,
            )

    def test_assistance_label_requires_null_fields(self) -> None:
        """Assistance labels must have injection_level and trajectory_state=None."""
        span = InjectionSpan(
            doc_id="doc",
            revision_id="rev",
            injection_id="inj",
            label=Label.ASSISTANCE_REVISION_ASSISTED,
            injection_level=None,
            trajectory_state=None,
            ambiguity_flag=AmbiguityFlag.MEDIUM,
            span_start_char=0,
            span_end_char=50,
            span_start_sentence=0,
            span_end_sentence=2,
            generator_class="assistant",
            prompt_hash="hash",
            rng_seed=0,
            provenance_hash=None,
        )
        assert span.label == Label.ASSISTANCE_REVISION_ASSISTED


class TestAugmentedRevision:
    """Tests for AugmentedRevision dataclass."""

    def test_creation(self) -> None:
        span = InjectionSpan(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            injection_id="inj_123",
            label=Label.INJECTION_NAIVE,
            injection_level=InjectionLevel.NAIVE,
            trajectory_state=TrajectoryState.COLD,
            ambiguity_flag=AmbiguityFlag.NONE,
            span_start_char=0,
            span_end_char=10,
            span_start_sentence=0,
            span_end_sentence=1,
            generator_class="test",
            prompt_hash="hash",
            rng_seed=42,
            provenance_hash="prov",
        )
        rev = AugmentedRevision(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            revision_index=0,
            text="Hello world",
            timestamp="2023-01-01T00:00:00+00:00",
            provenance_hash="hash123",
            annotations=[span],
        )
        assert rev.doc_id == "doc_abc"
        assert len(rev.annotations) == 1
        assert rev.annotations[0].injection_id == "inj_123"

    def test_empty_annotations(self) -> None:
        rev = AugmentedRevision(
            doc_id="doc_abc",
            revision_id="rev_xyz",
            revision_index=0,
            text="Clean text",
            timestamp=None,
            provenance_hash="hash",
            annotations=[],
        )
        assert len(rev.annotations) == 0


class TestAugmentedDocument:
    """Tests for AugmentedDocument dataclass."""

    def test_creation(self) -> None:
        rev = AugmentedRevision(
            doc_id="doc_abc",
            revision_id="rev_0",
            revision_index=0,
            text="text",
            timestamp=None,
            provenance_hash="hash",
            annotations=[],
        )
        doc = AugmentedDocument(doc_id="doc_abc", revisions=[rev])
        assert doc.doc_id == "doc_abc"
        assert len(doc.revisions) == 1

    def test_multiple_revisions(self) -> None:
        revisions = [
            AugmentedRevision(
                doc_id="doc_abc",
                revision_id=f"rev_{i}",
                revision_index=i,
                text=f"text {i}",
                timestamp=None,
                provenance_hash=f"hash_{i}",
                annotations=[],
            )
            for i in range(5)
        ]
        doc = AugmentedDocument(doc_id="doc_abc", revisions=revisions)
        assert len(doc.revisions) == 5


class TestRunManifest:
    """Tests for RunManifest dataclass."""

    def test_creation(self) -> None:
        manifest = RunManifest(
            run_id="run_20230101_001",
            created_at="2023-01-01T00:00:00+00:00",
            seed=42,
            code_version="0.1.0",
            checksums={"file1.jsonl": "abc123", "file2.jsonl": "def456"},
            params={"injection_rate": 0.1, "levels": ["naive", "contextual"]},
        )
        assert manifest.run_id == "run_20230101_001"
        assert manifest.seed == 42
        assert "file1.jsonl" in manifest.checksums


class TestSplitSpec:
    """Tests for SplitSpec dataclass."""

    def test_creation(self) -> None:
        spec = SplitSpec(
            train=["doc_1", "doc_2", "doc_3"],
            val=["doc_4"],
            test=["doc_5", "doc_6"],
        )
        assert len(spec.train) == 3
        assert len(spec.val) == 1
        assert len(spec.test) == 2

    def test_all_splits_are_lists(self) -> None:
        spec = SplitSpec(train=[], val=[], test=[])
        assert isinstance(spec.train, list)
        assert isinstance(spec.val, list)
        assert isinstance(spec.test, list)
