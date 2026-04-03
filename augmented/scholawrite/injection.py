"""Injection point detection, placeholder generation, and span creation.

Handles:
- Conceptual rupture detection (attention-shift points in text)
- Injection point selection from revision histories
- Deterministic placeholder generation (for tests/fallbacks)
- Injection span creation with metadata
- Prompt leakage detection

Two generation paths exist:
1. generate_deterministic_placeholder() - Fast, reproducible, for tests/fallbacks
2. agentic.run_causal_agentic_loop() - LLM-powered, contextual, for production

Use deterministic placeholders when:
- Writing tests that need reproducible outputs
- LLM API is unavailable (fallback)
- Rapid iteration during development
- Baseline comparisons in evaluation

DOES NOT contain:
- LLM orchestration -> lives in agentic.py
- Label parsing -> lives in labels.py
- Metric computation -> lives in metrics.py
"""
from __future__ import annotations

import re
import random
from dataclasses import dataclass
from typing import List, Tuple
from .schema import SeedDocument, InjectionSpan, InjectionLevel, TrajectoryState, AmbiguityFlag, Label
from .config import get_leakage_patterns, get_placeholder_text

__all__ = [
    "detect_conceptual_ruptures", "select_injection_points",
    "generate_deterministic_placeholder", "create_injection_span",
    "generate_injections", "InjectionCandidate",
    "LEAKAGE_PATTERNS", "detect_prompt_leakage", "has_prompt_leakage",
    # Deprecated alias for backwards compatibility
    "generate_placeholder_text",
]


# Load leakage patterns from config (lazy-loaded and cached)
def _get_leakage_patterns() -> List[str]:
    """Get leakage patterns, loading from config on first access."""
    return get_leakage_patterns()


# For backwards compatibility, expose as module-level variable
LEAKAGE_PATTERNS = property(lambda self: _get_leakage_patterns())


class _LeakagePatternProxy:
    """Proxy to lazily load leakage patterns from config."""
    def __iter__(self):
        return iter(_get_leakage_patterns())

    def __len__(self):
        return len(_get_leakage_patterns())

    def __getitem__(self, idx):
        return _get_leakage_patterns()[idx]


LEAKAGE_PATTERNS = _LeakagePatternProxy()


def detect_prompt_leakage(text: str) -> List[str]:
    """Detect LLM artifact patterns in text. Returns matched pattern strings."""
    detected = []
    for pattern in LEAKAGE_PATTERNS:
        if re.search(pattern, text, re.MULTILINE):
            detected.append(pattern)
    return detected


def has_prompt_leakage(text: str) -> bool:
    """Check if text contains any prompt leakage patterns."""
    return len(detect_prompt_leakage(text)) > 0


@dataclass
class InjectionCandidate:
    """A candidate location for injection with surrounding context."""
    doc_id: str
    revision_id: str
    revision_index: int
    sentence_index: int
    char_start: int
    char_end: int
    preceding_text: str
    following_text: str
    section_hint: str


def detect_conceptual_ruptures(text: str, window_size: int = 50) -> List[int]:
    """Find attention-shift points based on lexical density shifts or discourse markers."""
    words = text.split()
    if len(words) < window_size * 2:
        return [len(text) // 2]

    ruptures = []
    for i in range(window_size, len(words) - window_size, window_size // 2):
        window_before = words[i-window_size:i]
        window_after = words[i:i+window_size]

        rare_b = sum(1 for w in window_before if len(w) > 8)
        rare_a = sum(1 for w in window_after if len(w) > 8)
        shift = abs(rare_a - rare_b) / window_size

        marker_pattern = r"\b(" + "|".join([
            "however", "conversely", "nevertheless", "nonetheless", "yet", "still",
            "on the contrary", "in contrast", "whereas", "while", "although", "though",
            "despite", "notwithstanding", "alternatively", "instead", "rather",
            "consequently", "therefore", "thus", "hence", "accordingly", "as a result",
            "for this reason", "thereby", "subsequently", "in turn",
            "furthermore", "moreover", "additionally", "besides", "likewise", "similarly",
            "in addition", "also", "equally", "correspondingly",
            "admittedly", "granted", "of course", "certainly", "indeed", "naturally",
            "for example", "for instance", "specifically", "particularly", "notably",
            "in particular", "such as", "including",
            "firstly", "secondly", "finally", "subsequently", "meanwhile", "initially",
            "ultimately", "in summary", "in conclusion", "to summarize",
            "arguably", "presumably", "apparently", "seemingly", "ostensibly",
        ]) + r")\b"
        transition_cluster = len(re.findall(marker_pattern, " ".join(words[i:i+15]), re.IGNORECASE))

        if shift > 0.28 or transition_cluster >= 1:
            char_pos = len(" ".join(words[:i])) + 1
            ruptures.append(char_pos)

    return sorted(list(set(ruptures))) if ruptures else [len(text) // 2]

def select_injection_points(doc: SeedDocument, rng: random.Random, max_per_doc: int = 2) -> List[InjectionCandidate]:
    """Select plausible injection points from revisions after the first."""
    if not doc.revisions or len(doc.revisions) < 2:
        return []

    candidates: List[InjectionCandidate] = []

    for rev in doc.revisions[1:]:
        text = rev.text
        if len(text.split()) < 50:
            continue

        rupture_points = detect_conceptual_ruptures(text)
        for char_pos in rupture_points:
            preceding = text[max(0, char_pos - 200):char_pos]
            following = text[char_pos:char_pos + 200]
            candidates.append(InjectionCandidate(
                doc_id=doc.doc_id,
                revision_id=rev.revision_id,
                revision_index=rev.revision_index,
                sentence_index=0,
                char_start=char_pos,
                char_end=char_pos,
                preceding_text=preceding,
                following_text=following,
                section_hint="",
            ))

    if not candidates:
        return []
    return rng.sample(candidates, min(len(candidates), max_per_doc))

def generate_deterministic_placeholder(level: InjectionLevel, seed: int) -> str:
    """Generate deterministic scholarly placeholder text for testing/fallbacks.

    This function generates reproducible, template-based text for:
    - Deterministic test fixtures (enables reproducible testing)
    - Fallback content when LLM generation is unavailable
    - Basic pipeline runs without LLM API access

    For production augmented builds, use the agentic loop in agentic.py which
    generates contextual, LLM-powered injections.

    Text components are loaded from configs/placeholder_text.json.

    Args:
        level: Injection level (NAIVE, TOPICAL, CONTEXTUAL) - affects text selection.
        seed: Random seed for reproducible text generation.

    Returns:
        Deterministic placeholder text suitable for the injection level.
    """
    rng = random.Random(seed)
    text_data = get_placeholder_text()

    intros = text_data.get("intros", ["This empirical investigation demonstrates"])
    bodies = text_data.get("bodies", ["that the underlying assumptions remain foundational."])
    conclusions = text_data.get("conclusions", ["Consequently, subsequent research must address these gaps."])

    sentences = [rng.choice(intros) + " " + rng.choice(bodies), rng.choice(conclusions)]
    return " ".join(sentences)


# Deprecated alias for backwards compatibility
def generate_placeholder_text(level: InjectionLevel, seed: int) -> str:
    """Deprecated: Use generate_deterministic_placeholder instead."""
    return generate_deterministic_placeholder(level, seed)


def create_injection_span(
    candidate: "InjectionCandidate",
    level: InjectionLevel,
    trajectory_state: TrajectoryState,
    generator: "GeneratorSpec",
    rng_seed: int,
    injected_text: str,
    ordinal: int,
) -> InjectionSpan:
    """Create an injection span from a candidate location."""
    from .text import compute_provenance_hash
    from .ids import make_injection_id
    from .prompts import prompt_hash, build_contextual_prompt

    label_map = {
        InjectionLevel.NAIVE: Label.INJECTION_NAIVE,
        InjectionLevel.TOPICAL: Label.INJECTION_TOPICAL,
        InjectionLevel.CONTEXTUAL: Label.INJECTION_CONTEXTUAL,
    }
    prompt = build_contextual_prompt(
        candidate.section_hint, candidate.preceding_text, candidate.following_text
    )
    p_hash = prompt_hash(prompt)

    return InjectionSpan(
        doc_id=candidate.doc_id,
        revision_id=candidate.revision_id,
        injection_id=make_injection_id(candidate.doc_id, candidate.revision_id, ordinal),
        injection_level=level,
        trajectory_state=trajectory_state,
        ambiguity_flag=AmbiguityFlag.NONE,
        span_start_char=candidate.char_start,
        span_end_char=candidate.char_start + len(injected_text),
        span_start_sentence=candidate.sentence_index,
        span_end_sentence=candidate.sentence_index,
        generator_class=generator.name,
        prompt_hash=p_hash,
        rng_seed=rng_seed,
        provenance_hash=compute_provenance_hash(injected_text),
        label=label_map[level],
        causal_trace=[],
    )


def generate_injections(
    seed_docs: List[SeedDocument],
    generator: "GeneratorSpec",
    rng_seed: int,
    level: InjectionLevel,
    max_per_doc: int = 2,
) -> List[Tuple[InjectionCandidate, InjectionSpan]]:
    """Generate injection candidates and spans for a set of documents."""
    rng = random.Random(rng_seed)
    results = []

    for doc in seed_docs:
        if not doc.revisions or len(doc.revisions) < 2:
            continue

        candidates = select_injection_points(doc, rng, max_per_doc)
        for ordinal, candidate in enumerate(candidates):
            span_rng_seed = rng.randint(0, 100000)
            injected_text = generate_deterministic_placeholder(level, span_rng_seed)
            span = create_injection_span(
                candidate=candidate,
                level=level,
                trajectory_state=TrajectoryState.COLD,
                generator=generator,
                rng_seed=span_rng_seed,
                injected_text=injected_text,
                ordinal=ordinal,
            )
            results.append((candidate, span))

    return results


def _create_injection_span_simple(
    doc_id: str,
    rev_id: str,
    char_start: int,
    level: InjectionLevel,
    text: str,
    ordinal: int,
    generator_class: str = "placeholder"
) -> InjectionSpan:
    """Create a simple injection span without full metadata."""
    from .text import compute_provenance_hash

    return InjectionSpan(
        doc_id=doc_id, revision_id=rev_id, injection_id=f"init_{ordinal}_{doc_id[:4]}",
        injection_level=level, trajectory_state=TrajectoryState.COLD,
        ambiguity_flag=AmbiguityFlag.NONE, span_start_char=char_start,
        span_end_char=char_start + len(text), span_start_sentence=0, span_end_sentence=0,
        generator_class=generator_class, prompt_hash="seed", rng_seed=random.randint(0, 10000),
        provenance_hash=compute_provenance_hash(text),
        label=Label.INJECTION_TOPICAL if level == InjectionLevel.TOPICAL else Label.INJECTION_CONTEXTUAL,
        causal_trace=[]
    )


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .generators import GeneratorSpec
