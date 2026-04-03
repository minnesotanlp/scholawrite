#!/usr/bin/env python
"""Build complete, balanced dataset with all documents and injection levels.

This script orchestrates the full pipeline:
1. Generate diverse injections across ALL documents
2. Balance injection levels (naive/topical/contextual)
3. Build augmented documents with trajectory simulation
4. Generate statistics and validation report
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import List

from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, success, error, warning, info, bold, dim
from scholawrite.io import read_documents_jsonl, write_augmented_jsonl
from scholawrite.schema import (
    InjectionLevel, InjectionSpan, SeedDocument,
    TrajectoryState, CognitiveState, DocumentProfile
)
from scholawrite.injection import (
    select_injection_points, create_injection_span, generate_deterministic_placeholder
)
from scholawrite.generators import GeneratorSpec, GeneratorClass
from scholawrite.augment import build_augmented, InjectionRecord, get_doc_profile
from scholawrite.openrouter import OpenRouterClient, TruncationError
from scholawrite.embodied import EmbodiedScholar
from scholawrite.agentic import run_causal_agentic_loop


# Target distribution for balanced dataset
TARGET_INJECTIONS_PER_DOC = 50

# Natural variation parameters
INJECTION_COUNT_VARIANCE = 0.3  # ±30% variation in injections per doc
TEXT_LENGTH_MIN = 80
TEXT_LENGTH_MAX = 250
TIME_INTERVAL_MIN = 1  # minutes
TIME_INTERVAL_MAX = 8  # minutes

# Weighted distributions (more realistic than uniform rotation)
LEVEL_WEIGHTS = {
    InjectionLevel.NAIVE: 0.35,      # Generic text more common
    InjectionLevel.TOPICAL: 0.40,    # Domain-relevant most common
    InjectionLevel.CONTEXTUAL: 0.25, # Sophisticated insertion less common
}
TRAJECTORY_WEIGHTS = {
    TrajectoryState.COLD: 0.50,       # Most injections are fresh
    TrajectoryState.WARM: 0.35,       # Some get partially integrated
    TrajectoryState.ASSIMILATED: 0.15, # Few fully blend in
}

# Note: Problematic models have been removed from configs/openrouter_models.json
# No runtime exclusion needed - the config file only contains reliable models


def _generate_diverse_injections(
    documents: List[SeedDocument],
    injections_per_doc: int = TARGET_INJECTIONS_PER_DOC,
    seed: int = 42,
) -> List[tuple[InjectionSpan, str]]:
    """Generate injections across all documents with balanced levels."""
    all_injections = []

    # Create default generator specs for placeholder text
    generators = [
        GeneratorSpec("gpt-4-placeholder", GeneratorClass.STRONG, "1.0", {}),
        GeneratorSpec("claude-placeholder", GeneratorClass.STRONG, "1.0", {}),
        GeneratorSpec("llama-placeholder", GeneratorClass.MID, "1.0", {}),
    ]

    for doc in documents:
        print(info(f"  Generating {injections_per_doc} injections for {doc.doc_id[:12]}..."))

        # Select injection points
        doc_rng = random.Random(f"{seed}:{doc.doc_id}")
        candidates = select_injection_points(doc, doc_rng, max_per_doc=injections_per_doc)

        if not candidates:
            print(warning(f"    No injection candidates found for {doc.doc_id[:12]}"))
            continue

        for ordinal, candidate in enumerate(candidates):
            # Rotate through injection levels for balance
            level_idx = ordinal % 3
            if level_idx == 0:
                level = InjectionLevel.NAIVE
            elif level_idx == 1:
                level = InjectionLevel.TOPICAL
            else:
                level = InjectionLevel.CONTEXTUAL

            # Rotate through trajectory states for balance
            traj_idx = (ordinal // 3) % 3
            if traj_idx == 0:
                trajectory = TrajectoryState.COLD
            elif traj_idx == 1:
                trajectory = TrajectoryState.WARM
            else:
                trajectory = TrajectoryState.ASSIMILATED

            # Select generator
            generator = generators[ordinal % len(generators)]

            # Generate placeholder text
            text_seed = hash(f"{doc.doc_id}:{ordinal}")
            text = generate_deterministic_placeholder(level, seed=text_seed)

            # Create injection span
            span = create_injection_span(
                candidate=candidate,
                level=level,
                trajectory_state=trajectory,
                generator=generator,
                rng_seed=text_seed,
                injected_text=text,
                ordinal=ordinal,
            )

            all_injections.append((span, text))

    return all_injections


async def _generate_llm_injections(
    documents: List[SeedDocument],
    client: OpenRouterClient,
    models: List[str],
    injections_per_doc: int = TARGET_INJECTIONS_PER_DOC,
    seed: int = 42,
    use_cognitive: bool = True,
) -> List[tuple[InjectionSpan, str]]:
    """Generate injections using LLM with full cognitive simulation.

    When use_cognitive=True, uses:
    - EmbodiedScholar: Persistent metabolic state per document
    - run_causal_agentic_loop: Full high-fidelity orchestration with:
      - Technical intention deconstruction
      - Irreversible process engine execution
      - Adversarial hardening pass
      - Forensic identity binding with causal traces

    Natural variation is applied to:
    - Injections per document (±30% variance)
    - Injection level selection (weighted random, not rotation)
    - Trajectory state selection (weighted random)
    - Text length (variable within range)
    - Time intervals between injections
    - Cognitive state parameters
    """
    from scholawrite.prompts import (
        build_naive_prompt, build_topical_prompt, build_contextual_prompt
    )
    from scholawrite.embodied import get_syntactic_demand
    from dataclasses import replace

    all_injections = []

    # Create generator specs from model names
    def make_generator(model_id: str) -> GeneratorSpec:
        return GeneratorSpec(model_id, GeneratorClass.STRONG, "1.0", {})

    # Helper to select weighted random level
    def select_level(rng: random.Random) -> InjectionLevel:
        levels = list(LEVEL_WEIGHTS.keys())
        weights = list(LEVEL_WEIGHTS.values())
        return rng.choices(levels, weights=weights, k=1)[0]

    # Helper to select weighted random trajectory
    def select_trajectory(rng: random.Random) -> TrajectoryState:
        states = list(TRAJECTORY_WEIGHTS.keys())
        weights = list(TRAJECTORY_WEIGHTS.values())
        return rng.choices(states, weights=weights, k=1)[0]

    for doc in documents:
        doc_rng = random.Random(f"{seed}:{doc.doc_id}")

        # Natural variation in injections per document (±30%)
        variance_factor = 1.0 + doc_rng.uniform(-INJECTION_COUNT_VARIANCE, INJECTION_COUNT_VARIANCE)
        doc_injection_count = max(3, int(injections_per_doc * variance_factor))

        print(info(f"  Generating {doc_injection_count} cognitive injections for {doc.doc_id[:12]}..."))

        candidates = select_injection_points(doc, doc_rng, max_per_doc=doc_injection_count)

        if not candidates:
            print(warning(f"    No injection candidates found for {doc.doc_id[:12]}"))
            continue

        # Create persistent EmbodiedScholar for this document
        # This simulates cognitive resource depletion across the writing session
        author = EmbodiedScholar(author_id=f"author_{doc.doc_id[:8]}")

        # Get document profile from abstract
        abstract = doc.revisions[-1].text[:1500] if doc.revisions else ""
        profile = None
        if use_cognitive:
            try:
                profile = await get_doc_profile(client, doc_rng.choice(models), abstract)
            except Exception as e:
                print(warning(f"    Profile extraction failed: {e}"))

        # Default profile if extraction failed
        if profile is None:
            profile = DocumentProfile(
                persona="academic researcher",
                discipline="general academic",
                primary_goal="scholarly contribution",
                secondary_goals=["clarity", "rigor"],
                stylistic_voice="formal academic",
                paranoia_level=doc_rng.uniform(0.3, 0.7),  # Natural variation
            )

        # Track simulated session time with natural intervals
        session_minute = 0

        for ordinal, candidate in enumerate(candidates):
            # Weighted random selection instead of rotation
            level = select_level(doc_rng)
            trajectory = select_trajectory(doc_rng)

            # Natural time progression with variable intervals
            time_interval = doc_rng.uniform(TIME_INTERVAL_MIN, TIME_INTERVAL_MAX)
            session_minute += time_interval

            model = doc_rng.choice(models)
            generator = make_generator(model)
            text_seed = hash(f"{doc.doc_id}:{ordinal}")
            causal_trace = []
            causal_sigs = {}

            # Variable text length for natural appearance
            target_text_length = doc_rng.randint(TEXT_LENGTH_MIN, TEXT_LENGTH_MAX)

            # Variable cognitive demand based on context complexity
            context_text = (candidate.preceding_text or "") + (candidate.following_text or "")
            cognitive_demand = get_syntactic_demand(context_text) + doc_rng.uniform(-1.0, 1.0)

            try:
                # For CONTEXTUAL level with cognitive features, use full agentic loop
                if level == InjectionLevel.CONTEXTUAL and use_cognitive:
                    # Create cognitive state with natural variation
                    allocation = author.allocate_resources(demand=cognitive_demand)

                    # Context clarity degrades non-linearly with jitter
                    base_clarity = 0.9 - (session_minute / 120.0) * 0.4  # Degrades over 90+ min session
                    clarity_jitter = doc_rng.uniform(-0.05, 0.05)
                    context_clarity = max(0.3, min(1.0, base_clarity + clarity_jitter))

                    state = CognitiveState(
                        minute=int(session_minute),
                        fatigue_index=author.visual_fatigue,
                        glucose_level=author.glucose,
                        allocation=allocation,
                        context_clarity=context_clarity,
                        biometric_salt=f"{seed}:{doc.doc_id}:{ordinal}:{author.glucose:.4f}",
                    )

                    # Get revision context
                    rev = doc.revisions[-1] if doc.revisions else None
                    rev_id = rev.revision_id if rev else "rev_unknown"

                    # Generate initial span text for deconstruction
                    initial_span = candidate.preceding_text[-50:] if candidate.preceding_text else "This approach"

                    # Run full causal agentic loop with retry logic
                    # NO PLACEHOLDERS - retry with different model pairs until success
                    text = None
                    causal_trace = []
                    causal_sigs = {}
                    causal_id = None
                    tried_pairs = set()
                    last_error = None

                    max_attempts = min(len(models), 10)
                    for attempt in range(max_attempts):
                        m_author = doc_rng.choice(models)
                        m_critic = doc_rng.choice([m for m in models if m != m_author] or models)
                        pair_key = f"{m_author}:{m_critic}"
                        if pair_key in tried_pairs:
                            continue
                        tried_pairs.add(pair_key)

                        try:
                            text, causal_trace, causal_sigs, causal_id = await run_causal_agentic_loop(
                                client=client,
                                models=[m_author, m_critic],
                                abstract=abstract,
                                preceding=candidate.preceding_text or "",
                                span=initial_span,
                                following=candidate.following_text or "",
                                state=state,
                                profile=profile,
                                salt=f"{seed}:{ordinal}",
                                doc_id=doc.doc_id,
                                rev_id=rev_id,
                                ordinal=ordinal,
                                author=author,
                            )
                            if text and len(text) >= 30:
                                model = m_author
                                generator = make_generator(model)
                                break
                            else:
                                last_error = f"Response too short ({len(text) if text else 0} chars)"
                        except (TruncationError, Exception) as e:
                            last_error = str(e)
                            print(warning(f"      Attempt {attempt+1} failed ({m_author[:20]}): {str(e)[:50]}"))

                    # If causal loop failed, fall back to simpler contextual prompt
                    if not text or len(text) < 30:
                        print(warning(f"      Causal loop failed, using simple contextual prompt"))
                        domain = profile.discipline if profile else "academic writing"
                        fallback_prompt = build_contextual_prompt(
                            domain=domain,
                            preceding=candidate.preceding_text[-200:] if candidate.preceding_text else "",
                            following=candidate.following_text[:200] if candidate.following_text else "",
                        )
                        for m in models[:5]:  # Try up to 5 models
                            try:
                                resp = await client.chat_completion(
                                    model=m,
                                    messages=[{"role": "user", "content": fallback_prompt}],
                                    temperature=0.7,
                                    max_tokens=2048,
                                )
                                text = resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                                if text and len(text) >= 50:
                                    model = m
                                    generator = make_generator(model)
                                    causal_trace = []  # No causal trace for fallback
                                    break
                            except Exception:
                                continue
                        if not text or len(text) < 50:
                            raise RuntimeError(f"All CONTEXTUAL approaches failed. Last error: {last_error}")

                    # Author state mutated by the process engine
                    print(dim(f"      [{ordinal}] Glucose: {author.glucose:.3f}, Fatigue: {author.visual_fatigue:.3f}"))

                else:
                    # Simpler prompt-based generation for NAIVE/TOPICAL
                    if level == InjectionLevel.NAIVE:
                        prompt = build_naive_prompt()
                    else:  # TOPICAL
                        domain = profile.discipline if profile else "academic writing"
                        topic = candidate.section_hint or "research methodology"
                        prompt = build_topical_prompt(domain, topic)

                    # Natural temperature variation (higher when fatigued)
                    base_temp = 0.6 + (author.visual_fatigue * 0.3) + doc_rng.uniform(-0.1, 0.1)
                    temperature = max(0.4, min(0.95, base_temp))

                    # Try with current model, retry with different models until success
                    # NO PLACEHOLDERS - always get real LLM output
                    text = None
                    tried_models = set()
                    available_models = models  # Config file contains only reliable models
                    current_model = model
                    last_error = None

                    max_attempts = min(len(available_models), 10)  # Try up to 10 different models
                    for attempt in range(max_attempts):
                        tried_models.add(current_model)
                        try:
                            response = await client.chat_completion(
                                model=current_model,
                                messages=[{"role": "user", "content": prompt}],
                                temperature=temperature,
                                max_tokens=2048,  # Generous buffer to prevent truncation
                                reject_truncation=True,
                            )
                            text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                            text = text.strip()
                            if len(text) >= 50:  # Minimum viable length
                                text = text[:target_text_length]
                                model = current_model  # Update for generator tracking
                                generator = make_generator(model)
                                break
                            else:
                                last_error = f"Response too short ({len(text)} chars)"
                        except (TruncationError, Exception) as e:
                            last_error = str(e)

                        # Try a different model
                        remaining = [m for m in available_models if m not in tried_models]
                        if remaining:
                            current_model = doc_rng.choice(remaining)
                        else:
                            break

                    if not text or len(text) < 50:
                        raise RuntimeError(f"All {len(tried_models)} models failed. Last error: {last_error}")

                    # Consume cognitive resources with variable syntactic depth
                    if use_cognitive:
                        syntactic_depth = get_syntactic_demand(text)
                        author.consume_resources(tokens=len(text.split()), syntactic_depth=syntactic_depth)

            except Exception as e:
                # NO PLACEHOLDERS - fail loudly so we can fix the issue
                print(error(f"    FATAL: Injection {ordinal} failed after all retries: {e}"))
                raise

            # Create injection span
            span = create_injection_span(
                candidate=candidate,
                level=level,
                trajectory_state=trajectory,
                generator=generator,
                rng_seed=text_seed,
                injected_text=text,
                ordinal=ordinal,
            )

            # Attach causal trace if available
            if causal_trace:
                span = replace(span, causal_trace=causal_trace)

            all_injections.append((span, text))

        # Log final author state for this document
        print(info(f"    Final state - Glucose: {author.glucose:.3f}, Fatigue: {author.visual_fatigue:.3f}, Tokens: {author.total_tokens_produced}"))

    return all_injections


def _write_injections(
    injections: List[tuple[InjectionSpan, str]],
    output_path: Path,
) -> None:
    """Write injections to JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for span, text in injections:
            record = {
                "span": asdict(span),
                "generated_text": text,
                "model": span.generator_class or "placeholder",
            }
            f.write(json.dumps(record) + "\n")


def _print_distribution_report(injections: List[tuple[InjectionSpan, str]]) -> None:
    """Print injection distribution statistics."""
    level_counts = Counter()
    trajectory_counts = Counter()
    doc_counts = Counter()

    for span, _ in injections:
        level_counts[span.injection_level.value if span.injection_level else "none"] += 1
        trajectory_counts[span.trajectory_state.value if span.trajectory_state else "none"] += 1
        doc_counts[span.doc_id] += 1

    print()
    print(bold("  Injection Distribution"))
    print(dim("  " + "─" * 40))

    print("  By level:")
    total = sum(level_counts.values())
    for level, count in sorted(level_counts.items()):
        pct = 100 * count / total if total > 0 else 0
        print(f"    {level}: {count} ({pct:.1f}%)")

    print()
    print("  By trajectory state:")
    for traj, count in sorted(trajectory_counts.items()):
        pct = 100 * count / total if total > 0 else 0
        print(f"    {traj}: {count} ({pct:.1f}%)")

    print()
    print("  By document:")
    for doc_id, count in sorted(doc_counts.items()):
        print(f"    {doc_id[:12]}...: {count}")

    print()
    print(f"  Total injections: {len(injections)}")


async def main() -> int:
    print_banner("Build Complete Dataset")

    parser = argparse.ArgumentParser(
        description="Build complete, balanced ScholaWrite-Augmented dataset."
    )
    parser.add_argument(
        "--seed-docs", "-i",
        type=Path,
        default=Path("data/seed/normalized/all.jsonl"),
        help="Path to normalized seed documents."
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("data/augmented/complete"),
        help="Output directory for complete dataset."
    )
    parser.add_argument(
        "--injections-per-doc",
        type=int,
        default=TARGET_INJECTIONS_PER_DOC,
        help=f"Number of injections per document (default: {TARGET_INJECTIONS_PER_DOC})."
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for generating injection text (requires OpenRouter API key)."
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=Path("configs/openrouter_models.json"),
        help="Path to OpenRouter models config."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files."
    )
    parser.add_argument(
        "--cognitive",
        action="store_true",
        default=True,
        help="Enable cognitive simulation with EmbodiedScholar and causal traces (default: True)."
    )
    parser.add_argument(
        "--no-cognitive",
        action="store_false",
        dest="cognitive",
        help="Disable cognitive simulation, use simple prompt-based generation."
    )
    args = parser.parse_args()

    # Load documents
    print()
    print(info("Loading seed documents..."))
    if not args.seed_docs.exists():
        print(error(f"Seed docs not found: {args.seed_docs}"))
        return 1

    documents = read_documents_jsonl(args.seed_docs)
    print(success(f"Loaded {len(documents)} documents"))

    total_revisions = sum(len(d.revisions) for d in documents)
    print(info(f"  Total revisions: {total_revisions:,}"))

    # Generate injections
    print()
    print(bold("  Generating Injections"))
    print(dim("  " + "─" * 40))

    client = None
    models = []

    if args.use_llm:
        # NO PLACEHOLDERS - fail loudly if LLM setup or generation fails
        client = OpenRouterClient.from_env()
        try:
            if args.models_file.exists():
                models_data = json.loads(args.models_file.read_text(encoding="utf-8"))
                # Config file contains only reliable, tested models
                models = [m["id"] for m in models_data if "id" in m]
            print(success(f"OpenRouter connected with {len(models)} models"))

            injections = await _generate_llm_injections(
                documents, client, models,
                injections_per_doc=args.injections_per_doc,
                seed=args.seed,
                use_cognitive=args.cognitive,
            )
        finally:
            if client:
                await client.close()
    else:
        # Only use placeholders when explicitly NOT using LLM
        print(warning("Running WITHOUT --use-llm: generating placeholder text only"))
        injections = _generate_diverse_injections(
            documents,
            injections_per_doc=args.injections_per_doc,
            seed=args.seed,
        )

    _print_distribution_report(injections)

    if args.dry_run:
        print()
        print(info("Dry run complete - no files written."))
        return 0

    # Write injections
    print()
    print(info("Writing injections..."))
    injections_path = args.output_dir / "injections.jsonl"
    _write_injections(injections, injections_path)
    print(success(f"Wrote {len(injections)} injections to {injections_path}"))

    # Build augmented documents
    print()
    print(bold("  Building Augmented Documents"))
    print(dim("  " + "─" * 40))

    # Convert to InjectionRecord format
    records = [InjectionRecord(span=span, injected_text=text) for span, text in injections]

    with ProgressBar(total=len(documents), description="Augmenting") as pbar:
        augmented = []
        for i, doc in enumerate(documents):
            doc_records = [r for r in records if r.span.doc_id == doc.doc_id]
            aug_docs = build_augmented([doc], doc_records, verify_insertions=True)
            augmented.extend(aug_docs)
            pbar.update(1)

    # Write augmented documents
    print()
    print(info("Writing augmented documents..."))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    docs_path = args.output_dir / "documents.jsonl"
    write_augmented_jsonl(augmented, docs_path)
    print(success(f"Wrote {len(augmented)} documents to {docs_path}"))

    # Write annotations separately
    annotations_path = args.output_dir / "annotations.jsonl"
    with open(annotations_path, "w", encoding="utf-8") as f:
        for doc in augmented:
            for rev in doc.revisions:
                for ann in rev.annotations:
                    f.write(json.dumps(asdict(ann)) + "\n")

    ann_count = sum(len(rev.annotations) for doc in augmented for rev in doc.revisions)
    print(success(f"Wrote {ann_count} annotations to {annotations_path}"))

    # Generate statistics
    stats = {
        "documents": len(augmented),
        "total_revisions": sum(len(d.revisions) for d in augmented),
        "total_injections": len(injections),
        "injections_per_doc": args.injections_per_doc,
        "level_distribution": {
            level.value: sum(1 for s, _ in injections if s.injection_level == level)
            for level in InjectionLevel
        },
        "trajectory_distribution": {
            traj.value: sum(1 for s, _ in injections if s.trajectory_state == traj)
            for traj in TrajectoryState
        },
        "seed": args.seed,
    }

    stats_path = args.output_dir / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(success(f"Wrote statistics to {stats_path}"))

    # Summary
    print()
    print(bold("  Build Complete"))
    print(dim("  " + "─" * 40))
    print(f"  Documents: {len(augmented)}")
    print(f"  Revisions: {stats['total_revisions']:,}")
    print(f"  Injections: {stats['total_injections']}")
    print(f"  Output: {args.output_dir}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
