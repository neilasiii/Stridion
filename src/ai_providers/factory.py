"""
Factory for creating AI provider instances.
"""

import os
from typing import Dict, Any

from .base import AIProvider
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider


PROVIDERS = {
    'claude': ClaudeProvider,
    'openai': OpenAIProvider,
    'gemini': GeminiProvider,
    'ollama': OllamaProvider,
}


def get_provider(provider_name: str = None, config: Dict[str, Any] = None) -> AIProvider:
    """
    Get an AI provider instance.

    Args:
        provider_name: Name of the provider ('claude', 'openai', 'gemini', 'ollama').
                      If None, reads from AI_PROVIDER environment variable.
        config: Provider-specific configuration. If None, uses environment variables.

    Returns:
        Configured AIProvider instance

    Raises:
        ValueError: If provider name is invalid or provider is not configured
    """
    if provider_name is None:
        provider_name = os.getenv('AI_PROVIDER', 'claude').lower()

    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available providers: {', '.join(PROVIDERS.keys())}"
        )

    provider_class = PROVIDERS[provider_name]
    return provider_class(config or {})
