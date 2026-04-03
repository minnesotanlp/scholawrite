"""Text normalization, hashing, and validation utilities.

Handles TEXT MANIPULATION ONLY:
- Normalization (whitespace, Unicode)
- Sentence splitting and character offsets
- Provenance hashing for forensic validation
- Leakage detection (prompt/instruction artifacts)
- Jaccard similarity for text comparison

DOES NOT contain:
- Label parsing -> lives in labels.py
- Metric computation -> lives in metrics.py
- LLM orchestration -> lives in agentic.py
- Placeholder generation -> lives in injection.py
"""
from __future__ import annotations

import re
import unicodedata
import hashlib
from typing import List, Tuple

__all__ = ["normalize_text", "split_sentences", "char_offsets", "compute_provenance_hash", "has_prompt_leakage", "get_token_count", "compute_character_jaccard", "compute_word_jaccard"]

# Sentence boundary pattern: split after .!? followed by whitespace and capital letter
_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

# Significantly enhanced leakage patterns to catch conversational artifacts,
# instruction echos, and formatting markers common in flagship LLM outputs.
_LEAKAGE_PATTERNS = re.compile(
    r"(?i)^(?:sure|certainly|here is|here's|revised|modified|updated|final|corrected|as requested|the following|of course|i have|i've|understood|absolutely|no problem|glad to help|the (?:modified|revised) (?:text|version|span|paragraph|section) is|\[TARGET\]|\[PRECEDING\]|\[FOLLOWING\]|\[REVISED\]|\[SPAN\]|objective:|persona:|setting:|state of mind:|background:|ambient note|internal thought|---|\*\*\*|###|####|REVISED VERSION:|MODIFIED TEXT:|REVISION:|EDIT:)",
    re.IGNORECASE
)

def normalize_text(text: str) -> str:
    """Standardize scholarly text for deterministic hashing."""
    if not text: return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_sentences(text: str) -> List[str]:
    """High-performance sentence segmentation heuristic."""
    if not text: return []
    return [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]

def char_offsets(text: str, sentences: List[str]) -> List[Tuple[int, int]]:
    """Calculate precise (start, end) char offsets for sentences."""
    offsets, current = [], 0
    for s in sentences:
        idx = text.find(s, current)
        if idx == -1: idx = current
        offsets.append((idx, idx + len(s)))
        current = idx + len(s)
    return offsets

def compute_provenance_hash(text: str) -> str:
    """Strong SHA-256 cryptographic content anchor."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:32]

def get_token_count(text: str) -> int:
    """Fast whitespace-aware token counting."""
    return len(text.split())

def has_prompt_leakage(text: str) -> bool:
    """Multi-layer adversarial leakage detection."""
    clean = text.strip()
    if _LEAKAGE_PATTERNS.search(clean): return True
    if "[" in clean and "]" in clean:
        markers = ["TARGET", "SPAN", "REVISED", "PRECEDING", "FOLLOWING", "MARKER"]
        if any(m in clean.upper() for m in markers): return True
    instruction_echos = ["Return ONLY", "meta-commentary", "modified text", "revised text", "without commentary", "no meta-talk", "no quotes"]
    lower_clean = clean.lower()
    for m in instruction_echos:
        if m.lower() in lower_clean: return True
    if clean.startswith('"') and clean.endswith('"') and clean.count('"') == 2: return True
    return False

def compute_character_jaccard(a: str, b: str) -> float:
    """Character-level similarity for divergence validation."""
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)


def compute_word_jaccard(a: str, b: str) -> float:
    """Word-level similarity for content divergence detection."""
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a and not words_b: return 1.0
    if not words_a or not words_b: return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
