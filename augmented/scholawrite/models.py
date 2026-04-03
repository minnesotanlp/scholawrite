"""Dynamic model discovery and selection via OpenRouter API.

This module queries OpenRouter at runtime to discover available models
and selects a diverse set across vendors and generations for robust
dataset generation that works regardless of when the code is run.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import httpx

__all__ = ["ModelRegistry", "discover_models", "ModelInfo"]


# Vendor priority and recognition patterns
VENDOR_PATTERNS = {
    "anthropic": (1, re.compile(r"^anthropic/|^claude", re.IGNORECASE)),
    "openai": (2, re.compile(r"^openai/|^gpt-", re.IGNORECASE)),
    "google": (3, re.compile(r"^google/|^gemini", re.IGNORECASE)),
    "meta": (4, re.compile(r"^meta-llama/|^llama", re.IGNORECASE)),
    "mistral": (5, re.compile(r"^mistralai/|^mistral", re.IGNORECASE)),
    "cohere": (6, re.compile(r"^cohere/", re.IGNORECASE)),
    "deepseek": (7, re.compile(r"^deepseek/", re.IGNORECASE)),
    "qwen": (8, re.compile(r"^qwen/", re.IGNORECASE)),
    "perplexity": (9, re.compile(r"^perplexity/", re.IGNORECASE)),
    "nous": (10, re.compile(r"^nousresearch/|^nous", re.IGNORECASE)),
}

# Models to always exclude (specialized, non-text, or problematic)
EXCLUDE_PATTERNS = [
    re.compile(r"vision|image|audio|video|embed|moderat", re.IGNORECASE),
    re.compile(r"instruct-\d+k", re.IGNORECASE),  # Extended context variants
    re.compile(r"free$", re.IGNORECASE),  # Free tier often rate-limited
    re.compile(r"preview|beta|alpha|experimental", re.IGNORECASE),
]

# Flagship model indicators (higher is more flagship)
FLAGSHIP_INDICATORS = [
    (re.compile(r"opus|sonnet|4o|gpt-4|pro|ultra|large", re.IGNORECASE), 10),
    (re.compile(r"haiku|mini|small|nano|tiny|lite", re.IGNORECASE), -5),
    (re.compile(r"latest|turbo|flash", re.IGNORECASE), 5),
    (re.compile(r"405b|70b|72b|llama-3\.1", re.IGNORECASE), 8),
    (re.compile(r"8b|7b|3b|1b", re.IGNORECASE), -3),
]


@dataclass
class ModelCapabilities:
    """Capabilities and supported generation parameters for a model.

    Only tracks parameters relevant to text generation.
    """
    supports_temperature: bool = True
    supports_top_p: bool = True
    supports_top_k: bool = False
    supports_presence_penalty: bool = False
    supports_frequency_penalty: bool = False
    supports_repetition_penalty: bool = False
    supports_min_p: bool = False
    supports_seed: bool = False
    supports_stop: bool = True

    def get_supported_params(self) -> Set[str]:
        """Return set of supported parameter names."""
        supported = {"temperature", "max_tokens"}  # Always supported
        if self.supports_top_p:
            supported.add("top_p")
        if self.supports_top_k:
            supported.add("top_k")
        if self.supports_presence_penalty:
            supported.add("presence_penalty")
        if self.supports_frequency_penalty:
            supported.add("frequency_penalty")
        if self.supports_repetition_penalty:
            supported.add("repetition_penalty")
        if self.supports_min_p:
            supported.add("min_p")
        if self.supports_seed:
            supported.add("seed")
        if self.supports_stop:
            supported.add("stop")
        return supported


# Fallback capabilities by vendor (used when API doesn't provide specifics)
# These are conservative defaults that should work even if model evolves
_VENDOR_CAPABILITIES_FALLBACK = {
    "anthropic": ModelCapabilities(
        supports_top_p=True,
        supports_top_k=True,
        supports_stop=True,
    ),
    "openai": ModelCapabilities(
        supports_top_p=True,
        supports_presence_penalty=True,
        supports_frequency_penalty=True,
        supports_seed=True,
        supports_stop=True,
    ),
    "google": ModelCapabilities(
        supports_top_p=True,
        supports_top_k=True,
        supports_stop=True,
    ),
    "meta": ModelCapabilities(
        supports_top_p=True,
        supports_top_k=True,
        supports_repetition_penalty=True,
    ),
    "mistral": ModelCapabilities(
        supports_top_p=True,
        supports_presence_penalty=True,
        supports_frequency_penalty=True,
        supports_stop=True,
    ),
    "cohere": ModelCapabilities(
        supports_top_p=True,
        supports_top_k=True,
        supports_presence_penalty=True,
        supports_frequency_penalty=True,
    ),
    "deepseek": ModelCapabilities(
        supports_top_p=True,
        supports_presence_penalty=True,
        supports_frequency_penalty=True,
        supports_stop=True,
    ),
    "qwen": ModelCapabilities(
        supports_top_p=True,
        supports_top_k=True,
        supports_repetition_penalty=True,
    ),
}


def _parse_capabilities_from_api(model_data: Dict[str, Any], vendor: str) -> ModelCapabilities:
    """Parse model capabilities from OpenRouter API response.

    OpenRouter provides capability information in the model data.
    We use this when available, falling back to vendor defaults.

    Args:
        model_data: Model data from OpenRouter API
        vendor: Detected vendor name

    Returns:
        ModelCapabilities instance
    """
    # Check for supported_parameters if provided
    supported = set(model_data.get("supported_parameters", []))

    # Start with vendor fallback as base
    fallback = _VENDOR_CAPABILITIES_FALLBACK.get(vendor, ModelCapabilities())

    # If API provides specific capability info, use it
    if supported:
        return ModelCapabilities(
            supports_temperature="temperature" in supported or True,  # Always true
            supports_top_p="top_p" in supported,
            supports_top_k="top_k" in supported,
            supports_presence_penalty="presence_penalty" in supported,
            supports_frequency_penalty="frequency_penalty" in supported,
            supports_repetition_penalty="repetition_penalty" in supported,
            supports_min_p="min_p" in supported,
            supports_seed="seed" in supported,
            supports_stop="stop" in supported,
        )

    # Use vendor fallback as default
    return fallback


@dataclass
class ModelInfo:
    """Information about an available model."""
    id: str
    name: str
    vendor: str
    context_length: int
    pricing_prompt: float  # per 1M tokens
    pricing_completion: float  # per 1M tokens
    flagship_score: int = 0
    vendor_priority: int = 99
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)

    @property
    def is_capable(self) -> bool:
        """Check if model is capable enough for scholarly generation."""
        return self.context_length >= 4096

    @property
    def cost_per_1k(self) -> float:
        """Approximate cost per 1k tokens (combined in/out)."""
        return (self.pricing_prompt + self.pricing_completion) / 2000

    def filter_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter parameters to only those supported by this model."""
        supported = self.capabilities.get_supported_params()
        return {k: v for k, v in params.items() if k in supported and v is not None}


@dataclass
class ModelRegistry:
    """Registry of discovered models with intelligent selection."""
    models: Dict[str, ModelInfo] = field(default_factory=dict)
    by_vendor: Dict[str, List[ModelInfo]] = field(default_factory=dict)
    _discovered: bool = False

    async def discover(self, api_key: Optional[str] = None) -> int:
        """Discover available models from OpenRouter API.

        Returns the number of valid models discovered.
        """
        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY required for model discovery")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch models: {resp.status_code}")

            data = resp.json()

        for model_data in data.get("data", []):
            model_id = model_data.get("id", "")

            # Skip excluded models
            if any(p.search(model_id) for p in EXCLUDE_PATTERNS):
                continue

            # Determine vendor
            vendor = "other"
            vendor_priority = 99
            for v_name, (v_priority, v_pattern) in VENDOR_PATTERNS.items():
                if v_pattern.search(model_id):
                    vendor = v_name
                    vendor_priority = v_priority
                    break

            # Calculate flagship score
            flagship_score = 0
            for pattern, score in FLAGSHIP_INDICATORS:
                if pattern.search(model_id):
                    flagship_score += score

            # Extract pricing (OpenRouter returns per-token, convert to per-1M)
            pricing = model_data.get("pricing", {})
            pricing_prompt = float(pricing.get("prompt", "0")) * 1_000_000
            pricing_completion = float(pricing.get("completion", "0")) * 1_000_000

            # Parse capabilities from API or fall back to vendor defaults
            capabilities = _parse_capabilities_from_api(model_data, vendor)

            info = ModelInfo(
                id=model_id,
                name=model_data.get("name", model_id),
                vendor=vendor,
                context_length=model_data.get("context_length", 4096),
                pricing_prompt=pricing_prompt,
                pricing_completion=pricing_completion,
                flagship_score=flagship_score,
                vendor_priority=vendor_priority,
                capabilities=capabilities,
            )

            if info.is_capable:
                self.models[model_id] = info
                if vendor not in self.by_vendor:
                    self.by_vendor[vendor] = []
                self.by_vendor[vendor].append(info)

        # Sort each vendor's models by flagship score
        for vendor in self.by_vendor:
            self.by_vendor[vendor].sort(key=lambda m: -m.flagship_score)

        self._discovered = True
        return len(self.models)

    def select_diverse_set(
        self,
        count: int = 12,
        max_per_vendor: int = 3,
        include_budget: bool = True,
        cost_limit_per_1k: Optional[float] = None,
    ) -> List[str]:
        """Select a diverse set of models across vendors and capability levels.

        Args:
            count: Target number of models to select
            max_per_vendor: Maximum models from any single vendor
            include_budget: Include some lower-cost models for variety
            cost_limit_per_1k: Optional cost limit per 1k tokens

        Returns:
            List of model IDs
        """
        if not self._discovered:
            raise RuntimeError("Must call discover() before selecting models")

        selected: List[ModelInfo] = []
        vendor_counts: Dict[str, int] = {}

        # Sort vendors by priority
        sorted_vendors = sorted(
            self.by_vendor.keys(),
            key=lambda v: VENDOR_PATTERNS.get(v, (99, None))[0]
        )

        # Phase 1: Get flagship from each major vendor
        for vendor in sorted_vendors:
            if len(selected) >= count:
                break
            models = self.by_vendor[vendor]
            for model in models:
                if cost_limit_per_1k and model.cost_per_1k > cost_limit_per_1k:
                    continue
                if vendor_counts.get(vendor, 0) >= max_per_vendor:
                    break
                if model.id not in [m.id for m in selected]:
                    selected.append(model)
                    vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
                    break

        # Phase 2: Add second-tier models from major vendors
        for vendor in sorted_vendors[:6]:  # Top 6 vendors
            if len(selected) >= count:
                break
            models = self.by_vendor.get(vendor, [])
            for model in models[1:]:  # Skip flagship (already added)
                if cost_limit_per_1k and model.cost_per_1k > cost_limit_per_1k:
                    continue
                if vendor_counts.get(vendor, 0) >= max_per_vendor:
                    break
                if model.id not in [m.id for m in selected]:
                    selected.append(model)
                    vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
                    if len(selected) >= count:
                        break

        # Phase 3: Fill remaining with budget-friendly options if requested
        if include_budget and len(selected) < count:
            all_models = sorted(self.models.values(), key=lambda m: m.cost_per_1k)
            for model in all_models:
                if len(selected) >= count:
                    break
                if model.id not in [m.id for m in selected]:
                    if vendor_counts.get(model.vendor, 0) < max_per_vendor:
                        selected.append(model)
                        vendor_counts[model.vendor] = vendor_counts.get(model.vendor, 0) + 1

        return [m.id for m in selected]

    def get_fallback_sequence(self, primary_model: str, max_fallbacks: int = 3) -> List[str]:
        """Get a sequence of fallback models for a given primary model.

        Returns models from the same vendor first, then other vendors,
        prioritized by capability similarity.
        """
        if primary_model not in self.models:
            # Return generic fallbacks
            return self.select_diverse_set(count=max_fallbacks)

        primary = self.models[primary_model]
        fallbacks: List[str] = []

        # Same vendor, similar capability
        for model in self.by_vendor.get(primary.vendor, []):
            if model.id != primary_model and len(fallbacks) < max_fallbacks:
                fallbacks.append(model.id)

        # Different vendors, similar flagship score
        if len(fallbacks) < max_fallbacks:
            other_models = [
                m for m in self.models.values()
                if m.vendor != primary.vendor and m.id not in fallbacks
            ]
            other_models.sort(key=lambda m: abs(m.flagship_score - primary.flagship_score))
            for model in other_models:
                if len(fallbacks) >= max_fallbacks:
                    break
                fallbacks.append(model.id)

        return fallbacks


# Module-level registry instance
_registry: Optional[ModelRegistry] = None


async def discover_models(api_key: Optional[str] = None, force: bool = False) -> ModelRegistry:
    """Discover available models and return the registry.

    This is the main entry point for model discovery. It caches the result
    so subsequent calls return the same registry unless force=True.
    """
    global _registry
    if _registry is None or force:
        _registry = ModelRegistry()
        await _registry.discover(api_key)
    return _registry


def get_registry() -> Optional[ModelRegistry]:
    """Get the current registry without discovering (may be None)."""
    return _registry
