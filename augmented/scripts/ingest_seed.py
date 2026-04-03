#!/usr/bin/env python
"""CLI: Ingest ScholaWrite seed dataset into normalized format.

This script loads raw ScholaWrite parquet data and writes normalized
SeedDocument structures to JSONL format for downstream processing.

Usage:
    uv run python scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --output data/seed/normalized/seed.jsonl
    uv run python scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --split test_small --output data/seed/normalized/test_small.jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scholawrite.io import load_seed, load_seed_split, write_documents_jsonl
from scholawrite.banner import print_banner
from scholawrite.cli import error, success, info

__all__ = ["main"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest ScholaWrite seed data into normalized JSONL format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Load all data (concatenated splits)
    uv run python scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --output data/seed/normalized/all.jsonl

    # Load specific split
    uv run python scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --split test_small --output data/seed/normalized/test_small.jsonl

    # Dry run (no output file)
    uv run python scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --split test_small --dry-run
        """,
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to HuggingFace dataset directory containing parquet files.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=False,
        help="Output path for normalized JSONL file. Parent directories will be created.",
    )
    parser.add_argument(
        "--split",
        "-s",
        type=str,
        choices=["test_small", "test", "train", "all_sorted"],
        default=None,
        help="Specific split to load. If not specified, loads all parquet files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and validate data without writing output file.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed information about loaded documents.",
    )
    return parser.parse_args()


def main() -> int:
    print_banner("Ingest ScholaWrite Seed Data")
    args = parse_args()

    # Validate input path
    if not args.input.exists():
        print(error(f"Input path does not exist: {args.input}"), file=sys.stderr)
        return 1

    # Validate output requirement
    if not args.dry_run and args.output is None:
        print(error("--output is required unless --dry-run is specified."), file=sys.stderr)
        return 1

    # Load data
    print(info(f"Loading seed data from: {args.input}"))
    if args.split:
        print(f"  Split: {args.split}")
        documents = load_seed_split(args.input, split=args.split)
    else:
        print("  Split: all (concatenated)")
        documents = load_seed(args.input)

    # Print summary
    total_revisions = sum(len(doc.revisions) for doc in documents)
    print(info(f"Loaded {len(documents)} documents with {total_revisions} total revisions"))

    if args.verbose:
        print("\nDocument details:")
        for doc in documents:
            rev_count = len(doc.revisions)
            first_ts = doc.revisions[0].timestamp if doc.revisions else "N/A"
            last_ts = doc.revisions[-1].timestamp if doc.revisions else "N/A"
            print(f"  {doc.doc_id}: {rev_count} revisions ({first_ts} → {last_ts})")

    # Write output
    if args.dry_run:
        print(info("Dry run complete (no output written)."))
    else:
        print(info(f"Writing output to: {args.output}"))
        write_documents_jsonl(documents, args.output)
        print(success(f"Wrote {len(documents)} documents to JSONL."))

    return 0


if __name__ == "__main__":
    sys.exit(main())
