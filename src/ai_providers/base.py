"""
Base interface for AI providers.

This module defines the abstract base class that all AI providers must implement,
ensuring a consistent interface regardless of the underlying AI service.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a message in a conversation."""
    role: str  # 'user', 'assistant', or 'system'
    content: str


@dataclass
class AgentConfig:
    """Configuration for a coaching agent."""
    name: str
    description: str
    system_prompt: str
    model_preference: str = "default"  # "default", "fast", or "powerful"


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI provider implementations (Claude, ChatGPT, Gemini, Ollama) must
    inherit from this class and implement its abstract methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI provider.

        Args:
            config: Provider-specific configuration (API keys, endpoints, etc.)
        """
        self.config = config
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate that the provider has all required configuration.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Send a chat request to the AI provider and get a response.

        Args:
            messages: List of conversation messages
            agent_config: Optional agent configuration for system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response (None for provider default)

        Returns:
            The AI's response as a string

        Raises:
            Exception: If the API call fails
        """
        pass

    @abstractmethod
    def stream_chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Stream a chat response from the AI provider.

        Args:
            messages: List of conversation messages
            agent_config: Optional agent configuration for system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response (None for provider default)

        Yields:
            Chunks of the response as they arrive

        Raises:
            Exception: If the API call fails
        """
        pass

    @abstractmethod
    def get_model_name(self, preference: str = "default") -> str:
        """
        Get the actual model name based on preference.

        Args:
            preference: "default", "fast", or "powerful"

        Returns:
            The provider-specific model identifier
        """
        pass

    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return self.__class__.__name__.replace("Provider", "")
