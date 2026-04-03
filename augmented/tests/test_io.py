# Tests for scholawrite.io module.
from pathlib import Path

import pytest

from scholawrite.io import load_seed, load_seed_split, load_parquet_dir
from scholawrite.schema import SeedDocument, SeedRevision


# Path to test fixtures
SEED_DATA_PATH = Path("data/seed/raw/hf_scholawrite")


class TestLoadParquetDir:
    """Tests for load_parquet_dir function."""

    def test_raises_for_nonexistent_path(self) -> None:
        with pytest.raises(FileNotFoundError, match="does not exist"):
            load_parquet_dir("/nonexistent/path")

    def test_raises_for_empty_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No parquet files found"):
            load_parquet_dir(tmp_path)

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_loads_parquet_from_nested_directory(self) -> None:
        df = load_parquet_dir(SEED_DATA_PATH)
        assert len(df) > 0
        assert "project" in df.columns
        assert "timestamp" in df.columns
        assert "after text" in df.columns


class TestLoadSeedSplit:
    """Tests for load_seed_split function."""

    def test_raises_for_invalid_split(self) -> None:
        with pytest.raises(ValueError, match="Invalid split"):
            load_seed_split(SEED_DATA_PATH, split="invalid_split")

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_loads_test_small_split(self) -> None:
        docs = load_seed_split(SEED_DATA_PATH, split="test_small")

        # test_small should have 5 documents
        assert len(docs) == 5

        # Each document should be a SeedDocument
        for doc in docs:
            assert isinstance(doc, SeedDocument)
            assert doc.doc_id.startswith("doc_")
            assert len(doc.revisions) > 0

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_revisions_are_properly_structured(self) -> None:
        docs = load_seed_split(SEED_DATA_PATH, split="test_small")
        doc = docs[0]

        for i, rev in enumerate(doc.revisions):
            assert isinstance(rev, SeedRevision)
            assert rev.doc_id == doc.doc_id
            assert rev.revision_id.startswith("rev_")
            assert rev.revision_index == i
            assert rev.timestamp is not None  # All should have timestamps
            assert rev.provenance_hash is not None

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_revisions_sorted_by_timestamp(self) -> None:
        docs = load_seed_split(SEED_DATA_PATH, split="test_small")

        for doc in docs:
            timestamps = [
                rev.timestamp for rev in doc.revisions if rev.timestamp
            ]
            # Timestamps should be in ascending order
            assert timestamps == sorted(timestamps)

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_documents_sorted_by_doc_id(self) -> None:
        docs = load_seed_split(SEED_DATA_PATH, split="test_small")
        doc_ids = [doc.doc_id for doc in docs]
        assert doc_ids == sorted(doc_ids)

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_doc_ids_are_stable(self) -> None:
        """Loading the same data twice should produce the same doc IDs."""
        docs1 = load_seed_split(SEED_DATA_PATH, split="test_small")
        docs2 = load_seed_split(SEED_DATA_PATH, split="test_small")

        assert len(docs1) == len(docs2)
        for d1, d2 in zip(docs1, docs2):
            assert d1.doc_id == d2.doc_id

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_revision_ids_are_stable(self) -> None:
        """Loading the same data twice should produce the same revision IDs."""
        docs1 = load_seed_split(SEED_DATA_PATH, split="test_small")
        docs2 = load_seed_split(SEED_DATA_PATH, split="test_small")

        for d1, d2 in zip(docs1, docs2):
            assert len(d1.revisions) == len(d2.revisions)
            for r1, r2 in zip(d1.revisions, d2.revisions):
                assert r1.revision_id == r2.revision_id


class TestLoadSeed:
    """Tests for load_seed function (loads all splits)."""

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_loads_all_parquet_files(self) -> None:
        docs = load_seed(SEED_DATA_PATH)

        # Should have at least the 5 documents from test_small
        assert len(docs) >= 5

        for doc in docs:
            assert isinstance(doc, SeedDocument)
            assert len(doc.revisions) > 0


class TestBuildDocumentsEdgeCases:
    """Tests for edge cases in document building."""

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_handles_empty_text_revisions(self) -> None:
        """Some revisions may have empty text; should not crash."""
        docs = load_seed_split(SEED_DATA_PATH, split="test_small")
        # Check that empty texts are handled gracefully
        for doc in docs:
            for rev in doc.revisions:
                assert rev.text is not None  # Should never be None
                assert isinstance(rev.text, str)

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_provenance_hash_is_deterministic(self) -> None:
        """Provenance hash should be consistent for same content."""
        docs1 = load_seed_split(SEED_DATA_PATH, split="test_small")
        docs2 = load_seed_split(SEED_DATA_PATH, split="test_small")

        for d1, d2 in zip(docs1, docs2):
            for r1, r2 in zip(d1.revisions, d2.revisions):
                assert r1.provenance_hash == r2.provenance_hash


class TestWriteReadJsonl:
    """Tests for write_documents_jsonl and read_documents_jsonl functions."""

    @pytest.mark.skipif(
        not SEED_DATA_PATH.exists(),
        reason="Seed data not available"
    )
    def test_roundtrip(self, tmp_path: Path) -> None:
        """Write and read documents should preserve all data."""
        from scholawrite.io import write_documents_jsonl, read_documents_jsonl

        # Load original documents
        original = load_seed_split(SEED_DATA_PATH, split="test_small")

        # Write to JSONL
        output_file = tmp_path / "test.jsonl"
        write_documents_jsonl(original, output_file)

        # Read back
        loaded = read_documents_jsonl(output_file)

        # Compare
        assert len(loaded) == len(original)
        for orig_doc, loaded_doc in zip(original, loaded):
            assert loaded_doc.doc_id == orig_doc.doc_id
            assert len(loaded_doc.revisions) == len(orig_doc.revisions)

            for orig_rev, loaded_rev in zip(orig_doc.revisions, loaded_doc.revisions):
                assert loaded_rev.revision_id == orig_rev.revision_id
                assert loaded_rev.text == orig_rev.text
                assert loaded_rev.timestamp == orig_rev.timestamp
                assert loaded_rev.provenance_hash == orig_rev.provenance_hash

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_documents_jsonl should create parent directories."""
        from scholawrite.io import write_documents_jsonl

        nested_path = tmp_path / "a" / "b" / "c" / "test.jsonl"
        write_documents_jsonl([], nested_path)
        assert nested_path.exists()

    def test_read_raises_for_missing_file(self, tmp_path: Path) -> None:
        """read_documents_jsonl should raise for missing file."""
        from scholawrite.io import read_documents_jsonl

        with pytest.raises(FileNotFoundError):
            read_documents_jsonl(tmp_path / "nonexistent.jsonl")


# Path to test fixtures
FIXTURES_PATH = Path(__file__).parent / "fixtures"


class TestGoldenFileSeedDocuments:
    """Golden-file tests for SeedDocument serialization determinism."""

    @pytest.mark.skipif(
        not (FIXTURES_PATH / "seed_document_golden.jsonl").exists(),
        reason="Golden fixture not available"
    )
    def test_load_golden_fixture(self) -> None:
        """Verify golden fixture can be loaded correctly."""
        from scholawrite.io import read_documents_jsonl

        golden_path = FIXTURES_PATH / "seed_document_golden.jsonl"
        docs = read_documents_jsonl(golden_path)

        assert len(docs) == 2
        assert docs[0].doc_id == "doc_0001000000000000"
        assert len(docs[0].revisions) == 2
        assert docs[1].doc_id == "doc_0002000000000000"
        assert len(docs[1].revisions) == 1

    @pytest.mark.skipif(
        not (FIXTURES_PATH / "seed_document_golden.jsonl").exists(),
        reason="Golden fixture not available"
    )
    def test_roundtrip_matches_golden(self, tmp_path: Path) -> None:
        """Write and read should exactly match golden fixture."""
        from scholawrite.io import read_documents_jsonl, write_documents_jsonl

        golden_path = FIXTURES_PATH / "seed_document_golden.jsonl"
        original = read_documents_jsonl(golden_path)

        # Write to temp file
        output_path = tmp_path / "roundtrip.jsonl"
        write_documents_jsonl(original, output_path)

        # Read back and compare
        loaded = read_documents_jsonl(output_path)

        assert len(loaded) == len(original)
        for orig, load in zip(original, loaded):
            assert load.doc_id == orig.doc_id
            for r1, r2 in zip(orig.revisions, load.revisions):
                assert r1.revision_id == r2.revision_id
                assert r1.text == r2.text
                assert r1.timestamp == r2.timestamp
                assert r1.provenance_hash == r2.provenance_hash


class TestGoldenFileAugmentedDocuments:
    """Golden-file tests for AugmentedDocument serialization determinism."""

    @pytest.mark.skipif(
        not (FIXTURES_PATH / "augmented_document_golden.jsonl").exists(),
        reason="Golden fixture not available"
    )
    def test_load_golden_fixture(self) -> None:
        """Verify golden fixture can be loaded correctly."""
        from scholawrite.io import read_augmented_jsonl
        from scholawrite.schema import (
            AugmentedDocument,
            AugmentedRevision,
            InjectionSpan,
            Label,
            InjectionLevel,
            TrajectoryState,
            AmbiguityFlag,
        )

        golden_path = FIXTURES_PATH / "augmented_document_golden.jsonl"
        docs = read_augmented_jsonl(golden_path)

        assert len(docs) == 2

        # First document: injection label
        doc1 = docs[0]
        assert isinstance(doc1, AugmentedDocument)
        assert doc1.doc_id == "doc_aug_001"
        assert len(doc1.revisions) == 2

        rev1 = doc1.revisions[1]
        assert isinstance(rev1, AugmentedRevision)
        assert len(rev1.annotations) == 1

        ann1 = rev1.annotations[0]
        assert isinstance(ann1, InjectionSpan)
        assert ann1.label == Label.INJECTION_CONTEXTUAL
        assert ann1.injection_level == InjectionLevel.CONTEXTUAL
        assert ann1.trajectory_state == TrajectoryState.COLD
        assert ann1.ambiguity_flag == AmbiguityFlag.NONE

        # Second document: anomaly label
        doc2 = docs[1]
        assert doc2.doc_id == "doc_aug_002"
        ann2 = doc2.revisions[0].annotations[0]
        assert ann2.label == Label.ANOMALY_LARGE_DIFF
        assert ann2.injection_level is None
        assert ann2.trajectory_state is None
        assert ann2.ambiguity_flag == AmbiguityFlag.MEDIUM

    @pytest.mark.skipif(
        not (FIXTURES_PATH / "augmented_document_golden.jsonl").exists(),
        reason="Golden fixture not available"
    )
    def test_roundtrip_preserves_enums(self, tmp_path: Path) -> None:
        """Write and read should preserve enum types correctly."""
        from scholawrite.io import read_augmented_jsonl, write_augmented_jsonl
        from scholawrite.schema import Label, InjectionLevel, TrajectoryState, AmbiguityFlag

        golden_path = FIXTURES_PATH / "augmented_document_golden.jsonl"
        original = read_augmented_jsonl(golden_path)

        # Write to temp file
        output_path = tmp_path / "roundtrip.jsonl"
        write_augmented_jsonl(original, output_path)

        # Read back
        loaded = read_augmented_jsonl(output_path)

        assert len(loaded) == len(original)
        for orig_doc, load_doc in zip(original, loaded):
            assert load_doc.doc_id == orig_doc.doc_id
            for orig_rev, load_rev in zip(orig_doc.revisions, load_doc.revisions):
                assert len(load_rev.annotations) == len(orig_rev.annotations)
                for orig_ann, load_ann in zip(orig_rev.annotations, load_rev.annotations):
                    # Verify enums are preserved as enum types
                    assert isinstance(load_ann.label, Label)
                    assert load_ann.label == orig_ann.label

                    if orig_ann.injection_level is not None:
                        assert isinstance(load_ann.injection_level, InjectionLevel)
                        assert load_ann.injection_level == orig_ann.injection_level
                    else:
                        assert load_ann.injection_level is None

                    if orig_ann.trajectory_state is not None:
                        assert isinstance(load_ann.trajectory_state, TrajectoryState)
                        assert load_ann.trajectory_state == orig_ann.trajectory_state
                    else:
                        assert load_ann.trajectory_state is None

                    assert isinstance(load_ann.ambiguity_flag, AmbiguityFlag)
                    assert load_ann.ambiguity_flag == orig_ann.ambiguity_flag

    def test_write_augmented_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_augmented_jsonl should create parent directories."""
        from scholawrite.io import write_augmented_jsonl

        nested_path = tmp_path / "x" / "y" / "z" / "test.jsonl"
        write_augmented_jsonl([], nested_path)
        assert nested_path.exists()

    def test_read_augmented_raises_for_missing_file(self, tmp_path: Path) -> None:
        """read_augmented_jsonl should raise for missing file."""
        from scholawrite.io import read_augmented_jsonl

        with pytest.raises(FileNotFoundError):
            read_augmented_jsonl(tmp_path / "nonexistent.jsonl")
