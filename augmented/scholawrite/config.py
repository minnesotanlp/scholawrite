"""Configuration loading utilities for ScholaWrite."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = [
    "load_config",
    "get_leakage_patterns",
    "get_academic_markers",
    "get_sensory_anchors",
    "get_placeholder_text",
    "get_discourse_markers",
    "CONFIG_DIR",
]

# Default config directory - can be overridden
# Path: augmented/scholawrite/config.py -> augmented/configs/
CONFIG_DIR = Path(__file__).parent.parent / "configs"


def load_config(name: str, config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load a JSON config file by name.

    Args:
        name: Config file name (without .json extension)
        config_dir: Optional custom config directory

    Returns:
        Parsed JSON as a dictionary, or empty dict if not found
    """
    base_dir = config_dir or CONFIG_DIR
    path = base_dir / f"{name}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@lru_cache(maxsize=1)
def get_leakage_patterns() -> List[str]:
    """Load leakage detection patterns from config.

    Returns:
        List of regex pattern strings with case-insensitivity where appropriate
    """
    data = load_config("leakage_patterns")
    if not data:
        # Fallback minimal patterns
        return [
            r"(?i)\bas an ai\b",
            r"(?i)^here is\b",
            r"(?i)^certainly!",
        ]

    patterns = []
    for category, pattern_list in data.items():
        if category.startswith("_"):
            continue
        if isinstance(pattern_list, list):
            for p in pattern_list:
                # Add case-insensitivity flag if not already present
                # Handle patterns that start with ^ (anchored)
                if p.startswith("(?i)"):
                    patterns.append(p)
                elif p.startswith("^"):
                    # Anchor pattern - insert (?i) after ^
                    patterns.append(f"(?i){p}")
                else:
                    # Regular pattern
                    patterns.append(f"(?i){p}")
    return patterns


@lru_cache(maxsize=1)
def get_academic_markers() -> Dict[str, Any]:
    """Load academic markers from config.

    Returns:
        Dictionary with marker categories and lists
    """
    data = load_config("academic_markers")
    if not data:
        # Fallback minimal markers
        return {
            "logical_connectors": {
                "contrast": ["however", "nevertheless"],
                "causation": ["consequently", "therefore"],
            }
        }
    return data


def get_academic_markers_flat() -> List[str]:
    """Get a flat list of all academic markers for regex matching.

    Returns:
        List of all marker words/phrases
    """
    data = get_academic_markers()
    markers = []

    def extract_strings(obj):
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, str):
                    markers.append(item)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if key.startswith("_"):
                    continue
                extract_strings(value)

    extract_strings(data)
    return markers


@lru_cache(maxsize=1)
def get_sensory_anchors() -> Dict[str, Any]:
    """Load sensory anchor phrases from config.

    Returns:
        Dictionary with anchors and weights
    """
    data = load_config("sensory_anchors")
    if not data:
        # Fallback minimal anchors
        return {
            "anchors": {
                "auditory": ["keyboard clatter nearby"],
                "visual": ["cursor blinking rhythm"],
                "somatic": ["chair lumbar pressure shift"],
                "olfactory": ["stale coffee from mug"],
                "temporal": ["clock check compulsion"],
            },
            "weights": {
                "early_session": {"visual": 0.4, "auditory": 0.35, "somatic": 0.15, "olfactory": 0.05, "temporal": 0.05},
                "mid_session": {"visual": 0.25, "auditory": 0.25, "somatic": 0.30, "olfactory": 0.10, "temporal": 0.10},
                "late_session": {"visual": 0.15, "auditory": 0.15, "somatic": 0.35, "olfactory": 0.10, "temporal": 0.25},
            }
        }
    return data


@lru_cache(maxsize=1)
def get_placeholder_text() -> Dict[str, List[str]]:
    """Load placeholder text components from config.

    Returns:
        Dictionary with intros, bodies, conclusions, etc.
    """
    data = load_config("placeholder_text")
    if not data:
        # Fallback minimal text
        return {
            "intros": ["This empirical investigation demonstrates"],
            "bodies": ["that the underlying assumptions remain foundational."],
            "conclusions": ["Consequently, subsequent research must address these gaps."],
        }
    return data


@lru_cache(maxsize=1)
def get_discourse_markers() -> Dict[str, Any]:
    """Load discourse markers from config.

    Returns:
        Dictionary with repair markers, phase descriptions, etc.
    """
    data = load_config("discourse_markers")
    if not data:
        # Fallback minimal markers
        return {
            "repair_markers": {
                "syntactic_collapse": ["thus, ", "so, ", "consequently, "],
                "lexical_starvation_fallbacks": ["concept", "framework", "element"],
            },
            "phase_descriptions": {
                "Peak": "cognitive resources at maximum capacity",
                "Fatigue": "degraded executive function",
            }
        }
    return data
