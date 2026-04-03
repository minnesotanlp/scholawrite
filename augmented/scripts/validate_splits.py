#!/usr/bin/env python
"""CLI: validate data split integrity."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, error, success

__all__ = ["main"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that train/val/test splits are disjoint with no overlapping "
                    "document IDs across partitions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --splits data/splits/splits.json
  %(prog)s -i custom_splits.json

Expected splits.json format:
  {
    "train": ["doc_001", "doc_002", ...],
    "val": ["doc_010", "doc_011", ...],
    "test": ["doc_020", "doc_021", ...]
  }

Exit codes:
  0: Splits are disjoint (valid)
  1: Overlap detected or file not found (invalid)
"""
    )
    parser.add_argument(
        "-i", "--splits",
        type=Path,
        default=Path("data/splits/splits.json"),
        help="Path to splits JSON file containing 'train', 'val', and 'test' arrays "
             "of document IDs to validate for disjointness (default: data/splits/splits.json).",
    )
    return parser.parse_args()


def main() -> int:
    print_banner("Split Validation")
    args = parse_args()
    if not args.splits.exists():
        print(error(f"Splits file not found: {args.splits}"), file=sys.stderr)
        return 1
    data = json.loads(args.splits.read_text(encoding="utf-8"))
    train = set(data.get("train", []))
    val = set(data.get("val", []))
    test = set(data.get("test", []))

    split_pairs = [
        ("train_val", train, val),
        ("train_test", train, test),
        ("val_test", val, test),
    ]
    overlaps = {}
    with ProgressBar(total=len(split_pairs), description="Validating splits") as pbar:
        for name, s1, s2 in split_pairs:
            overlaps[name] = sorted(s1 & s2)
            pbar.update(1)

    has_overlap = any(overlaps[k] for k in overlaps)
    if has_overlap:
        print(error("Split overlap detected:"), file=sys.stderr)
        for key, items in overlaps.items():
            if items:
                print(f"  {key}: {items[:10]}", file=sys.stderr)
        return 1
    print(success("Splits are disjoint."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
