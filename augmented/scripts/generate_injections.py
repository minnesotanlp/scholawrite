#!/usr/bin/env python
"""CLI: Generate raw injection candidates with Causal Process Planning (Async).
"""
from __future__ import annotations

import argparse
import json
import sys
import asyncio
import random
from pathlib import Path
from dataclasses import asdict

from scholawrite.injection import select_injection_points, create_injection_span
from scholawrite.openrouter import OpenRouterClient
from scholawrite.io import read_documents_jsonl
from scholawrite.schema import InjectionLevel, CausalEvent
from scholawrite.augment import get_doc_profile
from scholawrite.causal_core import IrreversibleProcessEngine, LexicalIntention
from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, prompt_confirm, success, info

__all__ = ["main"]

async def main() -> int:
    print_banner("Generate Forensic Injections")
    parser = argparse.ArgumentParser(
        description="Generate raw injection candidates with Causal Process Planning. "
                    "Creates synthetic injected text spans with forensic birth traces.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i data/seed/documents.jsonl -o data/augmented/injections.jsonl
  %(prog)s --input data/docs.jsonl --output injections.jsonl --provider openrouter
  %(prog)s -i docs.jsonl -o out.jsonl --workers 10 --provider openrouter
  %(prog)s -i docs.jsonl -o out.jsonl --dry-run
"""
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to source documents JSONL file containing revision histories "
             "for injection point selection."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output path for generated injection spans JSONL file, including "
             "causal traces and model metadata."
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["placeholder", "openrouter"],
        default="placeholder",
        help="Text generation provider: 'placeholder' for deterministic test text, "
             "'openrouter' for LLM-generated content (default: placeholder)."
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=Path("configs/openrouter_models.json"),
        help="Path to JSON file containing OpenRouter model configurations "
             "(default: configs/openrouter_models.json)."
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=20,
        help="Number of concurrent async workers for parallel processing. "
             "Higher values increase throughput but may hit rate limits (default: 20)."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Useful for "
             "validating input and estimating output size."
    )
    args = parser.parse_args()

    # Check for existing output file
    if args.output.exists() and not args.force and not args.dry_run:
        if not prompt_confirm(f"Overwrite {args.output}?"):
            print(info("Cancelled."))
            return 0

    documents = read_documents_jsonl(args.input)
    client, models = None, []
    if args.provider == "openrouter":
        client = OpenRouterClient.from_env()
        if args.models_file.exists():
            models_data = json.loads(args.models_file.read_text(encoding="utf-8"))
            models = [m["id"] for m in models_data if "id" in m]

    results = []
    semaphore = asyncio.Semaphore(args.workers)

    async def run_doc(doc):
        # 1. Profile document
        abstract = doc.revisions[-1].text[:1500] if doc.revisions else ""
        profile = None
        if client and models:
            profile = await get_doc_profile(client, random.choice(models), abstract)
        
        # 2. Find conceptual ruptures
        rng = random.Random(doc.doc_id)
        offsets = select_injection_points(doc, rng, max_per_doc=2)
        
        doc_results = []
        for ordinal, char_pos in enumerate(offsets):
            async with semaphore:
                m = random.choice(models) if models else "placeholder"
                rev = doc.revisions[-1]
                
                # --- Forensic Seed Generation ---
                # We execute ONE causal intention to ensure birth trace existence
                engine = IrreversibleProcessEngine(initial_glucose=1.0, discipline=profile.discipline if profile else "general_academic")
                intent = LexicalIntention(target="This approach", syntactic_depth=2.0, lexical_rarity=0.1, cognitive_cost=0.01)
                text = engine.execute(intent)
                
                # Note: LLM expansion for openrouter provider could be added here
                # using build_contextual_prompt() from scholawrite.prompts
                
                span = create_injection_span(doc.doc_id, rev.revision_id, char_pos, InjectionLevel.CONTEXTUAL, text, ordinal, m)
                
                # Manually populate the birth trace
                trace = [CausalEvent(
                    intention=e.intention.target, actual_output=e.actual_output, 
                    status="success", failure_mode=None, repair_artifact=None, 
                    glucose_at_event=e.glucose_before, latency_ms=e.latency_ms, 
                    syntactic_complexity=e.intention.syntactic_depth
                ) for e in engine.trace]
                
                # Re-create span with trace
                from dataclasses import replace
                span = replace(span, causal_trace=trace)
                
                doc_results.append((span, text, m))
        return doc_results

    print(f"Generating forensic injections for {len(documents)} documents...")
    completed = 0
    with ProgressBar(total=len(documents), description="Processing documents") as pbar:
        async def run_doc_with_progress(doc):
            nonlocal completed
            result = await run_doc(doc)
            completed += 1
            pbar.set(completed)
            return result

        tasks = [run_doc_with_progress(d) for d in documents]
        all_doc_results = await asyncio.gather(*tasks)
    for dr in all_doc_results:
        results.extend(dr)

    if client: await client.close()

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write {len(results)} injection records to {args.output}"))
        print(info(f"  - Documents processed: {len(documents)}"))
        print(info(f"  - Provider: {args.provider}"))
        print(info("Dry run complete - no files modified."))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for span, text, model_id in results:
            record = {
                "span": asdict(span),
                "generated_text": text,
                "model": model_id
            }
            f.write(json.dumps(record) + "\n")
    print(success(f"Wrote {len(results)} injection records to {args.output}"))
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
