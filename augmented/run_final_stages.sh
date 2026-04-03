#!/usr/bin/env bash
set -euo pipefail

SEED_RAW="data/seed/raw/hf_scholawrite"
SEED_NORM="data/seed/normalized/all_sorted.jsonl"
INJ_RAW="data/injections/raw/all_sorted.jsonl"
OUT_DIR="data/augmented/full"
MODELS_CONFIG="configs/openrouter_models.json"
WORKERS=20

echo "1. Ingesting Seed Data..."
.venv/bin/python3 scripts/ingest_seed.py --input "$SEED_RAW" --output "$SEED_NORM" --split all_sorted

echo "2. Generating Causal Injections..."
.venv/bin/python3 scripts/generate_injections.py \
    --input "$SEED_NORM" \
    --output "$INJ_RAW" \
    --provider openrouter \
    --models-file "$MODELS_CONFIG" \
    --workers "$WORKERS"

echo "3. Starting High-Quality Augmented Build..."
.venv/bin/python3 -u scripts/build_augmented_dataset.py \
    --seed-docs "$SEED_NORM" \
    --injections "$INJ_RAW" \
    --output-dir "$OUT_DIR" \
    --openrouter \
    --models-file "$MODELS_CONFIG"

echo "4. Generating Anomalies..."
.venv/bin/python3 -u scripts/generate_anomalies.py --input "$OUT_DIR/documents.jsonl" --output "$OUT_DIR/anomalies.jsonl"

echo "5. Validating Annotations..."
.venv/bin/python3 -u scripts/validate_annotations.py --input "$OUT_DIR/documents.jsonl" --strict

echo "6. Running Baselines..."
.venv/bin/python3 -u scripts/run_baselines.py --input "$OUT_DIR/documents.jsonl" --output-dir "results/baselines"

echo "7. Running Harm Analysis..."
.venv/bin/python3 -u scripts/run_harm.py --input "$OUT_DIR/documents.jsonl" --output-dir "results/harm"

echo "Pipeline Run Completed Successfully!"