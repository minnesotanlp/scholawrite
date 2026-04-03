#!/usr/bin/env python
"""CLI: Validate data integrity and scan for PII.

This script acts as the single entrypoint for data quality checks,
orchestrating both annotation validation and PII scanning.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, error, warning, info

__all__ = ["main"]


def run_script(script_path: str, args_list: list[str]) -> bool:
    cmd = ["uv", "run", "python", script_path] + args_list
    print(info(f"Executing: {' '.join(cmd)}"))
    result = subprocess.run(cmd)
    return result.returncode == 0


def main() -> int:
    print_banner("Data Linting Tool")
    parser = argparse.ArgumentParser(
        description="Validate data integrity and scan for PII. This script acts as the "
                    "single entrypoint for data quality checks, orchestrating annotation "
                    "validation and optional PII scanning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s -i data/augmented
  %(prog)s --input-dir data/augmented --pii-scan
  %(prog)s -i custom_data/ --pii-scan

Validation steps:
  1. Annotation validation (always runs if annotations.jsonl exists)
  2. PII scan (optional, enabled with --pii-scan flag)

Exit codes:
  0: All validations passed
  1: One or more validations failed or required files missing
"""
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=Path,
        default=Path("data/augmented"),
        help="Directory containing augmented artifacts to validate. Should contain "
             "annotations.jsonl and optionally documents.jsonl (default: data/augmented)."
    )
    parser.add_argument(
        "--pii-scan",
        action="store_true",
        help="Include PII scan in validation. Requires documents.jsonl to exist in "
             "the input directory. Generates a pii_report.jsonl with findings."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output including all validation commands being executed."
    )
    args = parser.parse_args()

    success = True

    # Build list of validation steps
    steps = []
    ann_path = args.input_dir / "annotations.jsonl"
    if ann_path.exists():
        steps.append(("Validate annotations", "scripts/validate_annotations.py", ["--input", str(ann_path)]))
    else:
        print(warning(f"annotations.jsonl not found in {args.input_dir}"))

    if args.pii_scan:
        doc_path = args.input_dir / "documents.jsonl"
        if doc_path.exists():
            report_path = args.input_dir / "pii_report.jsonl"
            steps.append(("PII scan", "scripts/pii_scan.py", ["--input", str(doc_path), "--output", str(report_path)]))
        else:
            print(error(f"documents.jsonl not found for PII scan in {args.input_dir}"), file=sys.stderr)
            success = False

    # Run validation steps with progress
    if steps:
        with ProgressBar(total=len(steps), description="Linting data") as pbar:
            for step_name, script_path, script_args in steps:
                print(f"\n[{step_name}]")
                if not run_script(script_path, script_args):
                    success = False
                pbar.update(1)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())