"""Asynchronous OpenRouter API client with retry and connection pooling."""
from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

__all__ = ["OpenRouterClient", "OpenRouterError", "TruncationError"]


class OpenRouterError(RuntimeError):
    """Base exception for OpenRouter API failures."""


class TruncationError(OpenRouterError):
    """Raised when response was truncated due to max_tokens limit."""


class UnsupportedParameterError(OpenRouterError):
    """Raised when a model doesn't support certain parameters."""


# Parameters that may not be supported by all models
# When a 400 error mentions these, we retry without them
_OPTIONAL_PARAMS = frozenset([
    "top_p", "top_k", "presence_penalty", "frequency_penalty",
    "repetition_penalty", "min_p", "top_a", "seed",
    "logit_bias", "logprobs", "top_logprobs", "stop",
])


@dataclass
class OpenRouterClient:
    """
    High-concurrency client for OpenRouter.
    Implements aggressive retries and connection pooling.
    Gracefully handles models that don't support certain parameters.
    """
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_s: int = 120
    max_retries: int = 5

    _client: httpx.AsyncClient = field(init=False)
    _unsupported_params: Dict[str, set] = field(default_factory=dict, init=False)

    def __post_init__(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "ScholaWrite-Augmented"
        }
        # Connection pool optimized for 150+ concurrent LLM calls
        object.__setattr__(self, "_client", httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(self.timeout_s),
            limits=httpx.Limits(max_connections=150, max_keepalive_connections=30)
        ))
        object.__setattr__(self, "_unsupported_params", {})

    @classmethod
    def from_env(cls) -> OpenRouterClient:
        key = os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise OpenRouterError("OPENROUTER_API_KEY environment variable missing")
        return cls(api_key=key)

    async def close(self):
        await self._client.aclose()

    async def list_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from OpenRouter API."""
        resp = await self._client.get(f"{self.base_url}/models")
        if resp.status_code != 200:
            raise OpenRouterError(f"Failed to fetch models: {resp.status_code}")
        return resp.json().get("data", [])

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        reject_truncation: bool = True,
        # Optional parameters - only included if provided and supported
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        min_p: Optional[float] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **extra_params,
    ) -> Dict[str, Any]:
        """Execute a chat completion with exponential backoff retries.

        Supports additional OpenAI-compatible parameters. Parameters that aren't
        supported by a specific model are automatically removed on retry.

        Args:
            model: Model ID (e.g., "anthropic/claude-3-opus")
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            reject_truncation: Raise TruncationError if response truncated
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling limit
            presence_penalty: Penalty for new topics (-2.0 to 2.0)
            frequency_penalty: Penalty for repetition (-2.0 to 2.0)
            repetition_penalty: Alternative repetition penalty
            min_p: Minimum probability threshold
            seed: Random seed for reproducibility
            stop: Stop sequences
            **extra_params: Additional model-specific parameters

        Returns:
            API response dict with 'choices' containing generated content.

        Raises:
            OpenRouterError: On API errors after retries exhausted
            TruncationError: If reject_truncation=True and response truncated
        """
        # Build base payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }

        # Add optional parameters if provided
        optional = {
            "top_p": top_p,
            "top_k": top_k,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "repetition_penalty": repetition_penalty,
            "min_p": min_p,
            "seed": seed,
            "stop": stop,
        }
        optional.update(extra_params)

        # Filter out None values and previously known unsupported params for this model
        model_unsupported = self._unsupported_params.get(model, set())
        for key, value in optional.items():
            if value is not None and key not in model_unsupported:
                payload[key] = value

        for attempt in range(self.max_retries):
            try:
                resp = await self._client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )

                if resp.status_code == 429:  # Rate Limit
                    await asyncio.sleep((2 ** attempt) + 2)
                    continue

                if resp.status_code >= 500:  # Server errors
                    await asyncio.sleep(attempt + 1)
                    continue

                if resp.status_code == 400:
                    # Check if error is due to unsupported parameter
                    error_text = resp.text.lower()
                    removed_param = None
                    for param in _OPTIONAL_PARAMS:
                        if param in error_text or param.replace("_", "") in error_text:
                            # Mark as unsupported for this model
                            if model not in self._unsupported_params:
                                self._unsupported_params[model] = set()
                            self._unsupported_params[model].add(param)
                            # Remove from payload and retry
                            if param in payload:
                                del payload[param]
                                removed_param = param
                                break

                    if removed_param:
                        # Retry without the unsupported parameter
                        continue
                    else:
                        raise OpenRouterError(f"API Error 400: {resp.text}")

                if resp.status_code != 200:
                    raise OpenRouterError(f"API Error {resp.status_code}: {resp.text}")

                result = resp.json()

                # Check for truncation
                if reject_truncation:
                    choices = result.get("choices", [])
                    if choices:
                        finish_reason = choices[0].get("finish_reason", "")
                        if finish_reason == "length":
                            raise TruncationError(
                                f"Response truncated (finish_reason=length) for model {model}"
                            )

                return result

            except TruncationError:
                raise  # Don't retry truncation, bubble up immediately
            except (httpx.HTTPError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise OpenRouterError(
                        f"Request failed after {self.max_retries} attempts: {e}"
                    )
                await asyncio.sleep(2 ** attempt)

        return {}
