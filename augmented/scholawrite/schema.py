"""Data models for the ScholaWrite forensic annotation framework."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

class InjectionLevel(str, Enum):
    NAIVE = "naive"
    TOPICAL = "topical"
    CONTEXTUAL = "contextual"

class TrajectoryState(str, Enum):
    COLD = "cold"
    WARM = "warm"
    ASSIMILATED = "assimilated"

class AmbiguityFlag(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Label(str, Enum):
    INJECTION_NAIVE = "injection.naive"
    INJECTION_TOPICAL = "injection.topical"
    INJECTION_CONTEXTUAL = "injection.contextual"
    ANOMALY_MISSING_REVISION = "anomaly.missing_revision"
    ANOMALY_TIMESTAMP_JITTER = "anomaly.timestamp_jitter"
    ANOMALY_TRUNCATION = "anomaly.truncation"
    ANOMALY_LARGE_DIFF = "anomaly.large_diff"
    ANOMALY_PROCESS_VIOLATION = "anomaly.process_violation"
    ANOMALY_NO_COUPLING = "anomaly.no_resource_coupling"
    ASSISTANCE_REVISION_ASSISTED = "assistance.revision_assisted"

    def is_injection(self) -> bool:
        return self.value.startswith("injection.")
    def is_anomaly(self) -> bool:
        return self.value.startswith("anomaly.")
    def is_assistance(self) -> bool:
        return self.value.startswith("assistance.")

@dataclass(frozen=True)
class ResourceAllocation:
    """Cognitive resource allocation (lexical, syntactic, attention)."""
    lexical: float
    syntactic: float
    attention: float


@dataclass(frozen=True)
class CognitiveState:
    """Snapshot of author's cognitive resources at a specific minute."""
    minute: int
    fatigue_index: float
    glucose_level: float
    allocation: ResourceAllocation
    context_clarity: float
    biometric_salt: str


@dataclass(frozen=True)
class DocumentProfile:
    """Stylistic and thematic profile for a document."""
    persona: str
    discipline: str
    primary_goal: str
    secondary_goals: List[str]
    stylistic_voice: str
    paranoia_level: float


@dataclass(frozen=True)
class GenerationMetadata:
    """Metadata about LLM generation for reproducibility and analysis.

    Captures the parameters used for each LLM call, enabling:
    - Full reproducibility of generated content
    - Analysis of parameter impact on output quality
    - Model capability tracking
    """
    model_id: str
    temperature: float
    max_tokens: int
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    repetition_penalty: Optional[float] = None
    seed: Optional[int] = None
    attempt_number: int = 0
    cognitive_glucose: Optional[float] = None
    cognitive_fatigue: Optional[float] = None
    cognitive_attention: Optional[float] = None


@dataclass(frozen=True)
class CausalEvent:
    """A token-granular event in the causal execution trace."""
    intention: str
    actual_output: str
    status: str
    failure_mode: Optional[str]
    repair_artifact: Optional[str]
    glucose_at_event: float
    latency_ms: float
    syntactic_complexity: float

@dataclass(frozen=True)
class InjectionSpan:
    doc_id: str
    revision_id: str
    injection_id: str
    injection_level: Optional[InjectionLevel]
    trajectory_state: Optional[TrajectoryState]
    ambiguity_flag: AmbiguityFlag
    span_start_char: int
    span_end_char: int
    span_start_sentence: int
    span_end_sentence: int
    generator_class: str
    prompt_hash: str
    rng_seed: int
    provenance_hash: Optional[str]
    label: Label
    original_start_char: Optional[int] = None
    original_end_char: Optional[int] = None
    biometric_salt: Optional[str] = None
    causal_trace: List[CausalEvent] = field(default_factory=list)
    generation_metadata: Optional[GenerationMetadata] = None

    def __post_init__(self) -> None:
        if self.label.is_injection():
            if self.injection_level is None:
                raise ValueError("injection_level required for injection labels")
            if self.trajectory_state is None:
                raise ValueError("trajectory_state required for injection labels")
        elif self.label.is_anomaly():
            if self.injection_level is not None:
                raise ValueError("injection_level must be None for anomaly labels")
            if self.trajectory_state is not None:
                raise ValueError("trajectory_state must be None for anomaly labels")

@dataclass(frozen=True)
class SeedRevision:
    doc_id: str
    revision_id: str
    revision_index: int
    text: str
    timestamp: Optional[str]
    provenance_hash: str
    # Original ScholaWrite fields preserved for research affordances
    before_text: Optional[str] = None  # Text before this revision (diff source)
    writing_intention: Optional[str] = None  # Original expert annotation (Clarity, Structural, etc.)
    high_level_category: Optional[str] = None  # REVISION, INSERTION, etc.

@dataclass(frozen=True)
class SeedDocument:
    doc_id: str
    revisions: List[SeedRevision]

@dataclass(frozen=True)
class AugmentedRevision:
    doc_id: str
    revision_id: str
    revision_index: int
    text: str
    timestamp: Optional[str]
    provenance_hash: str
    annotations: List[InjectionSpan]
    # Original ScholaWrite fields preserved for research affordances
    before_text: Optional[str] = None  # Text before this revision (diff source)
    writing_intention: Optional[str] = None  # Original expert annotation (Clarity, Structural, etc.)
    high_level_category: Optional[str] = None  # REVISION, INSERTION, etc.

@dataclass(frozen=True)
class AugmentedDocument:
    doc_id: str
    revisions: List[AugmentedRevision]


@dataclass(frozen=True)
class RunManifest:
    """Metadata for a reproducible pipeline run."""
    run_id: str
    created_at: str
    seed: int
    code_version: str
    checksums: Dict[str, str]
    params: Dict[str, Any]


@dataclass(frozen=True)
class SplitSpec:
    """Train/val/test split document IDs."""
    train: List[str]
    val: List[str]
    test: List[str]
