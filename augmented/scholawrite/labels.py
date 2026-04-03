"""Writing intention label parsing and normalization.

Handles normalization of LLM outputs to the ScholaWrite 15-label taxonomy.
This module provides a single source of truth for label parsing logic.
"""
from __future__ import annotations

from typing import List

__all__ = ["WRITING_INTENTIONS", "parse_label", "is_valid_label"]

# The canonical 15-label ScholaWrite taxonomy for writing intentions
WRITING_INTENTIONS: List[str] = [
    "Text Production",
    "Visual Formatting",
    "Clarity",
    "Section Planning",
    "Structural",
    "Object Insertion",
    "Cross-reference",
    "Fluency",
    "Idea Generation",
    "Idea Organization",
    "Citation Integration",
    "Coherence",
    "Linguistic Style",
    "Scientific Accuracy",
    "Macro Insertion",
]


def parse_label(predicted_label: str, fallback: str = "Invalid", verbose: bool = False) -> str:
    """Normalize LLM output to a valid writing intention label.

    LLMs often produce verbose responses like "The writing intention is 'Clarity'
    because..." rather than just "Clarity". This function extracts the canonical
    label from such outputs.

    Args:
        predicted_label: Raw LLM output string to normalize.
        fallback: Value to return if no valid label is found. Defaults to "Invalid".
        verbose: If True, print unrecognized labels for debugging. Defaults to False.

    Returns:
        A canonical label from WRITING_INTENTIONS, or fallback if none found.

    Examples:
        >>> parse_label("Clarity")
        'Clarity'
        >>> parse_label("The intention is Text Production because...")
        'Text Production'
        >>> parse_label("gibberish")
        'Invalid'
    """
    if not predicted_label:
        return fallback

    # Exact match
    if predicted_label in WRITING_INTENTIONS:
        return predicted_label

    # Substring match (handles verbose LLM outputs)
    for label in WRITING_INTENTIONS:
        if label in predicted_label:
            return label

    # No match found
    if verbose:
        print(f"[labels] Unrecognized label: {predicted_label}")
    return fallback


def is_valid_label(label: str) -> bool:
    """Check if a label is in the canonical taxonomy.

    Args:
        label: Label string to validate.

    Returns:
        True if the label is in WRITING_INTENTIONS, False otherwise.
    """
    return label in WRITING_INTENTIONS
