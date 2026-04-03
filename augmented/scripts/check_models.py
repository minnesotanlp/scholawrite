"""
Purpose: scripts/check_models.py
Outputs: Async validation of model availability on OpenRouter.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from scholawrite.openrouter import OpenRouterClient
from scholawrite.banner import print_banner
from scholawrite.cli import warning, success, info

__all__ = ["main"]

REQUESTED_MODELS = [
    "openai/gpt-5.2-pro", "anthropic/claude-opus-4.5", "openai/o3-deep-research",
    "anthropic/claude-opus-4.1", "openai/o1", "anthropic/claude-3.5-sonnet",
    "openai/gpt-4-turbo", "google/gemini-3-pro-preview", "anthropic/claude-haiku-4.5",
    "qwen/qwen3-max", "nousresearch/hermes-4-405b", "x-ai/grok-4",
    "google/gemini-2.5-pro", "x-ai/grok-3", "anthropic/claude-sonnet-4",
    "cohere/command-a", "anthropic/claude-3.7-sonnet", "qwen/qwen-max",
    "mistralai/mistral-large-2411", "raifle/sorcererlm-8x22b", "cohere/command-r-plus-08-2024",
    "mistralai/mistral-large", "moonshotai/kimi-k2.5", "writer/palmyra-x5",
    "minimax/minimax-m2.1", "z-ai/glm-4.7", "google/gemini-3-flash-preview",
    "z-ai/glm-4.6v", "google/gemini-2.5-pro", "google/gemini-2.0-flash-001",
    "x-ai/grok-4.1-fast", "cohere/command-r7b-12-2024", "cohere/command",
    "amazon/nova-premier-v1", "amazon/nova-2-lite-v1", "qwen/qwq-32b",
    "01-ai/yi-1.5-34b-chat", "liuhaotian/llava-yi-34b", "deepseek/deepseek-v3.2-speciale",
    "deepseek/deepseek-chat-v3.1", "mistralai/mistral-small-creative",
    "meta-llama/llama-4-maverick", "meta-llama/llama-4-scout",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5", "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "gryphe/mythomax-l2-13b", "alpindale/goliath-120b", "arcee-ai/trinity-large-preview:free"
]

async def check(models_file: Path | None = None, verbose: bool = False) -> int:
    """Check model availability on OpenRouter."""
    print_banner("OpenRouter Model Checker")

    # Load models from file if provided, otherwise use defaults
    models_to_check = REQUESTED_MODELS
    if models_file and models_file.exists():
        data = json.loads(models_file.read_text(encoding="utf-8"))
        models_to_check = [m["id"] for m in data if "id" in m]
        print(info(f"Loaded {len(models_to_check)} models from {models_file}"))

    client = OpenRouterClient.from_env()
    try:
        # Use underlying client to get models list
        resp = await client._client.get(f"{client.base_url}/models")
        available = {m['id'] for m in resp.json().get('data', [])}

        valid = [m for m in models_to_check if m in available]
        invalid = [m for m in models_to_check if m not in available]

        print(info(f"Available requested models: {len(valid)}/{len(models_to_check)}"))

        if verbose:
            print(info("Available models:"))
            for m in sorted(valid):
                print(f"  + {m}")

        if invalid:
            print(warning(f"Missing models ({len(invalid)}):"))
            for m in sorted(invalid):
                print(f"  - {m}")
            return 1
        print(success("All requested models are available."))
        return 0
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate model availability on OpenRouter API. Checks if requested "
                    "models are accessible with the current API key.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --models-file configs/openrouter_models.json
  %(prog)s -v
  %(prog)s --models-file models.json --verbose

Environment variables:
  OPENROUTER_API_KEY: Required API key for OpenRouter authentication

Exit codes:
  0: All requested models are available
  1: One or more models are missing or unavailable
"""
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=None,
        help="Path to JSON file containing model configurations. If not specified, "
             "uses the built-in list of requested models. File should be an array "
             "of objects with 'id' fields."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output including list of all available models."
    )
    args = parser.parse_args()

    return asyncio.run(check(args.models_file, args.verbose))


if __name__ == "__main__":
    sys.exit(main())