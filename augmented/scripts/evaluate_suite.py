"""
Purpose: scripts/evaluate_suite.py
Dependencies: scholawrite.metrics, json, argparse.
Outputs: Forensic evaluation reports for Causal Process Simulation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from scholawrite.metrics import span_iou, f1
from scholawrite.banner import print_banner
from scholawrite.cli import prompt_confirm, error, success, info

__all__ = ["main"]

def _load(path: str) -> Dict[str, Dict[str, object]]:
    """Iteratively load forensic records from JSONL."""
    records = {}
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            # Forensically stable identity: doc + injection
            key = f"{rec['doc_id']}::{rec['injection_id']}"
            records[key] = rec
    return records

def main() -> int:
    print_banner("Forensic Evaluation Suite")
    parser = argparse.ArgumentParser(
        description="Evaluate model predictions against the causal process gold subset. "
                    "Computes process fidelity F1 and span IoU metrics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --gold data/gold/annotations.jsonl --pred results/predictions.jsonl --report results/eval.json
  %(prog)s --gold gold.jsonl --pred pred.jsonl --report eval_report.json

Output metrics:
  - process_fidelity_f1: F1 score for resource coupling classification (threshold: 0.6)
  - span_iou: Intersection-over-Union for predicted vs. gold span boundaries
  - records_evaluated: Number of overlapping records between gold and predictions
"""
    )
    parser.add_argument(
        "--gold",
        required=True,
        help="Path to gold standard JSONL file containing human-annotated records "
             "with doc_id, injection_id, span boundaries, and resource_coupling."
    )
    parser.add_argument(
        "--pred",
        required=True,
        help="Path to prediction results JSONL file with predicted_coupling and "
             "pred_start/pred_end span boundaries for each record."
    )
    parser.add_argument(
        "--report", "-o",
        required=True,
        help="Output path for evaluation JSON report containing computed metrics."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Computes metrics "
             "and reports them without saving the evaluation report."
    )
    args = parser.parse_args()

    out_path = Path(args.report)

    # Check for existing output file
    if out_path.exists() and not args.force and not args.dry_run:
        if not prompt_confirm(f"Overwrite {out_path}?"):
            print(info("Cancelled."))
            return 0

    gold, pred = _load(args.gold), _load(args.pred)
    common = sorted(set(gold.keys()) & set(pred.keys()))
    if not common:
        print(error("No overlapping records found for evaluation."), file=sys.stderr)
        return 1

    true_couplings, pred_couplings = [], []
    for key in common:
        g, p = gold[key], pred[key]
        # Forensic validation: resource coupling threshold
        true_couplings.append(1 if g.get("resource_coupling", 0) > 0.6 else 0)
        pred_couplings.append(1 if p.get("predicted_coupling", 0) > 0.6 else 0)

    report = {
        "process_fidelity_f1": round(f1(true_couplings, pred_couplings), 4),
        "span_iou": round(span_iou([(g["span_start_char"], g["span_end_char"]) for g in [gold[k] for k in common]],
                                    [(p.get("pred_start", 0), p.get("pred_end", 0)) for p in [pred[k] for k in common]]), 4),
        "records_evaluated": len(common),
    }

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write evaluation report to {out_path}"))
        print(info(f"  - Gold records: {len(gold)}"))
        print(info(f"  - Prediction records: {len(pred)}"))
        print(info(f"  - Overlapping records: {len(common)}"))
        print(info(f"  - Process Fidelity F1: {report['process_fidelity_f1']}"))
        print(info(f"  - Span IoU: {report['span_iou']}"))
        print(info("Dry run complete - no files modified."))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(success(f"Evaluation Complete: {args.report}"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
