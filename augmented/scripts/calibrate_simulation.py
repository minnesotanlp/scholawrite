#!/usr/bin/env python
"""Calibrate simulation parameters from real ScholaWrite keystroke timing data.

This script extracts inter-revision intervals from real scholarly writing sessions
and fits the embodied simulation parameters (glucose depletion, fatigue accumulation)
to match empirical production slowdowns.

Usage:
    uv run python scripts/calibrate_simulation.py --seed-docs data/seed/normalized/all.jsonl
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from collections import defaultdict

from scholawrite.banner import print_banner
from scholawrite.cli import success, error, info, bold, dim
from scholawrite.io import read_documents_jsonl


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp string."""
    if ts.endswith('Z'):
        ts = ts[:-1] + '+00:00'
    return datetime.fromisoformat(ts)


def extract_session_metrics(documents) -> dict:
    """Extract timing metrics from real revision data.

    Returns:
        Dictionary with:
        - inter_revision_intervals_ms: List of time between revisions (milliseconds)
        - text_deltas: List of (interval_ms, text_change_chars) tuples
        - session_lengths_min: List of session durations (minutes)
        - production_rates: List of (session_minute, chars_per_minute) tuples
    """
    metrics = {
        "inter_revision_intervals_ms": [],
        "text_deltas": [],
        "session_lengths_min": [],
        "production_rates": [],
        "slowdown_curves": [],  # (session_minute, relative_rate) for fitting glucose curve
    }

    for doc in documents:
        revisions = sorted(doc.revisions, key=lambda r: r.revision_index)
        if len(revisions) < 2:
            continue

        # Track session
        session_start = None
        last_ts = None
        last_text_len = 0

        # For production rate tracking
        minute_buckets = defaultdict(list)  # minute -> list of chars produced

        for rev in revisions:
            ts = parse_timestamp(rev.timestamp)
            text_len = len(rev.text) if rev.text else 0

            if session_start is None:
                session_start = ts

            if last_ts is not None:
                interval_ms = (ts - last_ts).total_seconds() * 1000
                text_delta = text_len - last_text_len

                # Only count positive intervals (skip duplicates)
                if interval_ms > 0:
                    metrics["inter_revision_intervals_ms"].append(interval_ms)

                    if text_delta != 0:
                        metrics["text_deltas"].append((interval_ms, abs(text_delta)))

                    # Bucket by session minute
                    session_minute = int((ts - session_start).total_seconds() / 60)
                    if text_delta > 0:
                        minute_buckets[session_minute].append(text_delta)

            last_ts = ts
            last_text_len = text_len

        # Calculate session length
        if last_ts and session_start:
            session_min = (last_ts - session_start).total_seconds() / 60
            metrics["session_lengths_min"].append(session_min)

        # Calculate production rates by minute
        if minute_buckets:
            base_rate = None
            for minute in sorted(minute_buckets.keys()):
                chars_this_minute = sum(minute_buckets[minute])
                metrics["production_rates"].append((minute, chars_this_minute))

                if base_rate is None and chars_this_minute > 0:
                    base_rate = chars_this_minute

                # Track relative slowdown for glucose curve fitting
                if base_rate and base_rate > 0:
                    relative_rate = chars_this_minute / base_rate
                    metrics["slowdown_curves"].append((minute, relative_rate))

    return metrics


def fit_glucose_curve(slowdown_curves: List[Tuple[int, float]]) -> Tuple[float, float]:
    """Fit glucose depletion parameters to observed production slowdowns.

    Uses least squares to find GLUCOSE_DEPLETION_RATE that best matches
    the observed relative production rate decline over session time.

    The model is: glucose(t) = initial * rate^(tokens_per_minute * t)

    Returns:
        (optimal_depletion_rate, r_squared)
    """
    if not slowdown_curves:
        return 0.9992, 0.0  # Default

    # Filter outliers (rates between 0.1 and 2.0)
    filtered = [(m, r) for m, r in slowdown_curves if 0.1 <= r <= 2.0]
    if len(filtered) < 5:
        return 0.9992, 0.0

    # Simple exponential fit: rate = initial * depletion^(tokens_per_min * minute)
    # Taking log: log(rate) = log(initial) + (tokens_per_min * minute) * log(depletion)
    # Linear regression: y = a + b*x where y=log(rate), x=minute, b=tokens_per_min*log(depletion)

    import math

    x_data = [m for m, r in filtered if r > 0]
    y_data = [math.log(r) for m, r in filtered if r > 0]

    if len(x_data) < 3:
        return 0.9992, 0.0

    # Linear regression
    n = len(x_data)
    x_mean = sum(x_data) / n
    y_mean = sum(y_data) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_data, y_data))
    denominator = sum((x - x_mean) ** 2 for x in x_data)

    if denominator == 0:
        return 0.9992, 0.0

    slope = numerator / denominator

    # slope = tokens_per_minute * log(depletion_rate)
    # Assuming ~50 tokens/minute average scholarly production
    tokens_per_min = 50

    if slope < 0:  # Expect negative slope (declining production)
        depletion_rate = math.exp(slope / tokens_per_min)
    else:
        depletion_rate = 0.9992  # Default if no slowdown observed

    # Clamp to reasonable range
    depletion_rate = max(0.990, min(0.9999, depletion_rate))

    # Calculate R-squared
    y_pred = [y_mean + slope * (x - x_mean) for x in x_data]
    ss_res = sum((y - yp) ** 2 for y, yp in zip(y_data, y_pred))
    ss_tot = sum((y - y_mean) ** 2 for y in y_data)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return depletion_rate, max(0, r_squared)


def estimate_fatigue_divisor(intervals: List[float], production_rates: List[Tuple[int, float]]) -> float:
    """Estimate FATIGUE_DIVISOR from observed inter-keystroke timing patterns.

    Fatigue accumulates as tokens/FATIGUE_DIVISOR. We look for correlation
    between cumulative tokens and increase in inter-keystroke intervals.

    Returns:
        Estimated fatigue divisor
    """
    if len(production_rates) < 10:
        return 12000.0  # Default

    # Track cumulative tokens and interval changes
    cumulative_tokens = 0
    last_rate = None
    interval_increases = []

    for minute, rate in sorted(production_rates):
        cumulative_tokens += rate

        if last_rate is not None and last_rate > 0:
            # Check if production rate is declining
            rate_change = (rate - last_rate) / last_rate
            if rate_change < -0.05:  # Significant decline
                # Fatigue at this point = cumulative_tokens / divisor
                # We want fatigue ~0.5 when rate drops significantly
                estimated_divisor = cumulative_tokens / 0.5
                interval_increases.append(estimated_divisor)

        last_rate = rate

    if interval_increases:
        # Use median to be robust to outliers
        return statistics.median(interval_increases)

    return 12000.0


def main() -> int:
    print_banner("Calibrate Simulation")

    parser = argparse.ArgumentParser(
        description="Calibrate embodied simulation parameters from real ScholaWrite data."
    )
    parser.add_argument(
        "--seed-docs", "-i",
        type=Path,
        default=Path("data/seed/normalized/all.jsonl"),
        help="Path to normalized seed documents."
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("configs/calibrated_params.json"),
        help="Output path for calibrated parameters."
    )
    args = parser.parse_args()

    # Load documents
    print()
    print(info("Loading seed documents..."))
    if not args.seed_docs.exists():
        print(error(f"Seed docs not found: {args.seed_docs}"))
        return 1

    documents = read_documents_jsonl(args.seed_docs)
    print(success(f"Loaded {len(documents)} documents"))

    total_revisions = sum(len(d.revisions) for d in documents)
    print(info(f"  Total revisions: {total_revisions:,}"))

    # Extract metrics
    print()
    print(info("Extracting timing metrics..."))
    metrics = extract_session_metrics(documents)

    print(success(f"Extracted {len(metrics['inter_revision_intervals_ms']):,} inter-revision intervals"))
    print(success(f"Extracted {len(metrics['text_deltas']):,} text delta measurements"))
    print(success(f"Extracted {len(metrics['production_rates']):,} production rate samples"))

    # Report statistics
    print()
    print(bold("  Empirical Metrics"))
    print(dim("  " + "-" * 40))

    if metrics["inter_revision_intervals_ms"]:
        intervals = metrics["inter_revision_intervals_ms"]
        print(f"  Inter-revision interval (ms):")
        print(f"    Median: {statistics.median(intervals):.1f}")
        print(f"    Mean: {statistics.mean(intervals):.1f}")
        print(f"    Std: {statistics.stdev(intervals) if len(intervals) > 1 else 0:.1f}")
        print(f"    Min: {min(intervals):.1f}, Max: {max(intervals):.1f}")

    if metrics["session_lengths_min"]:
        sessions = metrics["session_lengths_min"]
        print(f"  Session lengths (minutes):")
        print(f"    Median: {statistics.median(sessions):.1f}")
        print(f"    Mean: {statistics.mean(sessions):.1f}")
        print(f"    Max: {max(sessions):.1f}")

    # Fit parameters
    print()
    print(info("Fitting simulation parameters..."))

    # Fit glucose depletion curve
    depletion_rate, r_squared = fit_glucose_curve(metrics["slowdown_curves"])
    print(success(f"GLUCOSE_DEPLETION_RATE = {depletion_rate:.6f} (R² = {r_squared:.3f})"))

    # Estimate fatigue divisor
    fatigue_divisor = estimate_fatigue_divisor(
        metrics["inter_revision_intervals_ms"],
        metrics["production_rates"]
    )
    print(success(f"FATIGUE_DIVISOR = {fatigue_divisor:.1f}"))

    # Compare to defaults
    print()
    print(bold("  Comparison to Defaults"))
    print(dim("  " + "-" * 40))
    print(f"  GLUCOSE_DEPLETION_RATE: {depletion_rate:.6f} (default: 0.9992)")
    print(f"  FATIGUE_DIVISOR: {fatigue_divisor:.1f} (default: 12000.0)")

    # Write calibrated parameters
    calibrated = {
        "GLUCOSE_DEPLETION_RATE": depletion_rate,
        "FATIGUE_DIVISOR": fatigue_divisor,
        "calibration_metrics": {
            "num_documents": len(documents),
            "total_revisions": total_revisions,
            "num_intervals": len(metrics["inter_revision_intervals_ms"]),
            "num_production_samples": len(metrics["production_rates"]),
            "r_squared_glucose_fit": r_squared,
        }
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(calibrated, f, indent=2)

    print()
    print(success(f"Wrote calibrated parameters to {args.output}"))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
