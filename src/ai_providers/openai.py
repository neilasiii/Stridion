"""
OpenAI (ChatGPT) AI provider implementation.
"""

import os
from typing import List, Dict, Any, Optional
import openai

from .base import AIProvider, Message, AgentConfig


class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT API provider."""

    # Model mappings
    MODELS = {
        "fast": "gpt-4o-mini",
        "default": "gpt-4o",
        "powerful": "gpt-4o"
    }

    def validate_config(self) -> None:
        """Validate OpenAI API configuration."""
        api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment "
                "variable or provide 'api_key' in config."
            )
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=self.api_key)

    def get_model_name(self, preference: str = "default") -> str:
        """Get OpenAI model name based on preference."""
        return self.MODELS.get(preference, self.MODELS["default"])

    def _format_messages(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None
    ) -> List[Dict[str, str]]:
        """
        Format messages for OpenAI API.

        Returns:
            List of formatted messages
        """
        formatted_messages = []

        # Add agent system prompt if provided
        if agent_config and agent_config.system_prompt:
            formatted_messages.append({
                'role': 'system',
                'content': agent_config.system_prompt
            })

        # Add conversation messages
        for msg in messages:
            formatted_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        return formatted_messages

    def chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Send chat request to OpenAI API."""
        formatted_messages = self._format_messages(messages, agent_config)

        model = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        kwargs = {
            'model': model,
            'messages': formatted_messages,
            'temperature': temperature,
        }

        if max_tokens:
            kwargs['max_tokens'] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def stream_chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Stream chat response from OpenAI API."""
        formatted_messages = self._format_messages(messages, agent_config)

        model = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        kwargs = {
            'model': model,
            'messages': formatted_messages,
            'temperature': temperature,
            'stream': True
        }

        if max_tokens:
            kwargs['max_tokens'] = max_tokens

        stream = self.client.chat.completions.create(**kwargs)

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
