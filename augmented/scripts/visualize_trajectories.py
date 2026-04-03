"""
Purpose: scripts/visualize_trajectories.py
Dependencies: scholawrite.io, scholawrite.visualization, argparse.
Outputs: Forensic visualization of process-coupled trajectories.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scholawrite.io import read_augmented_jsonl
from scholawrite.banner import print_banner
from scholawrite.visualization import (
    generate_html_visualization,
    generate_terminal_visualization,
    generate_tex_report,
    get_citation_info,
)
from scholawrite.cli import success, error, info, dim, Spinner


def main():
    print_banner("Trajectory Visualizer")

    parser = argparse.ArgumentParser(
        description="Generate forensic visualizations of AI-generated text trajectories."
    )
    parser.add_argument("--input", "-i", type=Path, help="Input JSONL file")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--format", "-f", choices=["html", "tex", "terminal"], default="html")
    parser.add_argument("--max-docs", "-n", type=int, default=50)
    parser.add_argument("--cite", action="store_true", help="Show citation info")
    parser.add_argument("--cite-format", choices=["bibtex", "apa", "mla", "all"], default="all")

    args = parser.parse_args()

    if args.cite:
        print(get_citation_info(args.cite_format))
        return

    if not args.input:
        error("--input required")
        sys.exit(1)

    if not args.input.exists():
        error(f"File not found: {args.input}")
        sys.exit(1)

    # Default output paths
    if not args.output:
        args.output = Path(f"results/visualization.{'html' if args.format == 'html' else 'tex'}")

    # Load data
    with Spinner("Loading data") as spinner:
        try:
            docs = read_augmented_jsonl(args.input)
            spinner.succeed(f"Loaded {len(docs)} documents")
        except Exception as e:
            spinner.fail(str(e))
            sys.exit(1)

    # Generate output
    if args.format == "html":
        with Spinner("Generating HTML") as spinner:
            generate_html_visualization(docs, output_path=args.output, max_docs=args.max_docs)
            spinner.succeed("Done")
        success(f"Saved: {args.output}")
        info(dim("Open in browser. Print > Save as PDF for export."))

    elif args.format == "tex":
        with Spinner("Generating TeX") as spinner:
            generate_tex_report(docs, output_path=args.output, max_docs=args.max_docs)
            spinner.succeed("Done")
        success(f"Saved: {args.output}")

    elif args.format == "terminal":
        print(generate_terminal_visualization(docs, max_docs=min(args.max_docs, 10)))


if __name__ == "__main__":
    main()
