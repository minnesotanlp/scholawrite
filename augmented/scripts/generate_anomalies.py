#!/usr/bin/env python
"""CLI: Generate process signature anomalies (Causal Inconsistency).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scholawrite.anomalies import generate_anomalies
from scholawrite.io import read_augmented_jsonl, write_augmented_jsonl
from scholawrite.banner import print_banner
from scholawrite.cli import prompt_confirm, error, success, info

__all__ = ["main"]

def main() -> int:
    print_banner("Generate Process Anomalies")
    parser = argparse.ArgumentParser(
        description="Generate biometrically-grounded process anomalies representing "
                    "causal inconsistencies in document revision histories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i data/augmented/documents.jsonl -o data/augmented/anomalies.jsonl
  %(prog)s --input docs.jsonl --output anomalies.jsonl --force
  %(prog)s -i docs.jsonl -o anomalies.jsonl --dry-run
"""
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to augmented documents JSONL file containing revision histories "
             "and causal traces for anomaly detection."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output path for generated anomaly records JSONL file with "
             "biometrically-valid process inconsistencies."
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
             "document count and estimated anomaly output."
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

    print(info("Auditing documents for causal inconsistency..."))
    docs = read_augmented_jsonl(args.input)
    anomalies = generate_anomalies(docs)

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write {len(anomalies)} anomaly records to {args.output}"))
        print(info(f"  - Input documents: {len(docs)}"))
        print(info("Dry run complete - no files modified."))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_augmented_jsonl(anomalies, args.output)
    print(success(f"Wrote biometrically-valid anomalies to: {args.output}"))
    return 0

if __name__ == "__main__":
    sys.exit(main())