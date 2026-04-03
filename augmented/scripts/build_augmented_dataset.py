#!/usr/bin/env python
"""Build augmented dataset with full Irreversible Process Simulation.

Run without arguments for interactive mode, or use CLI args for automation.
Models are dynamically discovered from OpenRouter API at runtime.
"""
from __future__ import annotations

import argparse
import json
import asyncio
import sys
import time
from pathlib import Path
from typing import List, Optional

from scholawrite.augment import build_augmented
from scholawrite.io import write_augmented_jsonl
from scholawrite.openrouter import OpenRouterClient
from scholawrite.models import discover_models
from scholawrite.schema import (
    InjectionSpan, SeedRevision, SeedDocument, CausalEvent,
    Label, InjectionLevel, TrajectoryState, AmbiguityFlag
)
from scholawrite.banner import print_banner
from scholawrite.cli import (
    ProgressBar, prompt_path, prompt_confirm,
    success, error, warning, info, dim, bold, style, Style
)


def _read_injections(path: Path) -> List[InjectionSpan]:
    """Read injection spans from JSONL file."""
    records = []
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)["span"]
                causal = [CausalEvent(**e) for e in data.get("causal_trace", [])]
                span = InjectionSpan(
                    doc_id=data["doc_id"],
                    revision_id=data["revision_id"],
                    injection_id=data["injection_id"],
                    injection_level=InjectionLevel(data["injection_level"]) if data["injection_level"] else None,
                    trajectory_state=TrajectoryState(data["trajectory_state"]) if data["trajectory_state"] else None,
                    ambiguity_flag=AmbiguityFlag(data["ambiguity_flag"]),
                    span_start_char=data["span_start_char"],
                    span_end_char=data["span_end_char"],
                    span_start_sentence=data["span_start_sentence"],
                    span_end_sentence=data["span_end_sentence"],
                    generator_class=data["generator_class"],
                    prompt_hash=data["prompt_hash"],
                    rng_seed=data["rng_seed"],
                    provenance_hash=data["provenance_hash"],
                    label=Label(data["label"]),
                    causal_trace=causal
                )
                records.append(span)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(error(f"Line {line_num}: Failed to parse injection - {e}"))
    return records


def _count_lines(path: Path) -> int:
    """Count lines in a file efficiently."""
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def interactive_mode() -> tuple[Path, Path, Path, bool]:
    """Run interactive prompts to gather parameters."""
    print()
    print(bold("  Configure Build Parameters"))
    print(dim("  ─" * 30))
    print()

    seed_path = prompt_path(
        "Seed documents JSONL",
        default=Path("data/seed/documents.jsonl"),
        must_exist=True,
    )
    if not seed_path:
        sys.exit(1)

    injections_path = prompt_path(
        "Injections JSONL",
        default=Path("data/injections/spans.jsonl"),
        must_exist=True,
    )
    if not injections_path:
        sys.exit(1)

    output_dir = prompt_path(
        "Output directory",
        default=Path("data/augmented"),
    )
    if not output_dir:
        sys.exit(1)

    use_openrouter = prompt_confirm("Use OpenRouter for LLM simulation?", default=False)

    print()
    return seed_path, injections_path, output_dir, use_openrouter


async def _discover_and_select_models(
    client: OpenRouterClient,
    count: int = 12,
    max_per_vendor: int = 3,
    cost_limit: Optional[float] = None,
) -> List[str]:
    """Discover available models and select a diverse set.

    Args:
        client: OpenRouter client (for API key)
        count: Target number of models to select
        max_per_vendor: Maximum models from any single vendor
        cost_limit: Optional cost limit per 1k tokens

    Returns:
        List of model IDs
    """
    registry = await discover_models()

    # Select diverse set of models
    models = registry.select_diverse_set(
        count=count,
        max_per_vendor=max_per_vendor,
        include_budget=True,
        cost_limit_per_1k=cost_limit,
    )

    return models


async def run_build(
    seed_path: Path,
    injections_path: Path,
    output_dir: Path,
    use_openrouter: bool = False,
    model_count: int = 12,
    cost_limit: Optional[float] = None,
) -> int:
    """Run the augmented dataset build with progress tracking.

    Args:
        seed_path: Path to seed documents JSONL
        injections_path: Path to injections JSONL
        output_dir: Output directory for augmented dataset
        use_openrouter: Whether to use OpenRouter for LLM simulation
        model_count: Number of models to discover and use
        cost_limit: Optional cost limit per 1k tokens

    Returns:
        Exit code (0 for success, non-zero for failure)
    """

    # Load injections
    print()
    info("Loading injections...")
    injections = _read_injections(injections_path)
    if not injections:
        print(warning("No injections found. Will create documents without injections."))
    else:
        print(success(f"Loaded {len(injections)} injections"))

    # Count total documents
    info("Counting documents...")
    total_docs = _count_lines(seed_path)
    print(success(f"Found {total_docs} documents to process"))

    # Setup OpenRouter with dynamic model discovery
    client, models = None, []
    if use_openrouter:
        try:
            client = OpenRouterClient.from_env()

            # Dynamic model discovery
            info("Discovering available models...")
            models = await _discover_and_select_models(
                client=client,
                count=model_count,
                cost_limit=cost_limit,
            )

            if not models:
                print(error("No suitable models found"))
                return 1

            print(success(f"Selected {len(models)} models dynamically:"))
            # Show first few models
            for i, m in enumerate(models[:5]):
                print(f"    {dim(m)}")
            if len(models) > 5:
                print(f"    {dim(f'... and {len(models) - 5} more')}")

        except Exception as e:
            print(error(f"Failed to connect to OpenRouter: {e}"))
            return 1

    # Prepare output - clear existing file for fresh build
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "documents.jsonl"

    # Check for already processed documents (resume support)
    processed = set()
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    processed.add(json.loads(line)["doc_id"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        if processed:
            print(info(f"Resuming: {len(processed)} documents already processed"))

    remaining = total_docs - len(processed)
    if remaining == 0:
        print(success("All documents already processed!"))
        return 0

    # Process documents with progress bar
    print()
    print(bold(f"  Processing {remaining} documents"))
    print()

    start_time = time.time()
    completed = 0
    failed = 0
    failed_docs = []

    try:
        with open(seed_path, "r", encoding="utf-8") as f_in:
            with ProgressBar(total=remaining, description="Building") as pbar:
                for line_num, line in enumerate(f_in, 1):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"\n{error(f'Line {line_num}: Invalid JSON - {e}')}")
                        failed += 1
                        failed_docs.append((line_num, "Invalid JSON", str(e)))
                        pbar.update(1)
                        continue

                    doc_id = data.get("doc_id", f"unknown_{line_num}")
                    if doc_id in processed:
                        continue

                    try:
                        doc = SeedDocument(doc_id, [SeedRevision(**r) for r in data["revisions"]])
                        augmented = await build_augmented([doc], injections, client, models)

                        if augmented:
                            write_augmented_jsonl([augmented[0]], out_path)
                            completed += 1
                        else:
                            failed += 1
                            failed_docs.append((line_num, doc_id, "build_augmented returned empty"))

                    except KeyError as e:
                        print(f"\n{error(f'Doc {doc_id}: Missing field - {e}')}")
                        failed += 1
                        failed_docs.append((line_num, doc_id, f"Missing field: {e}"))
                    except Exception as e:
                        print(f"\n{error(f'Doc {doc_id}: {type(e).__name__} - {e}')}")
                        failed += 1
                        failed_docs.append((line_num, doc_id, f"{type(e).__name__}: {e}"))

                    pbar.update(1)

    except KeyboardInterrupt:
        print(f"\n\n{warning('Interrupted by user')}")
        print(info(f"Progress saved. {completed} documents completed, can resume later."))
        return 130
    finally:
        if client:
            await client.close()

    # Summary
    elapsed = time.time() - start_time
    print()
    print(bold("  Build Summary"))
    print(dim("  ─" * 30))
    print(f"  {style('Completed:', Style.GREEN)} {completed}")
    if failed > 0:
        print(f"  {style('Failed:', Style.RED)} {failed}")
    print(f"  {style('Time:', Style.CYAN)} {_format_time(elapsed)}")
    if completed > 0:
        avg_time = elapsed / completed
        print(f"  {style('Avg/doc:', Style.CYAN)} {avg_time:.2f}s")
    print(f"  {style('Output:', Style.DIM)} {out_path}")
    print(f"  {style('Models used:', Style.DIM)} {len(models)}")

    # Report failures
    if failed_docs:
        print()
        print(bold("  Failures"))
        print(dim("  ─" * 30))
        for line_num, doc_id, reason in failed_docs[:10]:  # Show first 10
            print(f"  Line {line_num}: {doc_id}")
            print(f"    {dim(reason)}")
        if len(failed_docs) > 10:
            print(f"  ... and {len(failed_docs) - 10} more failures")

        # Write failures to file
        failures_path = output_dir / "build_failures.jsonl"
        with open(failures_path, "w", encoding="utf-8") as f:
            for line_num, doc_id, reason in failed_docs:
                f.write(json.dumps({"line": line_num, "doc_id": doc_id, "error": reason}) + "\n")
        print(f"\n  {info(f'Full failure log: {failures_path}')}")

    print()
    return 0 if failed == 0 else 1


async def main() -> int:
    print_banner("Build Augmented Dataset")

    parser = argparse.ArgumentParser(
        description="Build augmented dataset with process simulation.",
        epilog="Run without arguments for interactive mode. Models are discovered dynamically from OpenRouter."
    )
    parser.add_argument("--seed-docs", type=Path, help="Seed documents JSONL")
    parser.add_argument("--injections", type=Path, help="Injections JSONL")
    parser.add_argument("--output-dir", type=Path, help="Output directory")
    parser.add_argument("--openrouter", action="store_true", help="Use OpenRouter for simulation")
    parser.add_argument("--model-count", type=int, default=12, help="Number of models to use (default: 12)")
    parser.add_argument("--cost-limit", type=float, help="Cost limit per 1k tokens (optional)")
    args = parser.parse_args()

    # Interactive mode if no arguments provided
    if not args.seed_docs:
        seed_path, injections_path, output_dir, use_openrouter = interactive_mode()

        print()
        if not prompt_confirm("Start build?"):
            print(dim("  Cancelled."))
            return 0

        model_count = args.model_count
        cost_limit = args.cost_limit
    else:
        # Validate CLI arguments
        if not args.seed_docs.exists():
            print(error(f"Seed docs not found: {args.seed_docs}"))
            return 1
        if not args.injections.exists():
            print(error(f"Injections not found: {args.injections}"))
            return 1

        seed_path = args.seed_docs
        injections_path = args.injections
        output_dir = args.output_dir or Path("data/augmented")
        use_openrouter = args.openrouter
        model_count = args.model_count
        cost_limit = args.cost_limit

    return await run_build(
        seed_path=seed_path,
        injections_path=injections_path,
        output_dir=output_dir,
        use_openrouter=use_openrouter,
        model_count=model_count,
        cost_limit=cost_limit,
    )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
