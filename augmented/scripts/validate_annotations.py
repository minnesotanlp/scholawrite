"""
Purpose: scripts/validate_annotations.py
Dependencies: scholawrite.annotations, scholawrite.io.
Outputs: Mandatory Forensic Integrity Validation for Causal Traces.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scholawrite.annotations import (
    validate_annotations,
    validate_all_leakage,
    verify_all_spans_content,
)
from scholawrite.io import read_augmented_jsonl
from scholawrite.banner import print_banner

__all__ = ["main"]

def main() -> int:
    print_banner("Forensic Integrity Validation")
    parser = argparse.ArgumentParser(description="Validate forensic integrity of augmented documents.")
    parser.add_argument("--input", "-i", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any forensic violation.")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--skip-earned-ambiguity", action="store_true",
                        help="Skip earned ambiguity validation (already included in main validation).")
    parser.add_argument("--check-leakage", action="store_true",
                        help="Check for prompt leakage patterns in injected text content.")
    parser.add_argument("--leakage-only", action="store_true",
                        help="Only run leakage detection (skip other validations).")
    parser.add_argument("--verify-content", action="store_true",
                        help="Verify that injected spans reference valid, non-empty content.")
    parser.add_argument("--content-only", action="store_true",
                        help="Only run span content verification (skip other validations).")
    args = parser.parse_args()

    if not args.input.exists(): return 1

    print(f"Loading dataset for forensic audit: {args.input}")
    docs = list(read_augmented_jsonl(args.input))

    # Run leakage-only mode if requested
    if args.leakage_only:
        print("Running Prompt Leakage Detection Only...")
        leakage_result = validate_all_leakage(docs)

        print(f"\nLeakage Scan Summary:")
        print(f"  Spans Checked: {leakage_result.spans_checked}")
        print(f"  Spans with Leakage: {leakage_result.spans_with_leakage}")
        print(f"  Total Leakage Errors: {len(leakage_result.errors)}")

        if leakage_result.pattern_counts:
            print("\nLeakage Patterns Detected:")
            sorted_patterns = sorted(
                leakage_result.pattern_counts.items(),
                key=lambda x: -x[1]
            )
            for pattern, count in sorted_patterns[:15]:
                print(f"    {pattern}: {count}")
            if len(sorted_patterns) > 15:
                print(f"    ... and {len(sorted_patterns) - 15} more patterns")

        if not leakage_result.is_clean:
            print("\nSample Leakage Errors:")
            for i, err in enumerate(leakage_result.errors[:10]):
                print(f"  {i+1}. {err}")
            if len(leakage_result.errors) > 10:
                print(f"  ... and {len(leakage_result.errors) - 10} more.")

            if args.strict:
                return 1
        else:
            print("\nNo prompt leakage detected. Content appears clean.")

        return 0

    # Run content-only mode if requested
    if args.content_only:
        print("Running Span Content Verification Only...")
        content_result = verify_all_spans_content(docs)

        print(f"\nSpan Content Verification Summary:")
        print(f"  Documents Checked: {content_result.documents_checked}")
        print(f"  Revisions Checked: {content_result.revisions_checked}")
        print(f"  Spans Verified: {content_result.spans_verified}")
        print(f"  Spans Failed: {content_result.spans_failed}")
        if content_result.spans_verified > 0:
            print(f"  Failure Rate: {content_result.failure_rate:.1%}")

        if not content_result.is_valid:
            print("\nSpan Content Errors Detected:")
            for i, err in enumerate(content_result.errors[:20]):
                print(f"  {i+1}. {err}")
            if len(content_result.errors) > 20:
                print(f"  ... and {len(content_result.errors) - 20} more errors.")

            if args.strict:
                return 1
        else:
            print("\nAll injection spans reference valid, non-empty content.")

        return 0

    print("Running Causal Signature Validation (Irreversibility & Coupling)...")
    print("  - Validating span boundaries and overlaps")
    print("  - Validating trajectory-ambiguity consistency")
    print("  - Validating earned ambiguity (causal trace requirements)")
    print("  - Validating trajectory monotonicity (COLD -> WARM -> ASSIMILATED)")
    if args.check_leakage:
        print("  - Checking for prompt leakage in injected content")
    if args.verify_content:
        print("  - Verifying span content (post-insertion verification)")
    result = validate_annotations(docs, check_leakage=args.check_leakage)

    # Count errors by type for detailed reporting
    error_types: dict[str, int] = {}
    for err in result.errors:
        error_types[err.error_type] = error_types.get(err.error_type, 0) + 1

    print(f"\nAudit Summary:")
    print(f"  Documents: {result.documents_checked}")
    print(f"  Revisions: {result.revisions_checked}")
    print(f"  Spans Audited: {result.spans_checked}")
    print(f"  Forensic Errors: {len(result.errors)}")

    # Run span content verification if requested
    content_result = None
    if args.verify_content:
        content_result = verify_all_spans_content(docs)
        print(f"\nSpan Content Verification:")
        print(f"  Spans Verified: {content_result.spans_verified}")
        print(f"  Spans Failed: {content_result.spans_failed}")
        if content_result.spans_verified > 0:
            print(f"  Failure Rate: {content_result.failure_rate:.1%}")

        # Add content verification errors to the error types
        for err in content_result.errors:
            error_types[err.error_type] = error_types.get(err.error_type, 0) + 1

    if error_types:
        print("\nErrors by Type:")
        for etype, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"    {etype}: {count}")

    # Combine all errors for display
    all_errors = list(result.errors)
    if content_result is not None:
        all_errors.extend(content_result.errors)

    has_errors = len(all_errors) > 0

    if has_errors:
        print("\nForensic Violations Detected:")
        for i, err in enumerate(all_errors[:20]):
            print(f"  {i+1}. {err}")
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors)-20} more errors.")

        if args.strict:
            return 1
    else:
        print("\nAll process signatures within human empirical bounds.")

    return 0

if __name__ == "__main__":
    sys.exit(main())