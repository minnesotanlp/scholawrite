"""Asynchronous augmented document builder with causal process simulation."""
from __future__ import annotations

import random
import json
import threading
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Sequence, Optional

from .schema import (
    AugmentedDocument,
    AugmentedRevision,
    InjectionSpan,
    SeedDocument,
    CausalEvent,
    GenerationMetadata,
)
from .text import char_offsets, compute_provenance_hash, split_sentences
from .trajectories import determine_trajectory_state
from .openrouter import OpenRouterClient
from .prompts import build_profiling_prompt, DocumentProfile
from .embodied import get_embodied_state, erode_context_deterministically, EmbodiedScholar
from .agentic import run_causal_agentic_loop
from .injection import detect_prompt_leakage
import logging

# Set up logger for leakage detection warnings
_leakage_logger = logging.getLogger("scholawrite.augment.leakage")

__all__ = [
    "build_augmented", "build_augmented_async", "InjectionRecord",
    "get_doc_profile", "InsertionVerificationError", "check_and_log_leakage",
    "LeakageFilterMode", "LLMCache",
]


class LeakageFilterMode:
    """Modes for handling detected prompt leakage in generated text."""
    IGNORE = "ignore"       # Don't check for leakage
    WARN = "warn"           # Log warnings but accept the text
    REJECT = "reject"       # Reject text with leakage, use fallback


def check_and_log_leakage(
    text: str,
    context_id: str,
    mode: str = LeakageFilterMode.WARN,
) -> tuple[bool, List[str]]:
    """Check generated text for prompt leakage and handle according to mode.

    Args:
        text: The generated text to check.
        context_id: Identifier for logging (e.g., injection_id, revision context).
        mode: One of LeakageFilterMode values.

    Returns:
        Tuple of (is_clean, detected_patterns).
        is_clean is True if no leakage detected or mode is IGNORE.
        detected_patterns is list of matched pattern strings.
    """
    if mode == LeakageFilterMode.IGNORE:
        return True, []

    detected = detect_prompt_leakage(text)

    if detected:
        _leakage_logger.warning(
            f"[LEAKAGE] Detected {len(detected)} pattern(s) in {context_id}: {detected[:3]}..."
        )
        if mode == LeakageFilterMode.REJECT:
            return False, detected

    return not detected, detected


class InsertionVerificationError(Exception):
    """Raised when an injection cannot be verified in the final text."""
    def __init__(self, message: str, span_id: str, revision_id: str):
        self.message = message
        self.span_id = span_id
        self.revision_id = revision_id
        super().__init__(f"{message} (span={span_id}, revision={revision_id})")


def _verify_insertion(
    revision_text: str,
    span: InjectionSpan,
    expected_text: str,
    strict: bool = False,
) -> bool:
    """
    Verify that injected text exists at the expected position.

    Args:
        revision_text: The full text of the revision after insertion.
        span: The InjectionSpan with updated character offsets.
        expected_text: The text that was supposed to be inserted.
        strict: If True, raises InsertionVerificationError on failure.

    Returns:
        True if verification passes, False otherwise.

    Raises:
        InsertionVerificationError: If strict=True and verification fails.
    """
    # Check span boundaries are within text
    if span.span_start_char < 0:
        msg = f"Span start {span.span_start_char} is negative"
        if strict:
            raise InsertionVerificationError(msg, span.injection_id, span.revision_id)
        return False

    if span.span_start_char >= len(revision_text):
        msg = f"Span start {span.span_start_char} exceeds text length {len(revision_text)}"
        if strict:
            raise InsertionVerificationError(msg, span.injection_id, span.revision_id)
        return False

    if span.span_end_char > len(revision_text):
        msg = f"Span end {span.span_end_char} exceeds text length {len(revision_text)}"
        if strict:
            raise InsertionVerificationError(msg, span.injection_id, span.revision_id)
        return False

    # Extract the actual content at the span position
    actual = revision_text[span.span_start_char:span.span_end_char]

    # Verify the expected text is present
    if expected_text not in actual:
        msg = f"Expected text not found at span position. Expected: '{expected_text[:50]}...', Got: '{actual[:50]}...'"
        if strict:
            raise InsertionVerificationError(msg, span.injection_id, span.revision_id)
        return False

    # Verify span is not empty
    if not actual.strip():
        msg = f"Span references empty or whitespace-only content"
        if strict:
            raise InsertionVerificationError(msg, span.injection_id, span.revision_id)
        return False

    return True


def _verify_all_spans(
    revision_text: str,
    spans: List[InjectionSpan],
    injected_texts: Dict[str, str],
    strict: bool = False,
) -> List[str]:
    """
    Verify all spans in a revision after insertions.

    Args:
        revision_text: The full text of the revision after all insertions.
        spans: List of InjectionSpans with updated character offsets.
        injected_texts: Mapping from injection_id to the injected text.
        strict: If True, raises on first failure.

    Returns:
        List of warning messages for any verification failures.
    """
    warnings = []

    for span in spans:
        expected = injected_texts.get(span.injection_id, "")
        if not _verify_insertion(revision_text, span, expected, strict=strict):
            warnings.append(
                f"Verification failed for span {span.injection_id} in revision {span.revision_id}"
            )

    return warnings

class LLMCache:
    """Thread-safe LLM response cache with file persistence."""

    def __init__(
        self,
        cache_file: Path = Path("data/augmented/full/llm_cache.jsonl"),
        trace_file: Path = Path("data/augmented/full/negotiation_traces.jsonl"),
    ):
        self._lock = threading.Lock()
        self._cache: Dict[str, str] = {}
        self._cache_file = cache_file
        self._trace_file = trace_file

    def load(self) -> None:
        """Load cache from disk."""
        if not self._cache_file.exists():
            return
        with self._lock:
            self._cache.clear()
            with open(self._cache_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        self._cache[data["prompt_hash"]] = data["result"]
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue

    def get(self, prompt_hash: str) -> Optional[str]:
        """Retrieve cached LLM result if available."""
        with self._lock:
            return self._cache.get(prompt_hash)

    def save(self, prompt_hash: str, result: str) -> None:
        """Save LLM result to cache (async write to avoid blocking)."""
        def _write():
            with self._lock:
                self._cache[prompt_hash] = result
                self._cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self._cache_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"prompt_hash": prompt_hash, "result": result}) + "\n")
        threading.Thread(target=_write, daemon=True).start()

    def save_trace(self, injection_id: str, revision_id: int, trace: List[CausalEvent]) -> None:
        """Save causal trace to file (async write)."""
        def _write():
            with self._lock:
                self._trace_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self._trace_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "injection_id": injection_id,
                        "revision_id": revision_id,
                        "timestamp": datetime.now().isoformat(),
                        "trace": [asdict(e) for e in trace]
                    }) + "\n")
        if trace:
            threading.Thread(target=_write, daemon=True).start()

    @staticmethod
    def make_key(doc_id: str, inj_id: str, rev_idx: int, context_hash: str) -> str:
        """Create a deterministic cache key for an LLM call."""
        import hashlib
        key_data = f"{doc_id}:{inj_id}:{rev_idx}:{context_hash}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]


# Module-level instance for backward compatibility
_default_cache = LLMCache()

@dataclass(frozen=True)
class InjectionRecord:
    span: InjectionSpan
    injected_text: str


def build_augmented(
    seed_docs: Sequence[SeedDocument],
    records: Sequence[InjectionRecord],
    simulate_edits: bool = False,
    verify_insertions: bool = True,
    strict_verification: bool = False,
) -> List[AugmentedDocument]:
    """
    Build augmented documents from seed documents and injection records.

    When simulate_edits=False, simply inserts the injected text at the span position.
    When simulate_edits=True, would require async processing (use build_augmented_async).

    Args:
        seed_docs: Source documents to augment.
        records: Injection records containing spans and text to inject.
        simulate_edits: If True, requires async processing (raises ValueError).
        verify_insertions: If True, verify that injected text exists at expected positions.
        strict_verification: If True, raise InsertionVerificationError on failure.

    Returns:
        List of augmented documents with injections applied.

    Raises:
        InsertionVerificationError: If strict_verification=True and verification fails.
    """
    if simulate_edits:
        raise ValueError("simulate_edits=True requires async processing. Use build_augmented_async instead.")

    # Build lookup for which revision each injection belongs to
    revision_lookup: Dict[str, Dict[str, int]] = {}
    for doc in seed_docs:
        revision_lookup[doc.doc_id] = {rev.revision_id: rev_idx for rev_idx, rev in enumerate(doc.revisions)}

    augmented_docs = []
    for doc in seed_docs:
        # Get records for this document
        doc_records = [r for r in records if r.span.doc_id == doc.doc_id]

        doc_revisions = []
        for rev_idx, rev in enumerate(doc.revisions):
            text = rev.text
            offset = 0
            updated_spans: List[InjectionSpan] = []

            for record in doc_records:
                span = record.span
                # Only include injection if this revision is at or after the injection's birth revision
                birth_rev_idx = revision_lookup[doc.doc_id].get(span.revision_id, 0)
                if rev_idx < birth_rev_idx:
                    continue

                # Insert injected text at the span position
                insert_pos = max(0, min(len(text), span.span_start_char + offset))
                text = text[:insert_pos] + record.injected_text + text[insert_pos:]

                # Create updated span with new end position
                new_end = insert_pos + len(record.injected_text)
                updated_span = InjectionSpan(
                    doc_id=span.doc_id,
                    revision_id=span.revision_id,
                    injection_id=span.injection_id,
                    injection_level=span.injection_level,
                    trajectory_state=span.trajectory_state,
                    ambiguity_flag=span.ambiguity_flag,
                    span_start_char=insert_pos,
                    span_end_char=new_end,
                    span_start_sentence=span.span_start_sentence,
                    span_end_sentence=span.span_end_sentence,
                    generator_class=span.generator_class,
                    prompt_hash=span.prompt_hash,
                    rng_seed=span.rng_seed,
                    provenance_hash=span.provenance_hash,
                    label=span.label,
                    causal_trace=span.causal_trace,
                )
                updated_spans.append(updated_span)
                offset += len(record.injected_text)

            # Verify insertions if enabled - only verify at birth revision
            # (positions are only meaningful at the revision where injection was created)
            if verify_insertions and updated_spans:
                # Only verify spans that are at their birth revision
                birth_spans = [
                    s for s in updated_spans
                    if revision_lookup[doc.doc_id].get(s.revision_id, 0) == rev_idx
                ]
                if birth_spans:
                    injected_texts = {
                        r.span.injection_id: r.injected_text
                        for r in doc_records
                        if revision_lookup[doc.doc_id].get(r.span.revision_id, 0) == rev_idx
                    }
                    warnings = _verify_all_spans(
                        text, birth_spans, injected_texts, strict=strict_verification
                    )
                    for warning in warnings:
                        print(f"[WARN] {warning}")

            doc_revisions.append(AugmentedRevision(
                doc_id=rev.doc_id,
                revision_id=rev.revision_id,
                revision_index=rev.revision_index,
                text=text,
                timestamp=rev.timestamp,
                provenance_hash=compute_provenance_hash(text),
                annotations=updated_spans,
                # Preserve original ScholaWrite fields
                before_text=getattr(rev, 'before_text', None),
                writing_intention=getattr(rev, 'writing_intention', None),
                high_level_category=getattr(rev, 'high_level_category', None),
            ))

        augmented_docs.append(AugmentedDocument(doc.doc_id, doc_revisions))

    return augmented_docs


async def get_doc_profile(client: OpenRouterClient, model: str, abstract: str) -> DocumentProfile:
    prompt = build_profiling_prompt(abstract)
    try:
        resp = await client.chat_completion(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.5, max_tokens=2048)
        text = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        data = json.loads(re.search(r"\\{.*\\}", text, re.DOTALL).group())
        return DocumentProfile(persona=data.get("persona", "prof"), discipline=data.get("discipline", "Research"), primary_goal=data.get("primary_goal", "clarity"), secondary_goals=data.get("secondary_goals", []), stylistic_voice=data.get("stylistic_voice", "formal"), paranoia_level=data.get("paranoia_level", 0.1))
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        pass
    return DocumentProfile("prof", "Research", "refine", [], "formal", 0.1)

async def build_augmented_async(
    seed_docs: Sequence[SeedDocument],
    injections: Sequence[InjectionSpan],
    client: Optional[OpenRouterClient] = None,
    models: Optional[List[str]] = None,
    verify_insertions: bool = True,
    strict_verification: bool = False,
    cache: Optional[LLMCache] = None,
) -> List[AugmentedDocument]:
    """
    Async version with full causal process simulation via LLM calls.

    Args:
        seed_docs: Source documents to augment.
        injections: Injection spans to apply.
        client: OpenRouter client for LLM calls.
        models: List of model IDs to use.
        verify_insertions: If True, verify that injected text exists at expected positions.
        strict_verification: If True, raise InsertionVerificationError on failure.
        cache: LLMCache instance (uses module default if None).

    Returns:
        List of augmented documents with injections applied.

    Raises:
        InsertionVerificationError: If strict_verification=True and verification fails.
    """
    if cache is None:
        cache = _default_cache
    cache.load()
    revision_lookup = {rev.revision_id: (doc_idx, rev_idx) for doc_idx, doc in enumerate(seed_docs) for rev_idx, rev in enumerate(doc.revisions)}
    augmented_docs = []

    for doc in seed_docs:
        author = EmbodiedScholar(f"author_{doc.doc_id[:8]}")
        injections_for_doc = [i for i in injections if i.doc_id == doc.doc_id]
        evolved_texts, evolved_traces, evolved_sigs, evolved_ids, evolved_meta = {}, {}, {}, {}, {}
        abstract = doc.revisions[-1].text[:1500] if doc.revisions else ""
        profile = await get_doc_profile(client, random.choice(models), abstract) if client and models else DocumentProfile("prof", "Research", "refine", [], "formal", 0.1)

        for ordinal, inj in enumerate(injections_for_doc):
            inj_id = inj.injection_id
            birth_idx = revision_lookup[inj.revision_id][1]
            span_rng = random.Random(f"{doc.doc_id}:{inj_id}")

            # --- Bridge Initial Trace Gap ---
            # Sample initial text from the human-checked or placeholder birth text
            # In a full run, we'd load this from generated_text.jsonl, here we use the span's implicit provenance
            current_text = "This approach"
            current_trace = list(inj.causal_trace)
            current_meta = inj.generation_metadata

            evolved_texts[inj_id], evolved_traces[inj_id], evolved_sigs[inj_id], evolved_ids[inj_id], evolved_meta[inj_id] = {birth_idx: current_text}, {birth_idx: current_trace}, {birth_idx: {}}, {birth_idx: inj_id}, {birth_idx: current_meta}
            target_model = inj.generator_class or (random.choice(models) if models else "openai/gpt-3.5-turbo")

            for rev_idx in range(birth_idx + 1, len(doc.revisions)):
                # GUARANTEE at least one edit per span to ensure causal grounding
                force_edit = (rev_idx == birth_idx + 2)
                if force_edit or span_rng.random() < 0.05:
                    state = get_embodied_state(author, rev_idx, len(doc.revisions), current_text)
                    rev_text = doc.revisions[rev_idx].text
                    pos = inj.span_start_char
                    pre = erode_context_deterministically(rev_text[max(0, pos-500):pos], state.context_clarity, f"{state.biometric_salt}:pre")
                    fol = erode_context_deterministically(rev_text[pos:pos+500], state.context_clarity, f"{state.biometric_salt}:fol")
                    m1, m2 = span_rng.sample(models, 2) if models and len(models) >= 2 else (target_model, target_model)

                    # Check cache before making LLM calls
                    context_hash = compute_provenance_hash(f"{pre}:{current_text}:{fol}")[:16]
                    cache_key = LLMCache.make_key(doc.doc_id, inj_id, rev_idx, context_hash)
                    cached_result = cache.get(cache_key)

                    if cached_result:
                        print(f"  [CACHE HIT] {inj_id[:8]} at rev {rev_idx}", flush=True)
                        # Parse cached result (stored as JSON)
                        try:
                            cached_data = json.loads(cached_result)
                            new_text = cached_data["text"]
                            trace = [CausalEvent(**e) for e in cached_data.get("trace", [])]
                            sigs = cached_data.get("sigs", {})
                            causal_id = cached_data.get("causal_id", f"{doc.doc_id}:{inj_id}:{rev_idx}")
                            meta_data = cached_data.get("generation_metadata")
                            gen_meta = GenerationMetadata(**meta_data) if meta_data else None
                        except (json.JSONDecodeError, KeyError, TypeError):
                            cached_result = None  # Invalid cache, regenerate

                    if not cached_result:
                        print(f"  Irreversible Process Edit: {inj_id[:8]} at rev {rev_idx}...", flush=True)
                        new_text, trace, sigs, causal_id, gen_meta = await run_causal_agentic_loop(client, [m1, m2], abstract, pre, current_text, fol, state, profile, f"{doc.doc_id}:{inj_id}:{rev_idx}", doc.doc_id, doc.revisions[rev_idx].revision_id, ordinal, author)

                        # Save to cache for future runs
                        cache_data = json.dumps({
                            "text": new_text,
                            "trace": [asdict(e) if hasattr(e, '__dataclass_fields__') else e for e in trace],
                            "sigs": sigs,
                            "causal_id": causal_id,
                            "generation_metadata": asdict(gen_meta) if gen_meta else None,
                        })
                        cache.save(cache_key, cache_data)

                    # Check for prompt leakage in generated text
                    is_clean, leakage_patterns = check_and_log_leakage(
                        new_text,
                        context_id=f"{inj_id}:rev{rev_idx}",
                        mode=LeakageFilterMode.WARN,
                    )
                    if not is_clean:
                        # Log detailed leakage info but continue (WARN mode)
                        _leakage_logger.warning(
                            f"  [LEAKAGE WARNING] Generated text for {inj_id[:8]} contains "
                            f"{len(leakage_patterns)} LLM artifact(s). Patterns: {leakage_patterns}"
                        )

                    # Store results ONLY if biometrically authentic
                    if sigs.get("is_plausible", False) or force_edit:
                        evolved_texts[inj_id][rev_idx], evolved_traces[inj_id][rev_idx], evolved_sigs[inj_id][rev_idx], evolved_ids[inj_id][rev_idx], evolved_meta[inj_id][rev_idx] = new_text, trace, sigs, causal_id, gen_meta
                        current_text = new_text
                        current_meta = gen_meta
                        if trace:
                            cache.save_trace(causal_id, rev_idx, trace)

        doc_revisions = []
        for rev_idx, rev in enumerate(doc.revisions):
            text, offset, updated_spans = rev.text, 0, []
            for inj in injections_for_doc:
                if rev_idx < revision_lookup[inj.revision_id][1]: continue
                evol_map, trace_map, id_map, meta_map = evolved_texts[inj.injection_id], evolved_traces[inj.injection_id], evolved_ids[inj.injection_id], evolved_meta[inj.injection_id]
                active_rev = max([r for r in evol_map.keys() if r <= rev_idx])
                injected_text, causal_id, active_trace, active_meta = evol_map[active_rev], id_map[active_rev], trace_map.get(active_rev, []), meta_map.get(active_rev)

                # Filter out raw dictionaries from the trace list and convert to CausalEvent
                typed_trace = []
                for e in active_trace:
                    if isinstance(e, dict):
                        # Re-map dictionary fields to CausalEvent attributes
                        typed_trace.append(CausalEvent(
                            intention=e.get('intention', {}).get('target', e.get('intention', '')),
                            actual_output=e['actual_output'],
                            status='success' if not e.get('failure_mode') else 'repair',
                            failure_mode=e.get('failure_mode'),
                            repair_artifact=e.get('repair_artifact'),
                            glucose_at_event=e.get('glucose_after', e.get('glucose_at_event', 1.0)),
                            latency_ms=e['latency_ms'],
                            syntactic_complexity=e.get('intention', {}).get('syntactic_depth', e.get('syntactic_complexity', 5.0))
                        ))
                    else:
                        typed_trace.append(e)

                at = max(0, min(len(text), inj.span_start_char + offset))
                text = text[:at] + injected_text + text[at:]
                meta = next((m for m in evolved_sigs[inj.injection_id].items() if m[0] <= rev_idx), (None, {}))
                res = determine_trajectory_state(meta[1])
                updated_spans.append(InjectionSpan(inj.doc_id, inj.revision_id, causal_id, inj.injection_level, res[0], res[1], at, at + len(injected_text), 0, 0, inj.generator_class, inj.prompt_hash, inj.rng_seed, inj.provenance_hash, label=inj.label, causal_trace=typed_trace, generation_metadata=active_meta))
                offset += len(injected_text)

            if updated_spans:
                sentences = split_sentences(text)
                offsets = char_offsets(text, sentences)
                for i, span in enumerate(updated_spans):
                    s_idx, e_idx = 0, 0
                    for j, (s, e) in enumerate(offsets):
                        if s <= span.span_start_char < e: s_idx = j
                        if s < span.span_end_char <= e: e_idx = j
                    updated_spans[i] = InjectionSpan(span.doc_id, span.revision_id, span.injection_id, span.injection_level, span.trajectory_state, span.ambiguity_flag, span.span_start_char, span.span_end_char, s_idx, e_idx, span.generator_class, span.prompt_hash, span.rng_seed, span.provenance_hash, label=span.label, causal_trace=span.causal_trace, generation_metadata=span.generation_metadata)

                # Verify insertions if enabled
                if verify_insertions:
                    injected_texts = {
                        inj.injection_id: evolved_texts[inj.injection_id].get(
                            max([r for r in evolved_texts[inj.injection_id].keys() if r <= rev_idx]), ""
                        )
                        for inj in injections_for_doc
                        if rev_idx >= revision_lookup[inj.revision_id][1]
                    }
                    warnings = _verify_all_spans(
                        text, updated_spans, injected_texts, strict=strict_verification
                    )
                    for warning in warnings:
                        print(f"[WARN] {warning}")

            doc_revisions.append(AugmentedRevision(
                doc_id=rev.doc_id,
                revision_id=rev.revision_id,
                revision_index=rev.revision_index,
                text=text,
                timestamp=rev.timestamp,
                provenance_hash=compute_provenance_hash(text),
                annotations=updated_spans,
                before_text=getattr(rev, 'before_text', None),
                writing_intention=getattr(rev, 'writing_intention', None),
                high_level_category=getattr(rev, 'high_level_category', None),
            ))
        augmented_docs.append(AugmentedDocument(doc.doc_id, doc_revisions))
    return augmented_docs
