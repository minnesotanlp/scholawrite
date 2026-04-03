"""Temporal normalization and biometric sequence generation."""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List, Optional

__all__ = [
    "normalize_timestamp", "normalize_timestamp_ms", "parse_iso_timestamp",
    "compute_deltas", "generate_biometric_iki_sequence"
]

def normalize_timestamp_ms(ts_ms: Optional[int]) -> Optional[str]:
    """Convert Unix milliseconds to ISO 8601 UTC string."""
    if ts_ms is None:
        return None
    try:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def parse_iso_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp string to datetime object."""
    # Handle with or without timezone
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        # Try without timezone
        return datetime.fromisoformat(ts)


def normalize_timestamp(ts: Optional[int | str]) -> Optional[str]:
    """Standardize timestamps to ISO 8601 UTC with performance fallback."""
    if ts is None: return None
    try:
        if isinstance(ts, int):
            return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).isoformat()
        if isinstance(ts, str):
            # Optimized ISO handling
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).isoformat()
    except (ValueError, TypeError, OSError):
        pass
    return None

def compute_deltas(timestamps: List[Optional[str]]) -> List[Optional[float]]:
    """Calculate inter-revision session deltas in seconds."""
    if not timestamps:
        return []
    deltas: List[Optional[float]] = [None]
    for i in range(1, len(timestamps)):
        t1, t2 = timestamps[i-1], timestamps[i]
        if t1 and t2:
            try:
                dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
                dt2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
                deltas.append((dt2 - dt1).total_seconds())
                continue
            except (ValueError, TypeError):
                pass
        deltas.append(None)
    return deltas

def generate_biometric_iki_sequence(base_latency: float, token_count: int, salt: str) -> List[float]:
    """
    Transform intention latency into a realistic 1/f noise sequence of intervals.
    Human motor control exhibits structured variability.
    """
    rng = random.Random(salt)
    sequence = []
    current = base_latency

    for _ in range(token_count):
        # Add deterministic jitter matching human 1/f signature
        jitter = rng.uniform(-0.15, 0.15) * current
        current = max(80, current + jitter)
        sequence.append(round(current, 2))

    return sequence
