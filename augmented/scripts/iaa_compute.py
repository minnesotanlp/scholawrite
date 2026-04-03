"""
Purpose: scripts/iaa_compute.py
Dependencies: json, argparse, pathlib.
Outputs: Inter-annotator agreement metrics (Kappa, IoU).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, prompt_confirm, error, success, info

__all__ = ["main"]

def _load(path: Path) -> Dict[str, dict]:
    records = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            key = f"{rec['doc_id']}::{rec['revision_id']}::{rec['injection_id']}"
            records[key] = rec
    return records

def _kappa(pairs: List[List[str]]) -> float:
    """Compute Cohen's Kappa for the first two annotators."""
    if not pairs or len(pairs[0]) < 2: return 0.0
    l1, l2 = [p[0] for p in pairs], [p[1] for p in pairs]
    cats = sorted(set(l1) | set(l2))
    total = len(l1)
    p0 = sum(1 for a, b in zip(l1, l2) if a == b) / total
    pe = sum((l1.count(c)/total) * (l2.count(c)/total) for c in cats)
    return (p0 - pe) / (1 - pe) if pe < 1 else 0.0

def main() -> int:
    print_banner("Inter-Annotator Agreement")
    parser = argparse.ArgumentParser(
        description="Compute inter-annotator agreement metrics (Cohen's Kappa) for "
                    "trajectory state annotations across multiple annotators.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --inputs annotator1.jsonl,annotator2.jsonl --report iaa_report.json
  %(prog)s --inputs a1.jsonl,a2.jsonl,a3.jsonl -o results/iaa.json
  %(prog)s -i a1.jsonl,a2.jsonl -o report.json --dry-run

Output metrics:
  - num_records: Number of overlapping records across all input files
  - trajectory_kappa: Cohen's Kappa for trajectory_state agreement (pairwise)

Note: Records are matched by composite key (doc_id::revision_id::injection_id).
"""
    )
    parser.add_argument(
        "-i", "--inputs",
        required=True,
        help="Comma-separated list of annotation JSONL file paths. Each file "
             "should contain records with doc_id, revision_id, injection_id, "
             "and trajectory_state fields. Example: 'ann1.jsonl,ann2.jsonl'"
    )
    parser.add_argument(
        "-o", "--report",
        required=True,
        help="Output path for IAA report JSON file containing computed agreement metrics."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Computes agreement "
             "metrics and reports them without saving the output file."
    )
    args = parser.parse_args()

    out = Path(args.report)

    # Check for existing output file
    if out.exists() and not args.force and not args.dry_run:
        if not prompt_confirm(f"Overwrite {out}?"):
            print(info("Cancelled."))
            return 0

    paths = [Path(p.strip()) for p in args.inputs.split(",") if p.strip()]

    print(info(f"Loading {len(paths)} annotation files..."))
    data = []
    with ProgressBar(total=len(paths), description="Loading files") as pbar:
        for p in paths:
            data.append(_load(p))
            pbar.update(1)

    keys = set.intersection(*(set(d.keys()) for d in data))

    if not keys:
        print(error("No overlapping records found across annotation files"), file=sys.stderr)
        return 1

    print(info(f"Computing agreement for {len(keys)} records..."))
    trajectories = []
    with ProgressBar(total=len(keys), description="Processing records") as pbar:
        for k in keys:
            trajectories.append([d[k]["trajectory_state"] for d in data])
            pbar.update(1)

    report = {
        "num_records": len(keys),
        "trajectory_kappa": round(_kappa(trajectories), 4),
    }

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write IAA report to {out}"))
        print(info(f"  - Annotation files: {len(paths)}"))
        print(info(f"  - Overlapping records: {len(keys)}"))
        print(info(f"  - Trajectory Kappa: {report['trajectory_kappa']}"))
        print(info("Dry run complete - no files modified."))
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(success(f"IAA Report written: {args.report}"))
    return 0

if __name__ == "__main__":
    sys.exit(main())