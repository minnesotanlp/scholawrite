"""Generator capability tiers for model classification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

__all__ = [
    "GeneratorClass",
    "GeneratorSpec",
    "WEAK_GENERATOR",
    "MID_GENERATOR",
    "STRONG_GENERATOR",
    "get_generator_by_class",
]

class GeneratorClass(str, Enum):
    """Classification of capability for executing scholarly intentions."""
    WEAK = "weak"
    MID = "mid"
    STRONG = "strong"

@dataclass(frozen=True)
class GeneratorSpec:
    """Metadata for a specific flagship model used in the causal pipeline."""
    name: str
    class_label: GeneratorClass
    version: str
    params: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "class_label": self.class_label.value,
            "version": self.version,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneratorSpec":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            class_label=GeneratorClass(data["class_label"]),
            version=data["version"],
            params=data.get("params", {}),
        )

# Predefined capability tiers calibrated for Causal Simulation.
WEAK_GENERATOR = GeneratorSpec(
    name="weak-baseline",
    class_label=GeneratorClass.WEAK,
    version="1.0",
    params={"description": "Baseline model; high probability of syntactic collapse under load"}
)

MID_GENERATOR = GeneratorSpec(
    name="mid-tier",
    class_label=GeneratorClass.MID,
    version="1.0",
    params={"description": "Standard model; exhibits realistic metabolic decay signatures"}
)

STRONG_GENERATOR = GeneratorSpec(
    name="strong-frontier",
    class_label=GeneratorClass.STRONG,
    version="1.0",
    params={"description": "Frontier model; maintains high syntactic depth even during low glucose phases"}
)


def get_generator_by_class(class_label: GeneratorClass) -> GeneratorSpec:
    """Get predefined generator by class label."""
    mapping = {
        GeneratorClass.WEAK: WEAK_GENERATOR,
        GeneratorClass.MID: MID_GENERATOR,
        GeneratorClass.STRONG: STRONG_GENERATOR,
    }
    return mapping[class_label]
