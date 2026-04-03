#!/usr/bin/env python
"""CLI: Scan documents and annotations for personally identifying information (PII).

This script implements the mandatory PII scan specified in docs/PROTOCOL.md
Section 11.1. It uses regex and heuristic rules to detect sensitive information.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

from scholawrite.io import read_augmented_jsonl
from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, prompt_confirm, error, warning, success, info

__all__ = ["main", "scan_text"]

# Patterns for common PII
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(\+\d{1,2}\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "ip_address": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
}

# Heuristic patterns for names and institutions
HEURISTIC_PATTERNS = {
    "potential_name": r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b",
    "potential_institution": r"\b(?:University|Institute|College|Laboratory|Dept|Department|School) of [A-Z][a-z]+\b",
    "potential_university": r"\b[A-Z][a-z]+ (?:University|Institute|College)\b",
}


def scan_text(text: str) -> List[Dict[str, str | int]]:
    """Scan a string for PII and return findings."""
    findings = []
    
    # Check exact PII patterns
    for rule_id, pattern in PII_PATTERNS.items():
        for match in re.finditer(pattern, text):
            findings.append({
                "rule_id": rule_id,
                "span_start": match.start(),
                "span_end": match.end(),
                "snippet": f"...{text[max(0, match.start()-10):min(len(text), match.end()+10)]}...",
                "severity": "high"
            })
            
    # Check heuristic patterns (potential author/affil leaks)
    for rule_id, pattern in HEURISTIC_PATTERNS.items():
        for match in re.finditer(pattern, text):
            # To reduce noise, we ignore common academic starts
            found_text = match.group()
            if found_text.startswith(("Table", "Figure", "Section", "Appendix", "Equation")):
                continue
                
            findings.append({
                "rule_id": rule_id,
                "span_start": match.start(),
                "span_end": match.end(),
                "snippet": f"...{text[max(0, match.start()-10):min(len(text), match.end()+10)]}...",
                "severity": "medium"
            })
            
    return findings


def main() -> int:
    print_banner("PII Scanner")
    parser = argparse.ArgumentParser(
        description="Scan documents and annotations for personally identifying information (PII). "
                    "Implements the mandatory PII scan specified in docs/PROTOCOL.md Section 11.1.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i data/augmented/documents.jsonl
  %(prog)s --input data/seed/documents.jsonl --output reports/pii_findings.jsonl
  %(prog)s -i docs.jsonl -o pii_report.jsonl

Detected PII types:
  - email:                Email addresses (high severity)
  - phone:                Phone numbers (high severity)
  - ssn:                  Social Security Numbers (high severity)
  - ip_address:           IP addresses (high severity)
  - potential_name:       Person names (medium severity, heuristic)
  - potential_institution: Institution names (medium severity, heuristic)
"""
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to documents JSONL file to scan for PII. Each document's "
             "revision text fields will be checked against PII patterns."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("data/augmented/pii_report.jsonl"),
        help="Output path for PII findings report in JSONL format. Each finding "
             "includes rule_id, severity, and snippet context "
             "(default: data/augmented/pii_report.jsonl)."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Scans for PII "
             "and reports findings count without creating the output file."
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

    print(info(f"Scanning {args.input} for PII..."))
    docs = read_augmented_jsonl(args.input)

    # Collect all findings for dry-run preview or actual write
    all_findings = []
    with ProgressBar(total=len(docs), description="Scanning documents") as pbar:
        for doc in docs:
            for rev in doc.revisions:
                findings = scan_text(rev.text)
                if findings:
                    for finding in findings:
                        report_rec = {
                            "record_id": rev.revision_id,
                            "doc_id": doc.doc_id,
                            "field": "text",
                            **finding,
                            "action": "review"
                        }
                        all_findings.append(report_rec)
            pbar.update(1)

    # Dry-run mode: preview what would be written
    if args.dry_run:
        high_severity = sum(1 for f in all_findings if f.get("severity") == "high")
        medium_severity = sum(1 for f in all_findings if f.get("severity") == "medium")
        print(info(f"Would write {len(all_findings)} PII findings to {args.output}"))
        print(info(f"  - Documents scanned: {len(docs)}"))
        print(info(f"  - High severity findings: {high_severity}"))
        print(info(f"  - Medium severity findings: {medium_severity}"))
        print(info("Dry run complete - no files modified."))
        return 1 if all_findings else 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f_out:
        for report_rec in all_findings:
            f_out.write(json.dumps(report_rec) + "\n")

    if all_findings:
        print(warning(f"Found {len(all_findings)} potential PII instances. See {args.output}"))
        return 1
    else:
        print(success("No PII detected."))
        return 0


if __name__ == "__main__":
    sys.exit(main())
