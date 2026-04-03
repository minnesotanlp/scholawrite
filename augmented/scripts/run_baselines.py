#!/usr/bin/env python
"""CLI: Run process-granular baselines including Causal Coupling AUC.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scholawrite.baselines import run_baselines
from scholawrite.io import read_augmented_jsonl
from scholawrite.banner import print_banner
from scholawrite.cli import prompt_confirm, error, success, info

__all__ = ["main"]

def main() -> int:
    print_banner("Process-Granular Baselines")
    parser = argparse.ArgumentParser(
        description="Run forensic process-aware baselines including Causal Coupling AUC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i data/augmented/documents.jsonl
  %(prog)s --input data/augmented/documents.jsonl --output-dir results/exp1
  %(prog)s -i data/augmented/documents.jsonl --threshold 0.5
  %(prog)s -i docs.jsonl --dry-run
"""
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to augmented documents JSONL file containing revision histories "
             "and causal traces for baseline evaluation."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/baselines"),
        help="Directory for output files including summary.csv and results.json "
             "(default: results/baselines)."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="NCD classification threshold for computing F1 scores. Higher values "
             "increase precision but decrease recall (default: 0.45, typical range: 0.3-0.6)."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Runs baselines "
             "and reports results without saving to disk."
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(error(f"Input not found: {args.input}"), file=sys.stderr)
        return 1

    summary_path = args.output_dir / "summary.csv"
    json_path = args.output_dir / "results.json"

    # Check for existing output files
    existing_outputs = []
    if summary_path.exists():
        existing_outputs.append(summary_path)
    if json_path.exists():
        existing_outputs.append(json_path)

    if existing_outputs and not args.force and not args.dry_run:
        files_str = ", ".join(str(p) for p in existing_outputs)
        if not prompt_confirm(f"Overwrite {files_str}?"):
            print(info("Cancelled."))
            return 0

    print(info(f"Loading documents from: {args.input}"))
    docs = read_augmented_jsonl(args.input)

    print(info("Executing Causal Signature Baselines..."))
    results = run_baselines(docs, threshold=args.threshold)

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write results to {args.output_dir}:"))
        print(info(f"  - {summary_path}"))
        print(info(f"  - {json_path}"))
        print(info(f"  - Documents evaluated: {len(docs)}"))
        print(info(f"  - Threshold: {args.threshold}"))
        print(info(f"  - Overall F1: {results.get('overall_f1', 0):.4f}"))
        for k, v in sorted(results.items()):
            if k != 'overall_f1':
                print(info(f"  - {k}: {v}"))
        print(info("Dry run complete - no files modified."))
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("metric,value\n")
        for k, v in sorted(results.items()):
            f.write(f"{k},{v}\n")

    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(success(f"Results (Overall F1: {results.get('overall_f1', 0):.4f})"))
    print(success(f"Saved to: {args.output_dir}"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
