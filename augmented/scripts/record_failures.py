# CLI: record failed cases.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scholawrite.banner import print_banner
from scholawrite.cli import success, info

__all__ = ["main"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record and normalize failure cases from pipeline execution to "
                    "a standardized JSONL format for analysis and debugging.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i logs/failures_raw.jsonl -o data/failures.jsonl
  %(prog)s --input pipeline_errors.jsonl --output recorded_failures.jsonl

If the input file does not exist, an empty output file is created. This allows
the script to be safely included in pipelines where failures may not occur.
"""
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to input JSONL file containing raw failure records from "
             "pipeline execution. Each line should be a valid JSON object."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output path for normalized failure records JSONL file. Records "
             "are re-serialized with ensure_ascii=False for proper Unicode support."
    )
    return parser.parse_args()


def main() -> int:
    print_banner("Record Failures")
    args = parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not inp.exists():
        out.write_text("", encoding="utf-8")
        print(info(f"Input not found, created empty output: {out}"))
        return 0
    count = 0
    with inp.open("r", encoding="utf-8") as f_in, out.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            if not line.strip():
                continue
            record = json.loads(line)
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(success(f"Recorded {count} failures to: {out}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
