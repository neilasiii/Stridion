"""
Claude/Anthropic AI provider implementation.
"""

import os
from typing import List, Dict, Any, Optional
import anthropic

from .base import AIProvider, Message, AgentConfig


class ClaudeProvider(AIProvider):
    """Anthropic Claude API provider."""

    # Model mappings
    MODELS = {
        "fast": "claude-3-5-haiku-20241022",
        "default": "claude-3-5-sonnet-20241022",
        "powerful": "claude-3-opus-20240229"
    }

    def validate_config(self) -> None:
        """Validate Claude API configuration."""
        api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "Claude API key not found. Set ANTHROPIC_API_KEY environment "
                "variable or provide 'api_key' in config."
            )
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def get_model_name(self, preference: str = "default") -> str:
        """Get Claude model name based on preference."""
        return self.MODELS.get(preference, self.MODELS["default"])

    def _format_messages(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Format messages for Claude API.

        Returns:
            Tuple of (system_prompt, formatted_messages)
        """
        system_prompt = None
        formatted_messages = []

        for msg in messages:
            if msg.role == 'system':
                # Claude uses a separate system parameter
                system_prompt = msg.content
            else:
                formatted_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })

        # If agent config provided, use its system prompt
        if agent_config and agent_config.system_prompt:
            system_prompt = agent_config.system_prompt

        return system_prompt, formatted_messages

    def chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Send chat request to Claude API."""
        system_prompt, formatted_messages = self._format_messages(
            messages, agent_config
        )

        model = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        kwargs = {
            'model': model,
            'messages': formatted_messages,
            'temperature': temperature,
            'max_tokens': max_tokens or 4096
        }

        if system_prompt:
            kwargs['system'] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def stream_chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Stream chat response from Claude API."""
        system_prompt, formatted_messages = self._format_messages(
            messages, agent_config
        )

        model = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        kwargs = {
            'model': model,
            'messages': formatted_messages,
            'temperature': temperature,
            'max_tokens': max_tokens or 4096
        }

        if system_prompt:
            kwargs['system'] = system_prompt

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
