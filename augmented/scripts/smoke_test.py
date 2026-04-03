#!/usr/bin/env python
"""CLI: ScholaWrite-Augmented Smoke Test.
Verifies the new Embodied Causal pipeline end-to-end.
"""
from __future__ import annotations

import subprocess
import sys

from scholawrite.banner import print_banner
from scholawrite.cli import error, success, info

def run(cmd: str) -> bool:
    print(info(f"Running: {cmd}"))
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(error(f"{res.stderr}"), file=sys.stderr)
        return False
    return True

def main() -> int:
    print_banner("End-to-End Smoke Test")

    # 1. Ingest Small Split
    if not run("uv run python scripts/ingest_seed.py --input data/seed/raw/hf_scholawrite --output data/seed/normalized/smoke.jsonl --split test_small"):
        return 1

    # 2. Generate Injections (Placeholder provider)
    if not run("uv run python scripts/generate_injections.py --input data/seed/normalized/smoke.jsonl --output data/injections/smoke.jsonl --provider placeholder"):
        return 1

    # 3. Build Augmented (No OpenRouter for smoke test)
    if not run("uv run python scripts/build_augmented_dataset.py --seed-docs data/seed/normalized/smoke.jsonl --injections data/injections/smoke.jsonl --output-dir data/augmented/smoke"):
        return 1

    # 4. Generate Anomalies
    if not run("uv run python scripts/generate_anomalies.py --input data/augmented/smoke/documents.jsonl --output data/augmented/smoke/anomalies.jsonl"):
        return 1

    # 5. Run Baselines (including Causal Coupling AUC)
    if not run("uv run python scripts/run_baselines.py --input data/augmented/smoke/anomalies.jsonl"):
        return 1

    # 6. Validate Annotations (Forensic integrity checks)
    if not run("uv run python scripts/validate_annotations.py --input data/augmented/smoke/anomalies.jsonl"):
        return 1

    print(success("End-to-End Smoke Test PASSED."))
    return 0

if __name__ == "__main__":
    sys.exit(main())
