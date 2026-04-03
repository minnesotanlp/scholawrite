# Tests for scholawrite.text module.
from scholawrite.text import (
    normalize_text,
    split_sentences,
    char_offsets,
    compute_provenance_hash,
)


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_strips_whitespace(self) -> None:
        assert normalize_text("  hello world  ") == "hello world"

    def test_normalizes_line_endings(self) -> None:
        assert normalize_text("line1\r\nline2\rline3") == "line1\nline2\nline3"

    def test_collapses_multiple_blank_lines(self) -> None:
        text = "para1\n\n\n\npara2"
        result = normalize_text(text)
        assert result == "para1\n\npara2"

    def test_handles_empty_string(self) -> None:
        assert normalize_text("") == ""

    def test_handles_none_like_empty(self) -> None:
        # normalize_text expects string, but should handle gracefully
        assert normalize_text("") == ""

    def test_unicode_normalization(self) -> None:
        # Combining characters should be normalized to NFC
        # é as e + combining accent vs precomposed é
        text_decomposed = "caf\u0065\u0301"  # e + combining acute
        text_composed = "café"  # precomposed é
        result = normalize_text(text_decomposed)
        # After NFC normalization, both should match
        assert normalize_text(text_composed) == result


class TestSplitSentences:
    """Tests for split_sentences function."""

    def test_splits_simple_sentences(self) -> None:
        text = "Hello world. This is a test. Another sentence here."
        result = split_sentences(text)
        assert len(result) == 3
        assert result[0] == "Hello world."
        assert result[1] == "This is a test."
        assert result[2] == "Another sentence here."

    def test_handles_question_marks(self) -> None:
        text = "What is this? It is a test."
        result = split_sentences(text)
        assert len(result) == 2

    def test_handles_exclamation_marks(self) -> None:
        text = "Wow! That is amazing."
        result = split_sentences(text)
        assert len(result) == 2

    def test_returns_empty_for_empty_input(self) -> None:
        assert split_sentences("") == []

    def test_returns_single_sentence_without_terminator(self) -> None:
        result = split_sentences("No terminator here")
        assert result == ["No terminator here"]

    def test_handles_abbreviations_imperfectly(self) -> None:
        # Note: simple heuristic may split on abbreviations
        # This test documents current behavior
        text = "Dr. Smith went home. He was tired."
        result = split_sentences(text)
        # Current heuristic splits after . followed by capital
        assert len(result) >= 2


class TestCharOffsets:
    """Tests for char_offsets function."""

    def test_computes_correct_offsets(self) -> None:
        text = "Hello world. This is a test."
        sentences = ["Hello world.", "This is a test."]
        offsets = char_offsets(text, sentences)

        assert len(offsets) == 2
        assert offsets[0] == (0, 12)  # "Hello world."
        assert offsets[1] == (13, 28)  # "This is a test."

    def test_returns_empty_for_empty_sentences(self) -> None:
        assert char_offsets("some text", []) == []

    def test_offsets_allow_text_extraction(self) -> None:
        text = "First sentence. Second sentence."
        sentences = ["First sentence.", "Second sentence."]
        offsets = char_offsets(text, sentences)

        for i, (start, end) in enumerate(offsets):
            assert text[start:end] == sentences[i]


class TestComputeProvenanceHash:
    """Tests for compute_provenance_hash function."""

    def test_returns_consistent_hash(self) -> None:
        text = "Hello world"
        hash1 = compute_provenance_hash(text)
        hash2 = compute_provenance_hash(text)
        assert hash1 == hash2

    def test_different_text_different_hash(self) -> None:
        hash1 = compute_provenance_hash("Hello")
        hash2 = compute_provenance_hash("World")
        assert hash1 != hash2

    def test_hash_is_32_chars(self) -> None:
        result = compute_provenance_hash("test")
        assert len(result) == 32

    def test_normalizes_before_hashing(self) -> None:
        # Same content with different whitespace should hash the same
        hash1 = compute_provenance_hash("  hello  ")
        hash2 = compute_provenance_hash("hello")
        assert hash1 == hash2

    def test_handles_empty_string(self) -> None:
        result = compute_provenance_hash("")
        assert len(result) == 32

    def test_handles_unicode(self) -> None:
        result = compute_provenance_hash("こんにちは世界")
        assert len(result) == 32

    def test_handles_very_long_text(self) -> None:
        long_text = "a" * 100000
        result = compute_provenance_hash(long_text)
        assert len(result) == 32


class TestEdgeCases:
    """Edge case tests for text module."""

    def test_normalize_text_with_only_whitespace(self) -> None:
        assert normalize_text("   \n\n\t  ") == ""

    def test_normalize_text_with_mixed_line_endings(self) -> None:
        text = "line1\r\nline2\rline3\nline4"
        result = normalize_text(text)
        assert "\r" not in result
        assert result.count("\n") == 3

    def test_split_sentences_with_multiple_punctuation(self) -> None:
        text = "What?! Really!! Yes..."
        result = split_sentences(text)
        assert len(result) >= 1

    def test_char_offsets_with_unicode(self) -> None:
        text = "Hello 世界. Goodbye 世界."
        sentences = ["Hello 世界.", "Goodbye 世界."]
        offsets = char_offsets(text, sentences)
        assert len(offsets) == 2
        # Verify we can extract text using offsets
        for i, (start, end) in enumerate(offsets):
            assert text[start:end] == sentences[i]
