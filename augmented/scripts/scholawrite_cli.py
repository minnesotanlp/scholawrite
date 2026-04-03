#!/usr/bin/env python
"""
ScholaWrite CLI - Interactive command-line interface for the ScholaWrite dataset toolkit.

This provides a unified entry point with both interactive menus and direct command-line
arguments for all ScholaWrite operations.

Usage:
    uv run python scripts/scholawrite_cli.py              # Interactive mode
    uv run python scripts/scholawrite_cli.py --help       # Show help
    uv run python scripts/scholawrite_cli.py ingest ...   # Direct command
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scholawrite.banner import print_banner, VERSION
from scholawrite.cli import (
    Menu, MenuItem, Spinner,
    style, success, error, warning, info, dim, bold,
    prompt_path, prompt_choice, prompt_confirm, prompt_number,
    clear_screen, section, divider, Style,
)

__all__ = ["main"]


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Mode Functions
# ═══════════════════════════════════════════════════════════════════════════════

def interactive_ingest() -> int:
    """Interactive workflow for ingesting seed data."""
    section("Ingest Seed Data")
    print(dim("  Load and normalize ScholaWrite seed data from HuggingFace format."))
    print()

    # Get input path
    input_path = prompt_path(
        "Input directory (HuggingFace dataset)",
        default=Path("data/seed/raw/hf_scholawrite"),
        must_exist=True,
        is_dir=True,
    )
    if not input_path:
        return 1

    # Get split choice
    split = prompt_choice(
        "Which split to load?",
        ["all", "train", "test", "test_small"],
        default="test_small",
    )

    # Get output path
    output_path = prompt_path(
        "Output JSONL file",
        default=Path(f"data/seed/normalized/{split}.jsonl"),
    )
    if not output_path:
        return 1

    # Confirm
    print()
    divider()
    print(f"  Input:  {input_path}")
    print(f"  Split:  {split}")
    print(f"  Output: {output_path}")
    divider()
    print()

    if not prompt_confirm("Proceed with ingestion?"):
        print(info("Cancelled."))
        return 0

    # Execute
    from scholawrite.io import load_seed, load_seed_split, write_documents_jsonl

    with Spinner("Loading seed data"):
        if split == "all":
            documents = load_seed(input_path)
        else:
            documents = load_seed_split(input_path, split=split)

    total_revisions = sum(len(doc.revisions) for doc in documents)
    print(success(f"Loaded {len(documents)} documents with {total_revisions} revisions"))

    with Spinner("Writing normalized JSONL"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_documents_jsonl(documents, output_path)

    print(success(f"Output written to: {output_path}"))
    return 0


def interactive_generate_injections() -> int:
    """Interactive workflow for generating injections."""
    section("Generate Injections")
    print(dim("  Create AI-generated injection candidates using causal process simulation."))
    print()

    input_path = prompt_path(
        "Input JSONL (normalized seed documents)",
        default=Path("data/seed/normalized/test_small.jsonl"),
        must_exist=True,
    )
    if not input_path:
        return 1

    output_path = prompt_path(
        "Output JSONL for injections",
        default=Path("data/injections/injections.jsonl"),
    )
    if not output_path:
        return 1

    provider = prompt_choice(
        "Text generation provider",
        ["placeholder", "openrouter"],
        default="placeholder",
    )

    print()
    if not prompt_confirm("Generate injections?"):
        return 0

    # Execute via subprocess - output streams directly to user
    import subprocess
    cmd = [
        "uv", "run", "python", "scripts/generate_injections.py",
        "--input", str(input_path),
        "--output", str(output_path),
        "--provider", provider,
    ]

    print()
    print(dim(f"  Running: {' '.join(cmd)}"))
    print()
    result = subprocess.run(cmd)
    return result.returncode


def interactive_build_augmented() -> int:
    """Interactive workflow for building augmented dataset."""
    section("Build Augmented Dataset")
    print(dim("  Combine seed documents with injections using embodied simulation."))
    print(dim("  The build script will prompt for options and show progress."))
    print()

    if not prompt_confirm("Launch build wizard?"):
        return 0

    # Run the script directly - it has its own interactive mode and progress bar
    import subprocess
    result = subprocess.run(["uv", "run", "python", "scripts/build_augmented_dataset.py"])
    return result.returncode


def interactive_run_baselines() -> int:
    """Interactive workflow for running baselines."""
    section("Run Baselines")
    print(dim("  Execute process-granular forensic baselines including Causal Coupling AUC."))
    print()

    input_path = prompt_path(
        "Augmented documents JSONL",
        default=Path("data/augmented/documents.jsonl"),
        must_exist=True,
    )
    if not input_path:
        return 1

    output_dir = prompt_path(
        "Results output directory",
        default=Path("results/baselines"),
    )
    if not output_dir:
        return 1

    threshold = prompt_number(
        "NCD classification threshold (percent)",
        default=45,
        min_val=1,
        max_val=99,
    )
    if threshold is None:
        return 1

    print()
    if not prompt_confirm("Run baseline evaluation?"):
        return 0

    import subprocess
    cmd = [
        "uv", "run", "python", "scripts/run_baselines.py",
        "--input", str(input_path),
        "--output-dir", str(output_dir),
        "--threshold", str(threshold / 100),
    ]

    print()
    print(dim(f"  Running: {' '.join(cmd)}"))
    print()
    result = subprocess.run(cmd)
    return result.returncode


def interactive_validate() -> int:
    """Interactive workflow for validation."""
    section("Validate Dataset")
    print(dim("  Run forensic integrity checks on augmented documents."))
    print()

    input_path = prompt_path(
        "Augmented documents JSONL",
        default=Path("data/augmented/documents.jsonl"),
        must_exist=True,
    )
    if not input_path:
        return 1

    strict = prompt_confirm("Use strict mode (fail on any violation)?", default=False)

    print()
    if not prompt_confirm("Run validation?"):
        return 0

    import subprocess
    cmd = [
        "uv", "run", "python", "scripts/validate_annotations.py",
        "--input", str(input_path),
    ]
    if strict:
        cmd.append("--strict")

    print()
    print(dim(f"  Running: {' '.join(cmd)}"))
    print()
    result = subprocess.run(cmd)
    return result.returncode


def interactive_visualize() -> int:
    """Interactive workflow for visualization."""
    section("Visualize Trajectories")
    print(dim("  Generate HTML visualization of process-coupled trajectories."))
    print()

    input_path = prompt_path(
        "Augmented documents JSONL",
        default=Path("data/augmented/documents.jsonl"),
        must_exist=True,
    )
    if not input_path:
        return 1

    output_path = prompt_path(
        "Output HTML file",
        default=Path("results/visualization.html"),
    )
    if not output_path:
        return 1

    print()
    if not prompt_confirm("Generate visualization?"):
        return 0

    import subprocess
    cmd = [
        "uv", "run", "python", "scripts/visualize_trajectories.py",
        "--input", str(input_path),
        "--output", str(output_path),
    ]

    print()
    print(dim(f"  Running: {' '.join(cmd)}"))
    print()
    result = subprocess.run(cmd)
    return result.returncode


def interactive_full_pipeline() -> int:
    """Run the complete pipeline interactively."""
    section("Full Pipeline")
    print(dim("  Run the complete ScholaWrite augmentation pipeline end-to-end."))
    print()
    print("  This will execute:")
    print(dim("    1. Ingest seed data"))
    print(dim("    2. Generate injections"))
    print(dim("    3. Build augmented dataset"))
    print(dim("    4. Generate anomalies"))
    print(dim("    5. Run baselines"))
    print(dim("    6. Validate annotations"))
    print()

    if not prompt_confirm("Run full pipeline?"):
        return 0

    steps = [
        ("Ingesting seed data", "scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --output data/seed/normalized/pipeline.jsonl --split test_small"),
        ("Generating injections", "scripts/generate_injections.py --input data/seed/normalized/pipeline.jsonl --output data/injections/pipeline.jsonl --provider placeholder"),
        ("Building augmented dataset", "scripts/build_augmented_dataset.py --seed-docs data/seed/normalized/pipeline.jsonl --injections data/injections/pipeline.jsonl --output-dir data/augmented/pipeline"),
        ("Generating anomalies", "scripts/generate_anomalies.py --input data/augmented/pipeline/documents.jsonl --output data/augmented/pipeline/anomalies.jsonl"),
        ("Running baselines", "scripts/run_baselines.py --input data/augmented/pipeline/anomalies.jsonl --output-dir results/pipeline"),
        ("Validating annotations", "scripts/validate_annotations.py --input data/augmented/pipeline/anomalies.jsonl"),
    ]

    import subprocess

    print()
    for i, (desc, script_args) in enumerate(steps, 1):
        print()
        print(bold(f"  Step {i}/6: {desc}"))
        print(dim("  " + "─" * 60))
        cmd = ["uv", "run", "python"] + script_args.split()
        print(dim(f"  {' '.join(cmd)}"))
        print()

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print()
            print(error(f"Pipeline failed at step {i}: {desc}"))
            return 1
        else:
            print(success(f"Step {i} completed: {desc}"))

    print()
    print(success("Full pipeline completed successfully!"))
    print(dim("  Results available in: results/pipeline/"))
    return 0


def show_about() -> int:
    """Show about information."""
    section("About ScholaWrite")
    print(f"""
  ScholaWrite v{VERSION}
  Embodied Causal Simulation for Scholarly Writing Detection

  ScholaWrite is a benchmark dataset for AI-generated text detection
  in scholarly writing contexts. It uses biometrically-grounded
  process simulation to create forensically-valid injection samples.

  Key Features:
    {style('•', Style.CYAN)} Embodied cognition simulation (glucose, fatigue, attention)
    {style('•', Style.CYAN)} Irreversible causal process engine
    {style('•', Style.CYAN)} Trajectory states (COLD → WARM → ASSIMILATED)
    {style('•', Style.CYAN)} Process-granular forensic baselines
    {style('•', Style.CYAN)} Disaggregated harm analysis

  Documentation:
    {dim('docs/PROTOCOL.md')}      - Dataset protocol
    {dim('docs/TERMINOLOGY.md')}   - Key terminology
    {dim('docs/TRAJECTORIES.md')}  - Trajectory system
    {dim('docs/ETHICS.md')}        - Ethical considerations

  License: MIT
  Repository: https://github.com/writerslogic/scholawrite-augmented
""")
    input(dim("  Press Enter to continue..."))
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# Main Menu
# ═══════════════════════════════════════════════════════════════════════════════

def run_interactive() -> int:
    """Run the interactive CLI menu."""
    clear_screen()
    print_banner()

    # Create data processing submenu
    data_menu = Menu(
        "Data Processing",
        [
            MenuItem("1", "Ingest Seed Data", "Load and normalize HuggingFace dataset", interactive_ingest),
            MenuItem("2", "Generate Injections", "Create AI injection candidates", interactive_generate_injections),
            MenuItem("3", "Build Augmented Dataset", "Combine seeds with injections", interactive_build_augmented),
            MenuItem("4", "Generate Anomalies", "Create process signature anomalies", lambda: run_script("generate_anomalies")),
            MenuItem("b", "Back", "Return to main menu"),
        ],
        subtitle="Prepare and augment dataset artifacts",
    )

    # Create evaluation submenu
    eval_menu = Menu(
        "Evaluation & Analysis",
        [
            MenuItem("1", "Run Baselines", "Execute forensic process baselines", interactive_run_baselines),
            MenuItem("2", "Compute Harm Metrics", "Disaggregated performance analysis", lambda: run_script("run_harm")),
            MenuItem("3", "Evaluate Suite", "Run against gold standard", lambda: run_script("evaluate_suite")),
            MenuItem("4", "IAA Computation", "Inter-annotator agreement", lambda: run_script("iaa_compute")),
            MenuItem("b", "Back", "Return to main menu"),
        ],
        subtitle="Evaluate and analyze results",
    )

    # Create utilities submenu
    utils_menu = Menu(
        "Utilities",
        [
            MenuItem("1", "Validate Annotations", "Forensic integrity checks", interactive_validate),
            MenuItem("2", "Visualize Trajectories", "Generate HTML visualization", interactive_visualize),
            MenuItem("3", "PII Scan", "Scan for personal information", lambda: run_script("pii_scan")),
            MenuItem("4", "Hash Artifacts", "Generate checksums", lambda: run_script("hash_artifacts")),
            MenuItem("5", "Validate Splits", "Check split disjointness", lambda: run_script("validate_splits")),
            MenuItem("6", "Environment Capture", "Show environment info", lambda: run_script("env_capture")),
            MenuItem("b", "Back", "Return to main menu"),
        ],
        subtitle="Utility functions and validation",
    )

    # Main menu
    main_menu = Menu(
        "ScholaWrite CLI",
        [
            MenuItem("1", "Data Processing", "Ingest, generate, and build datasets", lambda: data_menu.run()),
            MenuItem("2", "Evaluation", "Run baselines and analysis", lambda: eval_menu.run()),
            MenuItem("3", "Utilities", "Validation and helper tools", lambda: utils_menu.run()),
            MenuItem("4", "Full Pipeline", "Run complete end-to-end pipeline", interactive_full_pipeline),
            MenuItem("5", "Smoke Test", "Quick end-to-end verification", lambda: run_script("smoke_test")),
            MenuItem("a", "About", "About ScholaWrite", show_about),
            MenuItem("q", "Quit", "Exit the application"),
        ],
        subtitle="Embodied Causal Simulation for Scholarly Writing",
    )

    while True:
        clear_screen()
        print_banner()
        result = main_menu.show()

        if result is None or result.key == "q":
            print()
            print(dim("  Goodbye!"))
            print()
            return 0

        if result.action:
            clear_screen()
            print_banner()
            try:
                result.action()
            except KeyboardInterrupt:
                print()
                print(warning("Operation cancelled"))

            print()
            input(dim("  Press Enter to continue..."))


def run_script(script_name: str) -> int:
    """Helper to run a script by name."""
    import subprocess

    script_map = {
        "generate_anomalies": ["--input", "data/augmented/documents.jsonl", "--output", "data/augmented/anomalies.jsonl"],
        "run_harm": ["--input", "data/augmented/documents.jsonl"],
        "evaluate_suite": ["--gold", "data/gold/gold.jsonl", "--pred", "results/predictions.jsonl", "--report", "results/evaluation.json"],
        "iaa_compute": ["--inputs", "data/annotations/a1.jsonl,data/annotations/a2.jsonl", "--report", "results/iaa.json"],
        "pii_scan": ["--input", "data/augmented/documents.jsonl"],
        "hash_artifacts": [],
        "validate_splits": [],
        "env_capture": [],
        "smoke_test": [],
    }

    args = script_map.get(script_name, [])
    cmd = ["uv", "run", "python", f"scripts/{script_name}.py"] + args

    print()
    print(dim(f"  Running: {' '.join(cmd)}"))
    print()

    result = subprocess.run(cmd)
    return result.returncode


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Argument Parser
# ═══════════════════════════════════════════════════════════════════════════════

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="scholawrite",
        description="ScholaWrite - Embodied Causal Simulation for Scholarly Writing Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                           Launch interactive mode
  %(prog)s ingest -i data/raw -o data/normalized.jsonl
  %(prog)s inject -i data/normalized.jsonl -o data/injections.jsonl
  %(prog)s build --seed-docs data/normalized.jsonl --injections data/injections.jsonl
  %(prog)s baseline -i data/augmented/documents.jsonl
  %(prog)s validate -i data/augmented/documents.jsonl --strict

Version: {VERSION}
Documentation: docs/PROTOCOL.md
""",
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch interactive mode (default if no command given)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest and normalize seed data",
        description="Load ScholaWrite seed data from HuggingFace format and normalize to JSONL.",
    )
    ingest_parser.add_argument("-i", "--input", type=Path, required=True, help="Input directory")
    ingest_parser.add_argument("-o", "--output", type=Path, required=True, help="Output JSONL file")
    ingest_parser.add_argument("-s", "--split", choices=["train", "test", "test_small", "all"], default="all")

    # Inject command
    inject_parser = subparsers.add_parser(
        "inject",
        help="Generate injection candidates",
        description="Create AI-generated injection candidates using causal process simulation.",
    )
    inject_parser.add_argument("-i", "--input", type=Path, required=True, help="Input JSONL")
    inject_parser.add_argument("-o", "--output", type=Path, required=True, help="Output JSONL")
    inject_parser.add_argument("--provider", choices=["placeholder", "openrouter"], default="placeholder")

    # Build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build augmented dataset",
        description="Combine seed documents with injections using embodied simulation.",
    )
    build_parser.add_argument("--seed-docs", type=Path, required=True, help="Seed documents JSONL")
    build_parser.add_argument("--injections", type=Path, required=True, help="Injections JSONL")
    build_parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")
    build_parser.add_argument("--openrouter", action="store_true", help="Use OpenRouter API")

    # Baseline command
    baseline_parser = subparsers.add_parser(
        "baseline",
        help="Run forensic baselines",
        description="Execute process-granular forensic baselines.",
    )
    baseline_parser.add_argument("-i", "--input", type=Path, required=True, help="Input JSONL")
    baseline_parser.add_argument("--output-dir", type=Path, default=Path("results/baselines"))
    baseline_parser.add_argument("--threshold", type=float, default=0.45)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate dataset integrity",
        description="Run forensic integrity checks on augmented documents.",
    )
    validate_parser.add_argument("-i", "--input", type=Path, required=True, help="Input JSONL")
    validate_parser.add_argument("--strict", action="store_true", help="Fail on any violation")

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # If no command given, launch interactive mode
    if args.command is None or args.interactive:
        return run_interactive()

    # Otherwise, dispatch to appropriate script
    import subprocess

    script_map = {
        "ingest": "ingest_seed.py",
        "inject": "generate_injections.py",
        "build": "build_augmented_dataset.py",
        "baseline": "run_baselines.py",
        "validate": "validate_annotations.py",
    }

    script = script_map.get(args.command)
    if not script:
        print(error(f"Unknown command: {args.command}"))
        return 1

    # Build command with arguments
    cmd = ["uv", "run", "python", f"scripts/{script}"]

    # Pass through arguments
    for key, value in vars(args).items():
        if key in ("command", "interactive"):
            continue
        if value is None or value is False:
            continue

        # Convert to CLI flag format
        flag = f"--{key.replace('_', '-')}"

        if value is True:
            cmd.append(flag)
        else:
            cmd.extend([flag, str(value)])

    # Show banner and run
    print_banner()
    print(dim(f"  Running: {' '.join(cmd)}"))
    print()

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
