"""
Purpose: scripts/hash_artifacts.py
Dependencies: hashlib, json, argparse, pathlib.
Outputs: Forensic checksums and run manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict

from scholawrite.banner import print_banner
from scholawrite.cli import ProgressBar, prompt_confirm, success, info

__all__ = ["main"]

DEFAULT_ARTIFACTS = [
    "data/augmented/documents.jsonl",
    "data/augmented/annotations.jsonl",
    "data/augmented/anomalies.jsonl",
    "data/augmented/stats.json",
]

def _hash_file(path: Path) -> str:
    """Compute SHA-256 for a file chunk-by-chunk."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"

def main() -> int:
    print_banner("Forensic Artifact Checksums")
    parser = argparse.ArgumentParser(
        description="Generate SHA-256 checksums for data artifacts to ensure "
                    "reproducibility and provenance tracking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --output results/checksums.txt --manifest results/manifest.json
  %(prog)s --artifacts "data/docs.jsonl,data/annotations.jsonl"
  %(prog)s --dry-run

Default artifacts (when --artifacts not specified):
  - data/augmented/documents.jsonl
  - data/augmented/annotations.jsonl
  - data/augmented/anomalies.jsonl
  - data/augmented/stats.json
"""
    )
    parser.add_argument(
        "-o", "--output",
        default="data/augmented/checksums.txt",
        help="Output path for checksums text file in standard checksum format "
             "(default: data/augmented/checksums.txt)."
    )
    parser.add_argument(
        "--manifest",
        default="data/augmented/manifest.json",
        help="Output path for JSON manifest containing artifact checksums "
             "(default: data/augmented/manifest.json)."
    )
    parser.add_argument(
        "--artifacts",
        default="",
        help="Comma-separated list of artifact paths to hash. If not specified, "
             "uses the default artifact list for the augmented dataset."
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing output files without prompting for confirmation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without writing any files. Shows "
             "which artifacts would be hashed and output file paths."
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    manifest_path = Path(args.manifest)

    # Check for existing output files
    existing_outputs = []
    if out_path.exists():
        existing_outputs.append(out_path)
    if manifest_path.exists():
        existing_outputs.append(manifest_path)

    if existing_outputs and not args.force and not args.dry_run:
        files_str = ", ".join(str(p) for p in existing_outputs)
        if not prompt_confirm(f"Overwrite {files_str}?"):
            print(info("Cancelled."))
            return 0

    artifacts = DEFAULT_ARTIFACTS
    if args.artifacts:
        artifacts = [a.strip() for a in args.artifacts.split(",") if a.strip()]

    checksums: Dict[str, str] = {}
    existing_artifacts = [a for a in artifacts if Path(a).exists()]
    with ProgressBar(total=len(existing_artifacts), description="Hashing files") as pbar:
        for rel_path in existing_artifacts:
            path = Path(rel_path)
            checksums[rel_path] = _hash_file(path)
            pbar.update(1)

    # Dry-run mode: preview what would be written
    if args.dry_run:
        print(info(f"Would write checksums for {len(checksums)} artifacts:"))
        for artifact, checksum in checksums.items():
            print(info(f"  - {artifact}: {checksum[:30]}..."))
        print(info(f"Would write checksum file to: {out_path}"))
        print(info(f"Would write manifest to: {manifest_path}"))
        print(info("Dry run complete - no files modified."))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for p, d in checksums.items(): f.write(f"{d}  {p}\n")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"artifacts": checksums}, indent=2), encoding="utf-8")
    print(success(f"Manifest written to: {args.manifest}"))
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())