"""Trajectory state modeling (COLD -> WARM -> ASSIMILATED) based on causal signatures."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Dict, Any, List
from .schema import AmbiguityFlag, InjectionSpan, TrajectoryState, AugmentedRevision
from .metrics import (
    SUBSTANTIAL_EDIT_RATIO,
    COUPLING_ASSIMILATED_THRESHOLD,
    COUPLING_WARM_MINIMUM,
    LOCALITY_WARM_MAX,
)

__all__ = [
    "determine_trajectory_state", "update_span_with_trajectory",
    "EditClassification", "classify_edit", "compute_transition",
    "apply_trajectory", "compute_ambiguity_flag", "tokenize",
    "TrajectoryResult", "SUBSTANTIAL_EDIT_THRESHOLD",
]

SUBSTANTIAL_EDIT_THRESHOLD = SUBSTANTIAL_EDIT_RATIO


class EditClassification(str, Enum):
    """Classification of edit magnitude."""
    NONE = "none"
    LIGHT = "light"
    SUBSTANTIAL = "substantial"


@dataclass
class TrajectoryResult:
    """Result of applying trajectory analysis to a span."""
    final_state: TrajectoryState
    ambiguity_flag: AmbiguityFlag
    transition_history: List[Tuple[int, TrajectoryState]]
    span_start_char: int
    span_end_char: int
    original_start_char: int
    original_end_char: int


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    if not text:
        return []
    # Extract words, lowercase
    words = re.findall(r'\b\w+\b', text.lower())
    return words


def classify_edit(old_tokens: List[str], new_tokens: List[str]) -> EditClassification:
    """Classify the magnitude of an edit based on token differences."""
    if old_tokens == new_tokens:
        return EditClassification.NONE

    old_set = set(old_tokens)
    new_set = set(new_tokens)

    # Calculate symmetric difference
    added = new_set - old_set
    removed = old_set - new_set
    total_changes = len(added) + len(removed)

    # Denominator is max of old/new token counts
    denominator = max(len(old_tokens), len(new_tokens), 1)
    change_ratio = total_changes / denominator

    if change_ratio >= SUBSTANTIAL_EDIT_THRESHOLD:
        return EditClassification.SUBSTANTIAL
    elif change_ratio > 0:
        return EditClassification.LIGHT
    else:
        return EditClassification.NONE


def compute_transition(
    current_state: TrajectoryState,
    edit: EditClassification
) -> TrajectoryState:
    """Compute the next trajectory state based on current state and edit type."""
    # Assimilated is terminal
    if current_state == TrajectoryState.ASSIMILATED:
        return TrajectoryState.ASSIMILATED

    # Cold state transitions
    if current_state == TrajectoryState.COLD:
        if edit == EditClassification.NONE:
            return TrajectoryState.COLD
        elif edit == EditClassification.LIGHT:
            return TrajectoryState.WARM
        else:  # SUBSTANTIAL
            return TrajectoryState.ASSIMILATED

    # Warm state transitions
    if current_state == TrajectoryState.WARM:
        if edit == EditClassification.SUBSTANTIAL:
            return TrajectoryState.ASSIMILATED
        else:
            return TrajectoryState.WARM

    return current_state


def compute_ambiguity_flag(state: TrajectoryState) -> AmbiguityFlag:
    """Map trajectory state to ambiguity flag."""
    mapping = {
        TrajectoryState.COLD: AmbiguityFlag.NONE,
        TrajectoryState.WARM: AmbiguityFlag.LOW,
        TrajectoryState.ASSIMILATED: AmbiguityFlag.MEDIUM,
    }
    return mapping.get(state, AmbiguityFlag.NONE)


def apply_trajectory(
    span: InjectionSpan,
    revisions: List[AugmentedRevision],
    injection_revision_index: int,
) -> TrajectoryResult:
    """Apply trajectory analysis to track how a span evolves across revisions."""
    current_state = TrajectoryState.COLD
    transition_history: List[Tuple[int, TrajectoryState]] = [(injection_revision_index, current_state)]

    # Get original span text
    original_start = span.span_start_char
    original_end = span.span_end_char
    current_start = original_start
    current_end = original_end

    # Find injection revision
    injection_rev = None
    for rev in revisions:
        if rev.revision_index == injection_revision_index:
            injection_rev = rev
            break

    if injection_rev is None or injection_revision_index >= len(revisions):
        return TrajectoryResult(
            final_state=current_state,
            ambiguity_flag=compute_ambiguity_flag(current_state),
            transition_history=transition_history,
            span_start_char=current_start,
            span_end_char=current_end,
            original_start_char=original_start,
            original_end_char=original_end,
        )

    # Get initial span text
    prev_text = injection_rev.text[current_start:current_end]

    # Track changes across subsequent revisions
    for rev in revisions:
        if rev.revision_index <= injection_revision_index:
            continue

        # Get current span text (assuming same boundaries for simplicity)
        end = min(current_end, len(rev.text))
        start = min(current_start, len(rev.text))
        curr_text = rev.text[start:end] if start < end else ""

        # Classify the edit
        old_tokens = tokenize(prev_text)
        new_tokens = tokenize(curr_text)
        edit = classify_edit(old_tokens, new_tokens)

        # Compute state transition
        new_state = compute_transition(current_state, edit)

        if new_state != current_state:
            transition_history.append((rev.revision_index, new_state))
            current_state = new_state

        prev_text = curr_text

    return TrajectoryResult(
        final_state=current_state,
        ambiguity_flag=compute_ambiguity_flag(current_state),
        transition_history=transition_history,
        span_start_char=current_start,
        span_end_char=current_end,
        original_start_char=original_start,
        original_end_char=original_end,
    )

def determine_trajectory_state(
    sigs: Dict[str, Any]
) -> Tuple[TrajectoryState, AmbiguityFlag]:
    """
    Determine trajectory state EARNED by causal signatures.

    Trajectory states represent the degree of integration between
    injected content and the author's revision process:

    - COLD: Initial state, no causal integration detected
    - WARM: Emerging coupling, partial biometric alignment
    - ASSIMILATED: Full integration with irreversible process signatures

    Args:
        sigs: Dict containing causal signature values:
            - repair_locality: Token distance between failures and repairs
            - resource_coupling: Pearson r between failures and simplification
            - is_plausible: Boolean indicating within human baselines

    Returns:
        Tuple of (TrajectoryState, AmbiguityFlag)

    See docs/THRESHOLDS.md for detailed threshold justifications.
    """
    locality = sigs.get("repair_locality", 0.0)
    coupling = abs(sigs.get("resource_coupling", 0.0))
    is_plausible = sigs.get("is_plausible", False)

    # 1. ASSIMILATED: Strongest coupling (> 0.7) + biometric plausibility
    # MUST be earned by irreversible process signatures demonstrating
    # full integration into the author's cognitive production workflow.
    # Threshold: COUPLING_ASSIMILATED_THRESHOLD (0.7)
    if is_plausible and coupling > COUPLING_ASSIMILATED_THRESHOLD:
        return TrajectoryState.ASSIMILATED, AmbiguityFlag.HIGH

    # 2. WARM: Emerging coupling (>= 0.4) with acceptable locality (<= 4.5)
    # Indicates partial biometric alignment where the injection is being
    # actively edited but not yet fully assimilated.
    # Thresholds: COUPLING_WARM_MINIMUM (0.4), LOCALITY_WARM_MAX (4.5)
    if coupling >= COUPLING_WARM_MINIMUM and locality <= LOCALITY_WARM_MAX:
        return TrajectoryState.WARM, AmbiguityFlag.MEDIUM

    # 3. COLD: Initial state, no causal integration detected
    # Either no coupling or coupling too weak to indicate integration.
    return TrajectoryState.COLD, AmbiguityFlag.NONE

def update_span_with_trajectory(span: InjectionSpan, res: TrajectoryResult) -> InjectionSpan:
    """Update an injection span with trajectory analysis results."""
    return InjectionSpan(
        doc_id=span.doc_id, revision_id=span.revision_id, injection_id=span.injection_id,
        injection_level=span.injection_level, trajectory_state=res.final_state, ambiguity_flag=res.ambiguity_flag,
        span_start_char=span.span_start_char, span_end_char=span.span_end_char,
        span_start_sentence=span.span_start_sentence, span_end_sentence=span.span_end_sentence,
        generator_class=span.generator_class, prompt_hash=span.prompt_hash, rng_seed=span.rng_seed,
        provenance_hash=span.provenance_hash, label=span.label, causal_trace=span.causal_trace,
        original_start_char=span.original_start_char, original_end_char=span.original_end_char,
        biometric_salt=span.biometric_salt
    )
