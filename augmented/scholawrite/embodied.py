"""Embodied scholar simulation with metabolic resource tracking."""
from __future__ import annotations

import math
import re
import hashlib
from functools import lru_cache
from .schema import ResourceAllocation, CognitiveState
from .metrics import (
    GLUCOSE_INITIAL,
    GLUCOSE_FLOOR,
    GLUCOSE_DEPLETION_RATE,
    FATIGUE_DIVISOR,
    HIGH_SYNTACTIC_DEMAND,
)
from .config import get_academic_markers_flat

__all__ = ["EmbodiedScholar", "erode_context_deterministically", "get_syntactic_demand", "get_embodied_state"]

class EmbodiedScholar:
    """
    A stateful agent that persists across an entire document's revision history.

    Simulates human cognitive resources including:
    - Glucose: Cognitive fuel that depletes irreversibly over time
    - Visual fatigue: Accumulated strain from screen exposure
    - Resource allocation: Dynamic distribution of cognitive capacity

    Glucose depletion is irreversible and token-granular, modeling the
    metabolic constraints of extended writing sessions.

    All threshold values are documented in docs/THRESHOLDS.md,
    Section "Embodied Simulation Thresholds".
    """
    def __init__(self, author_id: str, initial_glucose: float = GLUCOSE_INITIAL):
        """Initialize the embodied scholar.

        Args:
            author_id: Unique identifier for this author
            initial_glucose: Starting glucose level (default: 1.0 = full capacity)
        """
        self.author_id = author_id
        self.glucose = initial_glucose
        self.visual_fatigue = 0.0
        self.total_tokens_produced = 0

    def consume_resources(self, tokens: int, syntactic_depth: float):
        """Irreversible metabolic depletion per token and complexity.

        Glucose depletes at rate GLUCOSE_DEPLETION_RATE (0.9992) per token,
        with additional penalty for syntactic complexity. Visual fatigue
        accumulates at tokens/FATIGUE_DIVISOR (12000.0).

        Args:
            tokens: Number of tokens produced
            syntactic_depth: Complexity of syntactic structures

        See docs/THRESHOLDS.md, Section "Embodied Simulation Thresholds".
        """
        # Complexity penalty: higher syntactic depth increases depletion
        complexity_penalty = 1.0 + (syntactic_depth / 10.0)

        # Logarithmic decay matching human metabolic study results
        # Rate: GLUCOSE_DEPLETION_RATE (0.9992), Floor: GLUCOSE_FLOOR (0.05)
        self.glucose = max(GLUCOSE_FLOOR, self.glucose * (GLUCOSE_DEPLETION_RATE ** (tokens * complexity_penalty)))

        # Visual fatigue accumulates with production (divisor: FATIGUE_DIVISOR = 12000)
        self.visual_fatigue = min(1.0, self.visual_fatigue + (tokens / FATIGUE_DIVISOR))
        self.total_tokens_produced += tokens

    def allocate_resources(self, demand: float) -> ResourceAllocation:
        """Deterministic allocation based on resource competition.

        Distributes cognitive resources between lexical, syntactic, and
        attentional processes based on current metabolic state and task demands.

        Resource allocation thresholds:
        - Lexical: glucose * (1 - fatigue * 0.4) - fatigue reduces lexical access
        - Syntactic: max(0.3, glucose * 1.3) - minimum floor of 0.3
        - Attention: max(0.1, glucose - fatigue * 0.5) - minimum floor of 0.1

        When demand > HIGH_SYNTACTIC_DEMAND (5.0), syntactic resources
        reduced by 30% to model resource competition.

        Args:
            demand: Current syntactic planning demand

        Returns:
            ResourceAllocation with lexical, syntactic, attention values

        See docs/THRESHOLDS.md, Section "Resource Allocation Thresholds".
        """
        # Lexical retrieval penalized by visual fatigue (up to 40% reduction)
        lexical = self.glucose * (1.0 - self.visual_fatigue * 0.4)
        # Syntactic planning with minimum floor of 0.3
        syntactic = max(0.3, self.glucose * 1.3)
        # High demand (> 5.0) triggers resource reallocation penalty
        if demand > HIGH_SYNTACTIC_DEMAND:
            syntactic *= 0.7
        # Attention with minimum floor of 0.1
        attention = max(0.1, self.glucose - (self.visual_fatigue * 0.5))

        return ResourceAllocation(
            lexical=round(min(1.0, lexical), 3),
            syntactic=round(min(1.0, syntactic), 3),
            attention=round(min(1.0, attention), 3)
        )

    def calculate_latency(self, syntactic_depth: float) -> float:
        """Deterministic mapping from state to keystroke latency (ms)."""
        return round(115 + 90 * math.log(1 + syntactic_depth) * (1.12 - self.glucose), 2)

    def get_biometric_salt(self, token_idx: int) -> str:
        """Generate a deterministic biometric salt for cryptographic anchoring."""
        return hashlib.sha256(f"{self.author_id}:{self.glucose:.6f}:{token_idx}".encode()).hexdigest()

def get_embodied_state(author: EmbodiedScholar, rev_idx: int, total_revs: int, text_context: str = "") -> CognitiveState:
    """Sample the current cognitive state of the persistent author."""
    minute = int((rev_idx / max(1, total_revs)) * 90)
    alloc = author.allocate_resources(get_syntactic_demand(text_context))
    return CognitiveState(
        minute=minute,
        fatigue_index=round(author.visual_fatigue, 3),
        glucose_level=round(author.glucose, 4),
        allocation=alloc,
        context_clarity=alloc.attention,
        biometric_salt=author.get_biometric_salt(rev_idx)
    )

def erode_context_deterministically(text: str, clarity: float, salt: str) -> str:
    """Simulate cognitive blurring by deterministically degrading context."""
    if clarity >= 0.9 or not text: return text
    chars = list(text)
    threshold = 1.0 - clarity
    for i in range(len(chars)):
        h = int(hashlib.md5(f"{salt}:{i}".encode()).hexdigest(), 16) % 100
        if (h / 100.0) < threshold:
            if chars[i] in ",.!?;:": chars[i] = " "
            elif chars[i].isupper() and clarity < 0.6: chars[i] = chars[i].lower()
    return "".join(chars)

@lru_cache(maxsize=1)
def _get_marker_pattern() -> re.Pattern:
    """Build and cache the academic marker regex pattern from config."""
    markers = get_academic_markers_flat()
    if not markers:
        # Fallback to basic markers
        markers = [
            "however", "consequently", "whereas", "although", "notwithstanding",
            "furthermore", "moreover", "conversely", "nevertheless", "nonetheless",
        ]
    # Escape special regex characters and join with |
    escaped = [re.escape(m) for m in markers]
    pattern = r"(?i)\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern)


def get_syntactic_demand(text: str) -> float:
    """
    Heuristic for syntactic planning load calculation.

    Academic markers are loaded from configs/academic_markers.json,
    providing 100+ scholarly cohesive devices and technical connectors.
    """
    if not text:
        return 1.0
    words = text.split()

    # Use config-loaded markers for syntactic orchestration detection
    pattern = _get_marker_pattern()
    markers = len(pattern.findall(text))

    return min(10.0, (len(words) / 10.0) + (markers * 1.2))
