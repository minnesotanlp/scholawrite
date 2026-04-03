"""
Purpose: scripts/env_capture.py
Outputs: Comprehensive environment capture for provenance.
"""
from __future__ import annotations

import argparse
import sys
import os
import platform
import json
from pathlib import Path

from scholawrite.banner import print_banner

__all__ = ["main"]


def main() -> int:
    print_banner("Environment Capture")
    parser = argparse.ArgumentParser(
        description="Capture comprehensive environment information for reproducibility "
                    "and provenance tracking. Redacts sensitive values containing 'KEY'.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s -o env_snapshot.json
  %(prog)s --output provenance/environment.json
  %(prog)s --no-env

Output includes:
  - python: Full Python version string
  - os: Platform information (OS, version, architecture)
  - cwd: Current working directory
  - env: Environment variables (with secrets redacted)

Note: Variables containing 'KEY' in their name are automatically redacted
to prevent accidental exposure of API keys and secrets.
"""
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output path for environment JSON file. If not specified, prints to stdout."
    )
    parser.add_argument(
        "--no-env",
        action="store_true",
        help="Exclude environment variables from output (only capture python, os, cwd)."
    )
    args = parser.parse_args()

    env_info = {
        "python": sys.version,
        "os": platform.platform(),
        "cwd": os.getcwd(),
    }

    if not args.no_env:
        # Redact secrets (variables containing KEY in their name)
        env_info["env"] = {k: v for k, v in os.environ.items() if "KEY" not in k.upper()}

    output_json = json.dumps(env_info, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_json, encoding="utf-8")
        print(f"Environment captured to: {args.output}")
    else:
        print(output_json)

    return 0


if __name__ == '__main__':
    sys.exit(main())