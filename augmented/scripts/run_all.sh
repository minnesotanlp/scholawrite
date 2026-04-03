#!/usr/bin/env bash
# Purpose: scripts/run_all.sh
# Orchestrate the high-quality, model-diverse ScholaWrite-Augmented pipeline.
set -euo pipefail

SEED_RAW=${1:-"data/seed/raw/hf_scholawrite"}
SPLIT=${2:-"all_sorted"}
OUT_DIR=${3:-"data/augmented/full"}
BUDGET=${4:-"150.0"}
WORKERS=${5:-"20"}

SEED_NORM="data/seed/normalized/${SPLIT}.jsonl"
INJ_RAW="data/injections/raw/${SPLIT}.jsonl"
MODELS_CONFIG="configs/openrouter_models.json"

echo "=== Starting High-Quality Diverse Pipeline Run ==="
echo "Seed Raw: $SEED_RAW"
echo "Split: $SPLIT"
echo "Output Dir: $OUT_DIR"
echo "Budget USD: $BUDGET"

echo "1. Ingesting Seed Data..."
uv run python scripts/ingest_seed.py --input "$SEED_RAW" --output "$SEED_NORM" --split "$SPLIT"

echo "2. Generating Diverse Injections via OpenRouter..."
# Use diverse models for initial injection too
uv run python scripts/generate_injections.py \
    --input "$SEED_NORM" \
    --output "$INJ_RAW" \
    --provider openrouter \
    --models-file "$MODELS_CONFIG" \
    --level contextual \
    --seed 42 \
    --budget-usd "$BUDGET" \
    --max-total 50

echo "3. Building Augmented Dataset with Diverse Stylistic Assimilation (Parallel)..."
uv run python scripts/build_augmented_dataset.py \
    --seed-docs "$SEED_NORM" \
    --injections "$INJ_RAW" \
    --output-dir "$OUT_DIR" \
    --openrouter \
    --models-file "$MODELS_CONFIG" \
    --workers "$WORKERS"

echo "4. Generating Anomalies..."
uv run python scripts/generate_anomalies.py --input "$OUT_DIR/documents.jsonl" --output "$OUT_DIR/anomalies.jsonl"

echo "5. Validating Annotations..."
uv run python scripts/validate_annotations.py --input "$OUT_DIR/documents.jsonl" --strict

echo "6. Running Baselines (including Compression-based)..."
uv run python scripts/run_baselines.py --input "$OUT_DIR/documents.jsonl" --output-dir "results/baselines"

echo "7. Running Disaggregated Harm Analysis..."
uv run python scripts/run_harm.py --input "$OUT_DIR/documents.jsonl" --output-dir "results/harm"

echo "8. Data Linting and PII Heuristic Scan..."
uv run python scripts/lint_data.py --input-dir "$OUT_DIR" --pii-scan

echo "9. Generating Trajectory Visualization..."
uv run python scripts/visualize_trajectories.py --input "$OUT_DIR/documents.jsonl" --output "results/visualization_full.html"

echo "10. Generating Checksums..."
uv run python scripts/hash_artifacts.py --artifacts "$OUT_DIR/documents.jsonl,$OUT_DIR/annotations.jsonl,$OUT_DIR/anomalies.jsonl,$OUT_DIR/generated_text.jsonl,$OUT_DIR/stats.json"

echo "=== Pipeline Run Completed Successfully ==="
