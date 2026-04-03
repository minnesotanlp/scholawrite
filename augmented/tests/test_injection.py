# Tests for scholawrite.injection module.
import pytest

from scholawrite.injection import (
    generate_injections,
    select_injection_points,
    create_injection_span,
    InjectionCandidate,
    LEAKAGE_PATTERNS,
    detect_prompt_leakage,
    has_prompt_leakage,
)
from scholawrite.prompts import (
    prompt_hash,
    build_naive_prompt,
    build_topical_prompt,
    build_contextual_prompt,
    NAIVE_PROMPT,
    TOPICAL_PROMPT,
    CONTEXTUAL_PROMPT,
)
from scholawrite.generators import (
    GeneratorClass,
    GeneratorSpec,
    WEAK_GENERATOR,
    MID_GENERATOR,
    STRONG_GENERATOR,
    get_generator_by_class,
)
from scholawrite.schema import (
    AmbiguityFlag,
    InjectionLevel,
    InjectionSpan,
    Label,
    SeedDocument,
    SeedRevision,
    TrajectoryState,
)


class TestPromptHash:
    """Tests for prompt hashing."""

    def test_hash_is_deterministic(self) -> None:
        prompt = "Write a paragraph about AI."
        h1 = prompt_hash(prompt)
        h2 = prompt_hash(prompt)
        assert h1 == h2

    def test_different_prompts_different_hashes(self) -> None:
        h1 = prompt_hash("Write about cats.")
        h2 = prompt_hash("Write about dogs.")
        assert h1 != h2

    def test_hash_is_16_chars(self) -> None:
        h = prompt_hash("Any prompt text here.")
        assert len(h) == 16

    def test_hash_is_hex(self) -> None:
        h = prompt_hash("Test prompt")
        int(h, 16)  # Should not raise


class TestPromptTemplates:
    """Tests for prompt template definitions."""

    def test_naive_prompt_template_exists(self) -> None:
        assert NAIVE_PROMPT.level == "naive"
        assert len(NAIVE_PROMPT.template) > 0

    def test_topical_prompt_template_exists(self) -> None:
        assert TOPICAL_PROMPT.level == "topical"
        assert "{domain}" in TOPICAL_PROMPT.template
        assert "{topic}" in TOPICAL_PROMPT.template

    def test_contextual_prompt_template_exists(self) -> None:
        assert CONTEXTUAL_PROMPT.level == "contextual"
        assert "{section}" in CONTEXTUAL_PROMPT.template
        assert "{preceding}" in CONTEXTUAL_PROMPT.template
        assert "{following}" in CONTEXTUAL_PROMPT.template

    def test_build_naive_prompt(self) -> None:
        prompt = build_naive_prompt()
        assert len(prompt) > 0
        assert "academic" in prompt.lower()

    def test_build_topical_prompt(self) -> None:
        prompt = build_topical_prompt(domain="computer science", topic="machine learning")
        assert "computer science" in prompt
        assert "machine learning" in prompt

    def test_build_contextual_prompt(self) -> None:
        prompt = build_contextual_prompt(
            section="Methods",
            preceding="We used a novel approach.",
            following="The results showed improvement.",
        )
        assert "Methods" in prompt
        assert "novel approach" in prompt
        assert "results showed" in prompt


class TestGeneratorSpec:
    """Tests for generator specifications."""

    def test_weak_generator_exists(self) -> None:
        assert WEAK_GENERATOR.class_label == GeneratorClass.WEAK
        assert WEAK_GENERATOR.name == "weak-baseline"

    def test_mid_generator_exists(self) -> None:
        assert MID_GENERATOR.class_label == GeneratorClass.MID

    def test_strong_generator_exists(self) -> None:
        assert STRONG_GENERATOR.class_label == GeneratorClass.STRONG

    def test_get_generator_by_class(self) -> None:
        weak = get_generator_by_class(GeneratorClass.WEAK)
        assert weak == WEAK_GENERATOR

        strong = get_generator_by_class(GeneratorClass.STRONG)
        assert strong == STRONG_GENERATOR

    def test_generator_spec_serialization(self) -> None:
        spec = STRONG_GENERATOR
        data = spec.to_dict()

        assert data["name"] == spec.name
        assert data["class_label"] == "strong"
        assert "params" in data

        # Roundtrip
        restored = GeneratorSpec.from_dict(data)
        assert restored.name == spec.name
        assert restored.class_label == spec.class_label


class TestSelectInjectionPoints:
    """Tests for injection point selection."""

    @pytest.fixture
    def sample_document(self) -> SeedDocument:
        """Create a sample document with multiple revisions."""
        revisions = [
            SeedRevision(
                doc_id="doc_test",
                revision_id=f"rev_{i}",
                revision_index=i,
                text=f"This is revision {i}. " * 20,  # ~400 chars
                timestamp=f"2023-01-0{i+1}T00:00:00+00:00",
                provenance_hash=f"hash_{i}",
            )
            for i in range(5)
        ]
        return SeedDocument(doc_id="doc_test", revisions=revisions)

    def test_selects_injection_points(self, sample_document: SeedDocument) -> None:
        import random
        rng = random.Random(42)

        candidates = select_injection_points(sample_document, rng, max_per_doc=3)

        assert len(candidates) <= 3
        assert len(candidates) > 0

        for candidate in candidates:
            assert candidate.doc_id == "doc_test"
            assert candidate.revision_index >= 1  # Skips first revision

    def test_deterministic_selection(self, sample_document: SeedDocument) -> None:
        import random

        rng1 = random.Random(42)
        candidates1 = select_injection_points(sample_document, rng1, max_per_doc=3)

        rng2 = random.Random(42)
        candidates2 = select_injection_points(sample_document, rng2, max_per_doc=3)

        assert len(candidates1) == len(candidates2)
        for c1, c2 in zip(candidates1, candidates2):
            assert c1.revision_id == c2.revision_id
            assert c1.char_start == c2.char_start

    def test_respects_max_per_doc(self, sample_document: SeedDocument) -> None:
        import random
        rng = random.Random(42)

        candidates = select_injection_points(sample_document, rng, max_per_doc=1)
        assert len(candidates) <= 1

    def test_skips_short_revisions(self) -> None:
        import random
        rng = random.Random(42)

        short_doc = SeedDocument(
            doc_id="doc_short",
            revisions=[
                SeedRevision(
                    doc_id="doc_short",
                    revision_id="rev_0",
                    revision_index=0,
                    text="Short.",
                    timestamp="2023-01-01T00:00:00+00:00",
                    provenance_hash="hash",
                ),
                SeedRevision(
                    doc_id="doc_short",
                    revision_id="rev_1",
                    revision_index=1,
                    text="Also short.",
                    timestamp="2023-01-02T00:00:00+00:00",
                    provenance_hash="hash2",
                ),
            ],
        )

        candidates = select_injection_points(short_doc, rng)
        assert len(candidates) == 0  # Too short for injection


class TestCreateInjectionSpan:
    """Tests for injection span creation."""

    def test_creates_valid_span(self) -> None:
        candidate = InjectionCandidate(
            doc_id="doc_test",
            revision_id="rev_test",
            revision_index=1,
            sentence_index=2,
            char_start=100,
            char_end=100,
            preceding_text="This is the preceding text.",
            following_text="This is the following text.",
            section_hint="Introduction section",
        )

        span = create_injection_span(
            candidate=candidate,
            level=InjectionLevel.CONTEXTUAL,
            trajectory_state=TrajectoryState.COLD,
            generator=STRONG_GENERATOR,
            rng_seed=42,
            injected_text="This is the injected content.",
            ordinal=0,
        )

        assert isinstance(span, InjectionSpan)
        assert span.doc_id == "doc_test"
        assert span.revision_id == "rev_test"
        assert span.injection_id.startswith("inj_")
        assert span.label == Label.INJECTION_CONTEXTUAL
        assert span.injection_level == InjectionLevel.CONTEXTUAL
        assert span.trajectory_state == TrajectoryState.COLD
        assert span.ambiguity_flag == AmbiguityFlag.NONE
        assert span.span_start_char == 100
        assert span.span_end_char == 100 + len("This is the injected content.")
        assert span.generator_class == "strong-frontier"
        assert span.rng_seed == 42
        assert span.provenance_hash is not None

    def test_creates_correct_label_for_level(self) -> None:
        candidate = InjectionCandidate(
            doc_id="doc",
            revision_id="rev",
            revision_index=1,
            sentence_index=1,
            char_start=0,
            char_end=0,
            preceding_text="",
            following_text="",
            section_hint="",
        )

        # Naive
        span_naive = create_injection_span(
            candidate, InjectionLevel.NAIVE, TrajectoryState.COLD,
            WEAK_GENERATOR, 1, "text", 0
        )
        assert span_naive.label == Label.INJECTION_NAIVE

        # Topical
        span_topical = create_injection_span(
            candidate, InjectionLevel.TOPICAL, TrajectoryState.COLD,
            MID_GENERATOR, 2, "text", 0
        )
        assert span_topical.label == Label.INJECTION_TOPICAL

        # Contextual
        span_contextual = create_injection_span(
            candidate, InjectionLevel.CONTEXTUAL, TrajectoryState.COLD,
            STRONG_GENERATOR, 3, "text", 0
        )
        assert span_contextual.label == Label.INJECTION_CONTEXTUAL


class TestGenerateInjections:
    """Tests for the main generate_injections function."""

    @pytest.fixture
    def sample_documents(self) -> list:
        """Create sample documents for testing."""
        docs = []
        for d in range(2):
            revisions = [
                SeedRevision(
                    doc_id=f"doc_{d}",
                    revision_id=f"rev_{d}_{r}",
                    revision_index=r,
                    text=f"Document {d} revision {r}. This is substantial content for testing. " * 10,
                    timestamp=f"2023-01-0{r+1}T00:00:00+00:00",
                    provenance_hash=f"hash_{d}_{r}",
                )
                for r in range(4)
            ]
            docs.append(SeedDocument(doc_id=f"doc_{d}", revisions=revisions))
        return docs

    def test_generates_injections(self, sample_documents: list) -> None:
        results = generate_injections(
            seed_docs=sample_documents,
            generator=STRONG_GENERATOR,
            rng_seed=42,
            level=InjectionLevel.CONTEXTUAL,
            max_per_doc=2,
        )

        assert len(results) > 0
        for candidate, span in results:
            assert isinstance(candidate, InjectionCandidate)
            assert isinstance(span, InjectionSpan)

    def test_deterministic_generation(self, sample_documents: list) -> None:
        results1 = generate_injections(
            seed_docs=sample_documents,
            generator=STRONG_GENERATOR,
            rng_seed=42,
            level=InjectionLevel.NAIVE,
            max_per_doc=2,
        )

        results2 = generate_injections(
            seed_docs=sample_documents,
            generator=STRONG_GENERATOR,
            rng_seed=42,
            level=InjectionLevel.NAIVE,
            max_per_doc=2,
        )

        assert len(results1) == len(results2)
        for (c1, s1), (c2, s2) in zip(results1, results2):
            assert s1.injection_id == s2.injection_id
            assert s1.rng_seed == s2.rng_seed
            assert s1.provenance_hash == s2.provenance_hash

    def test_different_seeds_different_results(self, sample_documents: list) -> None:
        results1 = generate_injections(
            seed_docs=sample_documents,
            generator=STRONG_GENERATOR,
            rng_seed=42,
            level=InjectionLevel.CONTEXTUAL,
            max_per_doc=2,
        )

        results2 = generate_injections(
            seed_docs=sample_documents,
            generator=STRONG_GENERATOR,
            rng_seed=123,  # Different seed
            level=InjectionLevel.CONTEXTUAL,
            max_per_doc=2,
        )

        # At least some RNG seeds should differ
        seeds1 = {s.rng_seed for _, s in results1}
        seeds2 = {s.rng_seed for _, s in results2}
        assert seeds1 != seeds2

    def test_respects_max_per_doc(self, sample_documents: list) -> None:
        results = generate_injections(
            seed_docs=sample_documents,
            generator=STRONG_GENERATOR,
            rng_seed=42,
            level=InjectionLevel.TOPICAL,
            max_per_doc=1,
        )

        # Count injections per document
        doc_counts = {}
        for _, span in results:
            doc_counts[span.doc_id] = doc_counts.get(span.doc_id, 0) + 1

        for count in doc_counts.values():
            assert count <= 1


class TestLeakagePatterns:
    """Tests for the LEAKAGE_PATTERNS constant."""

    def test_leakage_patterns_exist(self) -> None:
        """Verify LEAKAGE_PATTERNS is defined and non-empty."""
        assert LEAKAGE_PATTERNS is not None
        assert len(LEAKAGE_PATTERNS) > 0

    def test_leakage_patterns_are_valid_regex(self) -> None:
        """Verify all patterns are valid regex."""
        import re
        for pattern in LEAKAGE_PATTERNS:
            # Should not raise
            re.compile(pattern)


class TestDetectPromptLeakage:
    """Tests for the detect_prompt_leakage function."""

    def test_clean_text_returns_empty(self) -> None:
        """Clean academic text should return no patterns."""
        clean_text = (
            "The methodology employed in this study demonstrates "
            "a significant correlation between variables."
        )
        detected = detect_prompt_leakage(clean_text)
        assert len(detected) == 0

    def test_detects_ai_self_identification(self) -> None:
        """Should detect AI self-identification phrases."""
        texts = [
            "As an AI, I cannot provide medical advice.",
            "As a language model, I don't have opinions.",
            "I was trained on data up to 2023.",
            "My training data includes various sources.",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect leakage in: {text}"

    def test_detects_response_openers(self) -> None:
        """Should detect common LLM response opening phrases."""
        texts = [
            "Here is the paragraph you requested.",
            "Here's a summary of the key points.",
            "Certainly! I can help with that.",
            "Sure! Let me explain that for you.",
            "Of course! The answer is straightforward.",
            "Absolutely! Here's what you need to know.",
            "I'd be happy to help with that.",
            "Let me explain the concept.",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect leakage in: {text}"

    def test_detects_role_markers(self) -> None:
        """Should detect chat format role markers."""
        texts = [
            "Assistant: Here is your answer.",
            "Human: Can you help me?",
            "User: Please write a paragraph.",
            "System: You are a helpful assistant.",
            "[Assistant] Let me help you.",
            "[User] What is the meaning of life?",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect role marker in: {text}"

    def test_detects_meta_commentary(self) -> None:
        """Should detect meta-commentary about the text."""
        texts = [
            "The following text provides an overview.",
            "This passage discusses the methodology.",
            "As requested, here is the paragraph.",
            "As you asked, I have summarized the key points.",
            "I've written a comprehensive analysis.",
            "I have created the paragraph below.",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect meta-commentary in: {text}"

    def test_detects_markdown_artifacts(self) -> None:
        """Should detect markdown formatting at text start."""
        texts = [
            "# Introduction to Machine Learning",
            "## Methods and Materials",
            "1. First, we collected data.",
            "- This is a bullet point",
            "* Another bullet style",
            "```python\nprint('hello')\n```",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect markdown in: {text}"

    def test_detects_common_llm_phrases(self) -> None:
        """Should detect common LLM closing/transitional phrases."""
        texts = [
            "In conclusion, the results show significance.",
            "To summarize, we found three key factors.",
            "It's worth noting that the data is limited.",
            "It is important to note the limitations.",
            "I hope this helps with your research.",
            "Let me know if you need more information.",
            "Feel free to ask follow-up questions.",
            "If you have any questions, please ask.",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect LLM phrase in: {text}"

    def test_returns_matched_patterns(self) -> None:
        """Should return the specific patterns that matched."""
        text = "As an AI language model, here is the response."
        detected = detect_prompt_leakage(text)
        assert len(detected) >= 1  # Should match at least one pattern
        # All returned items should be strings (the patterns)
        for pattern in detected:
            assert isinstance(pattern, str)

    def test_case_insensitive_detection(self) -> None:
        """Detection should be case-insensitive for most patterns."""
        texts = [
            "AS AN AI, I cannot help.",
            "as an ai, i cannot help.",
            "As An Ai, I Cannot Help.",
            "HERE IS the paragraph.",
            "here is THE PARAGRAPH.",
        ]
        for text in texts:
            detected = detect_prompt_leakage(text)
            assert len(detected) > 0, f"Should detect regardless of case: {text}"

    def test_multiline_text(self) -> None:
        """Should work with multiline text."""
        text = """
        The study examined multiple factors.

        # Results

        In conclusion, we found significant effects.
        """
        detected = detect_prompt_leakage(text)
        # Should detect at least "in conclusion" (header may not match due to indentation)
        assert len(detected) >= 1


class TestHasPromptLeakage:
    """Tests for the has_prompt_leakage helper function."""

    def test_returns_true_for_leaky_text(self) -> None:
        """Should return True when leakage is detected."""
        assert has_prompt_leakage("As an AI, I cannot help.") is True
        assert has_prompt_leakage("Certainly! Here is the answer.") is True

    def test_returns_false_for_clean_text(self) -> None:
        """Should return False when no leakage is detected."""
        clean_text = (
            "The experimental results demonstrate a statistically "
            "significant correlation between the independent and "
            "dependent variables in our analysis."
        )
        assert has_prompt_leakage(clean_text) is False

    def test_empty_string_is_clean(self) -> None:
        """Empty string should not trigger leakage."""
        assert has_prompt_leakage("") is False

    def test_whitespace_only_is_clean(self) -> None:
        """Whitespace-only string should not trigger leakage."""
        assert has_prompt_leakage("   \n\t  ") is False


class TestLeakageIntegration:
    """Integration tests for leakage detection in the context of injections."""

    def test_generated_placeholder_text_is_clean(self) -> None:
        """Deterministic placeholder text should not contain leakage patterns."""
        from scholawrite.injection import generate_deterministic_placeholder

        for level in [InjectionLevel.NAIVE, InjectionLevel.TOPICAL, InjectionLevel.CONTEXTUAL]:
            for seed in [0, 42, 12345]:
                text = generate_deterministic_placeholder(level, seed)
                detected = detect_prompt_leakage(text)
                assert len(detected) == 0, (
                    f"Placeholder text for level={level}, seed={seed} "
                    f"contains leakage: {detected}"
                )

    def test_leakage_detection_performance(self) -> None:
        """Leakage detection should be reasonably fast for long texts."""
        import time

        # Generate a moderately long text
        long_text = " ".join([
            "The methodology employed in this research demonstrates "
            "a comprehensive approach to analyzing complex systems."
        ] * 100)

        start = time.time()
        for _ in range(100):
            detect_prompt_leakage(long_text)
        elapsed = time.time() - start

        # Should complete 100 iterations in under 1 second
        assert elapsed < 1.0, f"Leakage detection too slow: {elapsed:.2f}s for 100 iterations"

    def test_distinguishes_scholarly_from_llm_text(self) -> None:
        """Should distinguish genuine scholarly text from LLM-generated text."""
        # Genuine scholarly text patterns
        scholarly_texts = [
            "The research methodology employed a mixed-methods approach.",
            "Statistical analysis revealed a significant correlation (p < 0.05).",
            "These findings corroborate previous studies in the field.",
            "The theoretical framework draws upon established principles.",
            "Participants were recruited through convenience sampling.",
        ]

        # LLM-like text patterns
        llm_texts = [
            "Here is a comprehensive analysis of the topic.",
            "Certainly! Let me break this down for you.",
            "As an AI assistant, I'll explain this concept.",
            "I hope this helps with your understanding.",  # Pattern we have
            "## Summary\n\nIn conclusion, the key points are:",
        ]

        for text in scholarly_texts:
            assert not has_prompt_leakage(text), f"Scholarly text flagged as leakage: {text}"

        for text in llm_texts:
            assert has_prompt_leakage(text), f"LLM text not detected: {text}"
