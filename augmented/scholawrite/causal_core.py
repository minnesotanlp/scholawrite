"""Token-granular causal execution engine for irreversible process simulation."""
from __future__ import annotations

import hashlib
import json
from statistics import mean, stdev
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from .embodied import EmbodiedScholar
from .metrics import (
    GLUCOSE_FLOOR,
    GLUCOSE_LEXICAL_STARVATION,
    SYNTACTIC_COLLAPSE_BASE,
    SYNTACTIC_COLLAPSE_GLUCOSE_FACTOR,
    MIN_TRACE_LENGTH_COUPLING,
    LOCALITY_HUMAN_MIN,
    LOCALITY_HUMAN_MAX,
    COUPLING_STRONG_THRESHOLD,
)
from .config import get_discourse_markers, CONFIG_DIR

__all__ = [
    "LexicalIntention",
    "ExecutionEvent",
    "DeterministicRepairGenerator",
    "IrreversibleProcessEngine",
]

@dataclass(frozen=True)
class LexicalIntention:
    """Token-granular intention with biometric grounding."""
    target: str
    syntactic_depth: float
    lexical_rarity: float
    cognitive_cost: float

@dataclass(frozen=True)
class ExecutionEvent:
    """Trace of a single token execution."""
    intention: LexicalIntention
    actual_output: str
    failure_mode: Optional[str]
    repair_distance: int
    glucose_before: float
    glucose_after: float
    latency_ms: float

class DeterministicRepairGenerator:
    """Generates repairs using a domain-specific exhaustive lexicon."""

    def __init__(self, discipline: str = "general_academic"):
        self.discipline = discipline
        self.lexicon = self._load_lexicon()

    def _load_lexicon(self) -> Dict[str, Tuple[str, ...]]:
        path = CONFIG_DIR / "lexical_substitutions.json"
        if not path.exists(): return {}
        try:
            full_data = json.loads(path.read_text(encoding="utf-8"))
            base = full_data.get("general_academic", {})
            specific = full_data.get(self.discipline.lower(), {})
            return {k.lower(): tuple(v) for k, v in {**base, **specific}.items()}
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            return {}

    def generate_repair(self, intention: LexicalIntention, mode: str, glucose: float, token_idx: int) -> Tuple[str, int]:
        """Deterministic repair generation based on metabolic state.

        Repair markers are loaded from configs/discourse_markers.json.
        """
        seed = int(hashlib.md5(f"{intention.target}:{mode}:{glucose:.4f}:{token_idx}".encode()).hexdigest(), 16)

        # Load repair markers from config
        discourse_data = get_discourse_markers()
        repair_markers = discourse_data.get("repair_markers", {})

        if mode == "lexical_starvation":
            fallbacks = repair_markers.get("lexical_starvation_fallbacks", ["concept", "framework", "element"])
            subs = self.lexicon.get(intention.target.lower(), tuple(fallbacks))
            return f"{subs[seed % len(subs)]} ", 1
        if mode == "syntactic_collapse":
            markers = repair_markers.get("syntactic_collapse", ["thus, ", "so, ", "consequently, ", "accordingly, "])
            return markers[seed % len(markers)], 2

        # Cognitive overflow fallback
        overflow_fillers = repair_markers.get("cognitive_overflow_fillers", ["it "])
        return overflow_fillers[seed % len(overflow_fillers)], 3

class IrreversibleProcessEngine:
    """
    Simulates writing as an irreversible resource-coupled causal process.
    Operates directly on a stateful EmbodiedScholar.
    """

    def __init__(self, author: EmbodiedScholar, discipline: str = "general_academic"):
        self.author = author
        self.token_idx = 0
        self.trace: List[ExecutionEvent] = []
        self.repair_gen = DeterministicRepairGenerator(discipline)

    def execute(self, intention: LexicalIntention) -> str:
        """Execute a single intention, permanently depleting the author's resources."""
        glucose_before = self.author.glucose
        failure = self._check_failure(intention)

        if failure:
            output, repair_dist = self.repair_gen.generate_repair(intention, failure, self.author.glucose, self.token_idx)
            # Failure repair costs 2.7x the base cognitive cost
            depletion_cost = intention.cognitive_cost * 2.7
        else:
            output = intention.target
            repair_dist = 0
            depletion_cost = intention.cognitive_cost

        latency = self.author.calculate_latency(intention.syntactic_depth)

        # Record event using state BEFORE permanent depletion
        # Glucose floor: GLUCOSE_FLOOR (0.05) maintains minimal cognitive function
        self.trace.append(ExecutionEvent(
            intention=intention, actual_output=output,
            failure_mode=failure, repair_distance=repair_dist,
            glucose_before=glucose_before, glucose_after=max(GLUCOSE_FLOOR, self.author.glucose - depletion_cost),
            latency_ms=round(latency, 2)
        ))

        # IRREVERSIBLE RESOURCE CONSUMPTION
        self.author.consume_resources(1, intention.syntactic_depth)
        self.author.glucose = max(GLUCOSE_FLOOR, self.author.glucose - depletion_cost)

        self.token_idx += 1
        return output

    def _check_failure(self, intention: LexicalIntention) -> Optional[str]:
        """Deterministic resource-gated failure check.

        Failure modes are triggered based on metabolic state and task demands:

        1. lexical_starvation: Glucose < GLUCOSE_LEXICAL_STARVATION (0.65) and
           lexical rarity exceeds capacity. Based on resource competition models
           of lexical retrieval under cognitive load.

        2. syntactic_collapse: Syntactic depth exceeds SYNTACTIC_COLLAPSE_BASE (4.0)
           plus glucose-scaled capacity (glucose * SYNTACTIC_COLLAPSE_GLUCOSE_FACTOR).
           Higher glucose extends syntactic planning capacity.

        See docs/THRESHOLDS.md, Section "Embodied Simulation Thresholds".
        """
        # Lexical starvation: low glucose + high lexical rarity
        # Threshold: GLUCOSE_LEXICAL_STARVATION (0.65)
        if self.author.glucose < GLUCOSE_LEXICAL_STARVATION and intention.lexical_rarity > (0.4 + (1.0 - self.author.glucose) * 0.6):
            return "lexical_starvation"
        # Syntactic collapse: depth exceeds glucose-scaled capacity
        # Thresholds: SYNTACTIC_COLLAPSE_BASE (4.0), SYNTACTIC_COLLAPSE_GLUCOSE_FACTOR (3.5)
        if intention.syntactic_depth > (SYNTACTIC_COLLAPSE_BASE + self.author.glucose * SYNTACTIC_COLLAPSE_GLUCOSE_FACTOR):
            return "syntactic_collapse"
        return None

    def compute_causal_signatures(self) -> Dict[str, Any]:
        """Mathematically rigorous biometric validation.

        Computes two key signatures of human production:

        1. Repair Locality: Token distance between failures and repairs
           Human baseline: LOCALITY_HUMAN_MIN (1.0) to LOCALITY_HUMAN_MAX (3.5)
           Based on typing repair studies (Salthouse, 1984)

        2. Resource Coupling: Pearson correlation between failure events
           and subsequent syntactic simplification
           Human baseline: abs(r) >= COUPLING_STRONG_THRESHOLD (0.6)

        See docs/THRESHOLDS.md for detailed justifications.

        Returns:
            Dict with repair_locality, resource_coupling, and is_plausible
        """
        if not self.trace:
            return {"repair_locality": 0.0, "resource_coupling": 0.0, "is_plausible": False}

        fails = [i for i, e in enumerate(self.trace) if e.failure_mode]
        repairs = [i for i, e in enumerate(self.trace) if e.repair_distance > 0]

        # 1. Repair Locality (Human baseline: LOCALITY_HUMAN_MIN to LOCALITY_HUMAN_MAX)
        locality = sum(min([abs(r-f) for r in repairs if r>=f] or [100]) for f in fails) / len(fails) if fails else 0.0

        # 2. Resource Coupling (Human baseline: abs(r) >= COUPLING_STRONG_THRESHOLD)
        # Requires MIN_TRACE_LENGTH_COUPLING (10) events for meaningful correlation
        coupling = 0.0
        if len(self.trace) > MIN_TRACE_LENGTH_COUPLING and fails:
            try:
                x = [1 if e.failure_mode else 0 for e in self.trace[:-1]]
                y = [e.intention.syntactic_depth for e in self.trace[1:]]
                mu_x, mu_y = mean(x), mean(y)
                std_x, std_y = stdev(x), stdev(y)
                if std_x > 0 and std_y > 0:
                    coupling = sum((xi - mu_x) * (yi - mu_y) for xi, yi in zip(x, y)) / ((len(x)-1) * std_x * std_y)
            except (ValueError, ZeroDivisionError, TypeError):
                pass

        # Plausibility requires BOTH locality and coupling within human baselines
        is_plausible = (
            LOCALITY_HUMAN_MIN <= locality <= LOCALITY_HUMAN_MAX
            and abs(coupling) >= COUPLING_STRONG_THRESHOLD
        )
        return {
            "repair_locality": round(locality, 2),
            "resource_coupling": round(coupling, 3),
            "is_plausible": is_plausible
        }

    def render_text(self) -> str:
        """Render text FROM causal trace."""
        return " ".join(e.actual_output for e in self.trace).strip()
