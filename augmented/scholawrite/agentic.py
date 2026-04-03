"""Agentic loop orchestration for LLM-POWERED GENERATION.

Orchestrates:
- AAA (Attention-Allocation-Action) loop execution
- Cognitive state management and resource tracking
- LLM-based contextual injection generation
- Causal trace recording for forensic validation

This is the production path for generating high-fidelity, contextually
appropriate injections that simulate human writing processes.

For deterministic placeholder text (testing/fallbacks), use injection.py.

DOES NOT contain:
- Placeholder generation -> lives in injection.py
- Label parsing -> lives in labels.py
- Metric computation -> lives in metrics.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .schema import DocumentProfile, CausalEvent, CognitiveState, GenerationMetadata, ResourceAllocation
from .embodied import EmbodiedScholar
from .openrouter import OpenRouterClient, OpenRouterError
from .baselines import _compression_discontinuity
from .causal_core import IrreversibleProcessEngine, LexicalIntention
from .ids import make_causal_injection_id

__all__ = ["run_causal_agentic_loop", "load_meta_commentary_config", "ContentGenerationError"]


class ContentGenerationError(Exception):
    """Raised when content generation fails after all retries."""


# Cached config
_config_cache: Optional[dict] = None
# Path: augmented/scholawrite/agentic.py -> augmented/configs/
_config_path = Path(__file__).parent.parent / "configs" / "meta_commentary_patterns.json"


def load_meta_commentary_config(config_path: Optional[Path] = None) -> dict:
    """Load meta-commentary patterns from JSON config file.

    Args:
        config_path: Path to config file. Uses default if not provided.

    Returns:
        Parsed config dictionary with patterns and settings.
    """
    global _config_cache

    path = config_path or _config_path
    if _config_cache is None or config_path is not None:
        if not path.exists():
            # Return minimal defaults if config missing
            return {
                "prefix_patterns": [r'^Here is .*?:?\s*\n*', r'^Here\'s .*?:?\s*\n*'],
                "suffix_patterns": [],
                "wrapper_removal": {},
                "quality_indicators": {"min_length_chars": 50, "min_words": 10}
            }
        with open(path, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)

    return _config_cache


def _strip_meta_commentary(text: str, config: Optional[dict] = None) -> str:
    """Remove LLM meta-commentary from text using configurable patterns.

    Args:
        text: Raw text that may contain meta-commentary.
        config: Pattern config dict. Loads from file if not provided.

    Returns:
        Cleaned text with meta-commentary removed.
    """
    if not text:
        return text

    cfg = config or load_meta_commentary_config()
    result = text.strip()

    # Apply prefix patterns
    for pattern in cfg.get("prefix_patterns", []):
        try:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE)
        except re.error:
            continue  # Skip invalid patterns

    # Apply suffix patterns
    for pattern in cfg.get("suffix_patterns", []):
        try:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE)
        except re.error:
            continue

    # Apply wrapper removal
    wrappers = cfg.get("wrapper_removal", {})

    # Markdown bold headers
    if "markdown_bold_headers" in wrappers:
        result = re.sub(wrappers["markdown_bold_headers"], '', result)

    # Full quote wrap
    result = result.strip()
    if result.startswith('"') and result.endswith('"') and result.count('"') == 2:
        result = result[1:-1]

    # Backtick wrap
    if result.startswith('`') and result.endswith('`') and '`' not in result[1:-1]:
        result = result[1:-1]

    # Triple backtick code blocks
    if result.startswith('```') and result.endswith('```'):
        match = re.match(r'^```[\w]*\n([\s\S]*?)\n```$', result)
        if match:
            result = match.group(1)

    return result.strip()


def _check_content_quality(text: str, config: Optional[dict] = None) -> Tuple[bool, str]:
    """Check if generated content meets quality standards.

    Args:
        text: Generated text to check.
        config: Config dict with quality_indicators.

    Returns:
        Tuple of (is_valid, reason_if_invalid).
    """
    cfg = config or load_meta_commentary_config()
    indicators = cfg.get("quality_indicators", {})

    min_chars = indicators.get("min_length_chars", 50)
    min_words = indicators.get("min_words", 10)
    suspicious = indicators.get("suspicious_phrases", [])

    if not text:
        return False, "empty_response"

    if len(text) < min_chars:
        return False, f"too_short_chars:{len(text)}"

    word_count = len(text.split())
    if word_count < min_words:
        return False, f"too_short_words:{word_count}"

    # Check for suspicious phrases that indicate refusal or meta-output
    text_lower = text.lower()
    for phrase in suspicious:
        if phrase.lower() in text_lower:
            return False, f"suspicious_phrase:{phrase}"

    return True, "ok"


def _cognitive_to_generation_params(state: CognitiveState, attempt: int = 0) -> dict:
    """Map cognitive state to LLM generation parameters.

    Maps the embodied scholar's metabolic state to generation parameters that
    simulate realistic cognitive effects:

    - Low glucose (depleted) → Lower temperature (conservative, less creative)
    - High fatigue → Higher presence penalty (avoiding repetition when exhausted)
    - Low attention → Lower top_p (narrower focus, less exploratory)
    - Syntactic resources → Affects max_tokens (complex planning = longer outputs)

    Args:
        state: Current CognitiveState from EmbodiedScholar
        attempt: Retry attempt number (0-indexed)

    Returns:
        Dict with temperature, top_p, presence_penalty, frequency_penalty, max_tokens
    """
    glucose = state.glucose_level
    fatigue = state.fatigue_index
    attention = state.allocation.attention if state.allocation else 0.8
    syntactic = state.allocation.syntactic if state.allocation else 0.7

    # Temperature: Higher glucose = more creative/exploratory
    # Range: 0.5 (depleted) to 0.9 (fresh)
    # Retry increases temp slightly to encourage different outputs
    base_temp = 0.5 + (glucose * 0.4)
    temperature = min(1.0, base_temp + (attempt * 0.05))

    # Top_p: Attention determines focus breadth
    # Low attention = narrower sampling, high attention = broader exploration
    # Range: 0.8 (narrow) to 0.98 (broad)
    top_p = 0.8 + (attention * 0.18)

    # Presence penalty: Fatigue increases tendency to avoid repetition
    # Exhausted writers instinctively avoid repeated phrases
    # Range: 0.0 (fresh) to 0.5 (fatigued)
    presence_penalty = fatigue * 0.5

    # Frequency penalty: Inverse of syntactic resources
    # High syntactic planning = more tolerance for repeated structures
    # Low syntactic resources = avoid overused patterns
    # Range: 0.0 (high resources) to 0.3 (low resources)
    frequency_penalty = max(0.0, 0.3 * (1.0 - syntactic))

    # Max tokens: Higher syntactic resources allow longer, more complex outputs
    # Range: 1536 (constrained) to 3072 (expansive)
    base_tokens = int(1536 + (syntactic * 1536))
    max_tokens = min(4096, base_tokens + (attempt * 256))

    return {
        "temperature": round(temperature, 3),
        "top_p": round(top_p, 3),
        "presence_penalty": round(presence_penalty, 3),
        "frequency_penalty": round(frequency_penalty, 3),
        "max_tokens": max_tokens,
    }


async def _generate_scholarly_content_with_retry(
    client: OpenRouterClient,
    models: List[str],
    abstract: str,
    preceding: str,
    following: str,
    discipline: str,
    target_length: int,
    salt: str,
    state: Optional[CognitiveState] = None,
    max_retries: int = 3,
) -> Tuple[str, GenerationMetadata]:
    """Generate scholarly content with automatic retry across models.

    Tries the primary model first, then falls back to other models
    in the list if generation fails or produces low-quality output.
    Generation parameters are derived from the author's cognitive state.

    Args:
        client: OpenRouter client instance.
        models: List of model IDs to try in order.
        abstract: Paper abstract for context.
        preceding: Text before insertion point.
        following: Text after insertion point.
        discipline: Academic discipline.
        target_length: Target word count.
        salt: Session identifier for prompt uniqueness.
        state: Cognitive state of the simulated author.
        max_retries: Max retries per model.

    Returns:
        Tuple of (generated_content, generation_metadata).

    Raises:
        ContentGenerationError: If all models fail after retries.
    """
    config = load_meta_commentary_config()
    errors = []

    # Default cognitive state if not provided
    if state is None:
        state = CognitiveState(
            minute=30,
            fatigue_index=0.2,
            glucose_level=0.8,
            allocation=ResourceAllocation(lexical=0.8, syntactic=0.7, attention=0.75),
            context_clarity=0.75,
            biometric_salt=salt,
        )

    prompt = f"""You are a tenured professor writing a scholarly paper in {discipline}.

Generate a cohesive passage (approximately {target_length} words) that fits naturally between the preceding and following text.

Paper abstract: {abstract[:400]}

Preceding text: "{preceding[-300:]}"

Following text: "{following[:300]}"

CRITICAL REQUIREMENTS:
- Write substantive scholarly content appropriate for the discipline
- Maintain academic register and terminology
- Ensure smooth transitions with surrounding context
- DO NOT include any preamble like "Here is..." or "The passage..."
- DO NOT wrap the text in quotes or formatting
- DO NOT explain what you're doing
- Start directly with the scholarly content itself
- Session identifier: {salt}

OUTPUT: Write ONLY the scholarly passage. Begin immediately with the actual content."""

    for model_idx, model in enumerate(models):
        for attempt in range(max_retries):
            try:
                # Derive generation parameters from cognitive state
                gen_params = _cognitive_to_generation_params(state, attempt)

                resp = await client.chat_completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    reject_truncation=True,
                    **gen_params,
                )

                content = resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                content = _strip_meta_commentary(content, config)

                is_valid, reason = _check_content_quality(content, config)
                if is_valid:
                    # Capture generation metadata for reproducibility
                    metadata = GenerationMetadata(
                        model_id=model,
                        temperature=gen_params.get("temperature", 0.7),
                        max_tokens=gen_params.get("max_tokens", 2048),
                        top_p=gen_params.get("top_p"),
                        presence_penalty=gen_params.get("presence_penalty"),
                        frequency_penalty=gen_params.get("frequency_penalty"),
                        attempt_number=attempt + (model_idx * max_retries),
                        cognitive_glucose=state.glucose_level,
                        cognitive_fatigue=state.fatigue_index,
                        cognitive_attention=state.allocation.attention if state.allocation else None,
                    )
                    return content, metadata
                else:
                    errors.append(f"{model}[{attempt}]: quality_fail:{reason}")

            except OpenRouterError as e:
                errors.append(f"{model}[{attempt}]: {type(e).__name__}:{str(e)[:50]}")
            except Exception as e:
                errors.append(f"{model}[{attempt}]: {type(e).__name__}:{str(e)[:50]}")

    raise ContentGenerationError(
        f"All models failed after retries. Errors: {'; '.join(errors[-6:])}"
    )


def _tokenize_for_simulation(text: str) -> List[str]:
    """Split text into tokens for causal simulation.

    Uses a simple word-based tokenization that preserves punctuation
    attached to words for more realistic simulation.
    """
    tokens = text.split()
    return [t for t in tokens if t.strip()]


async def run_causal_agentic_loop(
    client: OpenRouterClient, models: List[str], abstract: str,
    preceding: str, span: str, following: str, state: CognitiveState,
    profile: DocumentProfile, salt: str, doc_id: str, rev_id: str, ordinal: int,
    author: EmbodiedScholar
) -> Tuple[str, List[CausalEvent], dict, str, Optional[GenerationMetadata]]:
    """
    Full high-fidelity orchestrator with content generation:
    1. Generate Content (LLM creates new scholarly text fitting context)
    2. Plan Intentions (Technical deconstruction of generated content)
    3. Execute Irreversible Process Engine (Direct Author Mutation)
    4. Adversarial Hardening pass (Stylistic submergence)
    5. Forensic Identity Binding

    Args:
        client: OpenRouter API client.
        models: List of model IDs to use (first for author, second for critic).
        abstract: Paper abstract for context.
        preceding: Text before injection point.
        span: Original span being replaced.
        following: Text after injection point.
        state: Current cognitive state of simulated author.
        profile: Document profile with metadata.
        salt: Unique session identifier.
        doc_id: Document ID for injection.
        rev_id: Revision ID for injection.
        ordinal: Injection ordinal within revision.
        author: EmbodiedScholar instance for simulation.

    Returns:
        Tuple of (final_text, causal_events, signatures, causal_id, generation_metadata).

    Raises:
        ContentGenerationError: If content generation fails after all retries.
    """
    config = load_meta_commentary_config()
    discipline = profile.discipline if profile else "academic writing"

    # Target length based on context
    target_words = max(40, len(span.split()) * 4)

    # 1. GENERATE (Create new scholarly content via LLM with retry)
    # Pass cognitive state to drive generation parameters
    generated_content, gen_metadata = await _generate_scholarly_content_with_retry(
        client=client,
        models=models,
        abstract=abstract,
        preceding=preceding,
        following=following,
        discipline=discipline,
        target_length=target_words,
        salt=salt,
        state=state,
    )

    # 2. PLAN (Technical Intention Deconstruction of GENERATED content)
    tokens = _tokenize_for_simulation(generated_content)

    plan_prompt = f"""As a cognitive linguist, analyze these tokens from a scholarly writing session.
Session identifier: {salt}
Tokens: {json.dumps(tokens[:30])}
Context: "{abstract[:300]}"
Task: For each token, estimate syntactic_depth (1-10), lexical_rarity (0-1), and cognitive_cost (0.01-0.1).
Return ONLY a JSON list of objects with keys: target, syntactic_depth, lexical_rarity, cognitive_cost."""

    m_author = models[0]
    m_critic = models[1] if len(models) > 1 else models[0]

    try:
        resp = await client.chat_completion(
            model=m_author,
            messages=[{"role": "user", "content": plan_prompt}],
            temperature=0.2,
            max_tokens=4096
        )

        raw = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r'\[[\s\S]*\]', raw)
        if match:
            intent_data = json.loads(match.group())
            intentions = []
            for i, d in enumerate(intent_data):
                if i < len(tokens):
                    intentions.append(LexicalIntention(
                        target=tokens[i],
                        syntactic_depth=float(d.get("syntactic_depth", 5.0)),
                        lexical_rarity=float(d.get("lexical_rarity", 0.5)),
                        cognitive_cost=float(d.get("cognitive_cost", 0.03))
                    ))
            for i in range(len(intentions), len(tokens)):
                intentions.append(LexicalIntention(tokens[i], 5.0, 0.5, 0.03))
        else:
            raise ValueError("JSON not found")
    except (json.JSONDecodeError, ValueError, KeyError, TypeError, OpenRouterError):
        intentions = [LexicalIntention(t, 5.0, 0.5, 0.03) for t in tokens]

    # 3. EXECUTE (Irreversible Process Engine - Mutates Author)
    engine = IrreversibleProcessEngine(author=author, discipline=discipline)
    for intent in intentions:
        engine.execute(intent)

    causal_text = engine.render_text()
    sigs = engine.compute_causal_signatures()

    # 4. HARDEN (Final Adversarial Pass)
    floor = _compression_discontinuity(preceding, following)
    surprise = _compression_discontinuity(preceding, causal_text)

    final_text = causal_text
    if abs(surprise - floor) > 0.10:
        harden_prompt = f"""Refine this scholarly passage for {discipline} writing.

INPUT: {causal_text}

TASK: Improve clarity and academic register while preserving meaning.

CRITICAL: Output ONLY the refined text. No preamble, no explanations, no "Here is". Begin directly with the scholarly content."""

        try:
            resp_h = await client.chat_completion(
                model=m_critic,
                messages=[{"role": "user", "content": harden_prompt}],
                temperature=0.3,
                max_tokens=2048
            )
            hardened = resp_h.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            hardened = _strip_meta_commentary(hardened, config)
            if hardened and len(hardened) > len(causal_text) * 0.5:
                final_text = hardened
        except OpenRouterError:
            pass  # Keep causal_text if hardening fails

    # 5. IDENTITY BINDING (Anchor to process signatures)
    causal_events = [CausalEvent(
        intention=e.intention.target,
        actual_output=e.actual_output,
        status="success" if not e.failure_mode else "repair",
        failure_mode=e.failure_mode,
        repair_artifact=e.actual_output if e.failure_mode else None,
        glucose_at_event=e.glucose_after,
        latency_ms=e.latency_ms,
        syntactic_complexity=e.intention.syntactic_depth
    ) for e in engine.trace]

    causal_id = make_causal_injection_id(doc_id, rev_id, ordinal, sigs)

    return final_text, causal_events, sigs, causal_id, gen_metadata
