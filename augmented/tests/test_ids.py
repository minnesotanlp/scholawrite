# Tests for scholawrite.ids module.
from scholawrite.ids import (
    make_doc_id,
    make_revision_id,
    make_injection_id,
    DOC_ID_PREFIX,
    REV_ID_PREFIX,
    INJ_ID_PREFIX,
)


class TestMakeDocId:
    """Tests for make_doc_id function."""

    def test_returns_prefixed_id(self) -> None:
        result = make_doc_id("test_source")
        assert result.startswith(DOC_ID_PREFIX)

    def test_consistent_for_same_input(self) -> None:
        id1 = make_doc_id("scholawrite:project:1")
        id2 = make_doc_id("scholawrite:project:1")
        assert id1 == id2

    def test_different_for_different_input(self) -> None:
        id1 = make_doc_id("scholawrite:project:1")
        id2 = make_doc_id("scholawrite:project:2")
        assert id1 != id2

    def test_handles_empty_string(self) -> None:
        result = make_doc_id("")
        assert result.startswith(DOC_ID_PREFIX)
        assert len(result) == len(DOC_ID_PREFIX) + 16

    def test_handles_unicode(self) -> None:
        result = make_doc_id("项目:测试")
        assert result.startswith(DOC_ID_PREFIX)

    def test_handles_special_characters(self) -> None:
        result = make_doc_id("project/with:special@chars!")
        assert result.startswith(DOC_ID_PREFIX)

    def test_id_length_is_consistent(self) -> None:
        # prefix (4) + hash (16) = 20 characters
        ids = [
            make_doc_id("short"),
            make_doc_id("a" * 1000),
            make_doc_id(""),
        ]
        for doc_id in ids:
            assert len(doc_id) == 20


class TestMakeRevisionId:
    """Tests for make_revision_id function."""

    def test_returns_prefixed_id(self) -> None:
        result = make_revision_id("doc_abc123", 0)
        assert result.startswith(REV_ID_PREFIX)

    def test_consistent_for_same_input(self) -> None:
        id1 = make_revision_id("doc_abc", 5)
        id2 = make_revision_id("doc_abc", 5)
        assert id1 == id2

    def test_different_for_different_doc_id(self) -> None:
        id1 = make_revision_id("doc_abc", 0)
        id2 = make_revision_id("doc_xyz", 0)
        assert id1 != id2

    def test_different_for_different_index(self) -> None:
        id1 = make_revision_id("doc_abc", 0)
        id2 = make_revision_id("doc_abc", 1)
        assert id1 != id2

    def test_handles_large_index(self) -> None:
        result = make_revision_id("doc_abc", 999999)
        assert result.startswith(REV_ID_PREFIX)

    def test_handles_negative_index(self) -> None:
        # Note: negative indices are technically invalid but shouldn't crash
        result = make_revision_id("doc_abc", -1)
        assert result.startswith(REV_ID_PREFIX)


class TestMakeInjectionId:
    """Tests for make_injection_id function."""

    def test_returns_prefixed_id(self) -> None:
        result = make_injection_id("doc_abc", "rev_xyz", 0)
        assert result.startswith(INJ_ID_PREFIX)

    def test_consistent_for_same_input(self) -> None:
        id1 = make_injection_id("doc_abc", "rev_xyz", 3)
        id2 = make_injection_id("doc_abc", "rev_xyz", 3)
        assert id1 == id2

    def test_different_for_different_ordinal(self) -> None:
        id1 = make_injection_id("doc_abc", "rev_xyz", 0)
        id2 = make_injection_id("doc_abc", "rev_xyz", 1)
        assert id1 != id2

    def test_different_for_different_revision(self) -> None:
        id1 = make_injection_id("doc_abc", "rev_xyz", 0)
        id2 = make_injection_id("doc_abc", "rev_123", 0)
        assert id1 != id2


class TestIdUniqueness:
    """Tests for uniqueness across ID types."""

    def test_different_prefixes(self) -> None:
        """IDs with same input but different types should differ."""
        doc_id = make_doc_id("test")
        # These use different inputs but verify prefixes are distinct
        assert doc_id.startswith("doc_")
        rev_id = make_revision_id(doc_id, 0)
        assert rev_id.startswith("rev_")
        inj_id = make_injection_id(doc_id, rev_id, 0)
        assert inj_id.startswith("inj_")

    def test_id_components_are_hex(self) -> None:
        """Hash portion should be valid hex."""
        doc_id = make_doc_id("test")
        hash_part = doc_id[len(DOC_ID_PREFIX):]
        # Should be valid hex
        int(hash_part, 16)  # Will raise if not valid hex
