#!/usr/bin/env python
"""CLI: sample gold subset candidates for human annotation.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from scholawrite.banner import print_banner
from scholawrite.cli import prompt_confirm, error, success, info

__all__ = ["main"]

def main() -> int:
    print_banner("Gold Subset Preparation")
    parser = argparse.ArgumentParser(
        description="Sample gold subset candidates from annotation records for human "
                    "validation. Uses deterministic random sampling for reproducibility.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i data/augmented/annotations.jsonl -o data/gold/candidates.jsonl
  %(prog)s --input annotations.jsonl --output gold.jsonl --size 100
  %(prog)s -i annotations.jsonl -o gold.jsonl --size 500 --seed 123
  %(prog)s -i annotations.jsonl -o gold.jsonl --dry-run

The output file contains a stratified random sample suitable for human annotation
and inter-annotator agreement studies.
"""
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to source annotations JSONL file containing records to sample from."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output path for sampled gold subset JSONL file."
    )
    parser.add_argument(
        "--size",
        type=int,
        default=200,
        help="Number of records to sample for gold subset. If the input has fewer "
             "records, all records are included (default: 200)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling. Use the same seed to regenerate "
             "identical subsets (default: 42)."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Reports "
             "sample size and output path without creating the file."
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(error(f"Input not found: {args.input}"), file=sys.stderr)
        return 1

    # Check for existing output file
    if args.output.exists() and not args.force and not args.dry_run:
        if not prompt_confirm(f"Overwrite {args.output}?"):
            print(info("Cancelled."))
            return 0

    records = []
    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        print(error("No records found in input file."), file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    sample_size = min(args.size, len(records))
    sample = rng.sample(records, sample_size)

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write {len(sample)} gold candidates to {args.output}"))
        print(info(f"  - Input records: {len(records)}"))
        print(info(f"  - Requested sample size: {args.size}"))
        print(info(f"  - Actual sample size: {sample_size}"))
        print(info(f"  - Random seed: {args.seed}"))
        print(info("Dry run complete - no files modified."))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for rec in sample:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(success(f"Wrote {len(sample)} gold candidates to {args.output}"))
    return 0

if __name__ == "__main__":
    sys.exit(main())