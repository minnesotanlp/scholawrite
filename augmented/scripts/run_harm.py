#!/usr/bin/env python
"""CLI: Disaggregated harm analysis using process-based predictions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scholawrite.harm import compute_harm
from scholawrite.io import read_augmented_jsonl
from scholawrite.banner import print_banner

__all__ = ["main"]

def main() -> int:
    print_banner("Disaggregated Harm Analysis")
    parser = argparse.ArgumentParser(description="Run disaggregated harm evaluation.")
    parser.add_argument("--input", "-i", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/harm"))
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input not found: {args.input}", file=sys.stderr)
        return 1
        
    print(f"Loading documents from: {args.input}")
    docs = read_augmented_jsonl(args.input)
    
    print("Computing subgroup performance (Harm Analysis)...")
    results = compute_harm(docs)
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "summary.csv"
    
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("metric,value\n")
        for k, v in sorted(results.items()): f.write(f"{k},{v}\n")
            
    print(f"Harm analysis complete. Saved to: {summary_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
