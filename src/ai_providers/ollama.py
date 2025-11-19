"""
Ollama local LLM provider implementation.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional

from .base import AIProvider, Message, AgentConfig


class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    # Model mappings (user can customize these based on installed models)
    MODELS = {
        "fast": "llama3.2:latest",
        "default": "llama3.1:latest",
        "powerful": "llama3.1:70b"
    }

    def validate_config(self) -> None:
        """Validate Ollama configuration."""
        # Get Ollama host (default to localhost)
        self.host = self.config.get('host') or os.getenv('OLLAMA_HOST', 'http://localhost:11434')

        # Get default model if specified
        default_model = self.config.get('default_model') or os.getenv('OLLAMA_MODEL')
        if default_model:
            self.MODELS['default'] = default_model

        # Verify Ollama is accessible
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ValueError(
                f"Cannot connect to Ollama at {self.host}. "
                f"Make sure Ollama is running. Error: {e}"
            )

    def get_model_name(self, preference: str = "default") -> str:
        """Get Ollama model name based on preference."""
        return self.MODELS.get(preference, self.MODELS["default"])

    def _format_messages(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Format messages for Ollama API.

        Returns:
            Tuple of (system_prompt, formatted_messages)
        """
        system_prompt = None
        formatted_messages = []

        for msg in messages:
            if msg.role == 'system':
                system_prompt = msg.content
            else:
                formatted_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })

        # Use agent system prompt if provided
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
        """Send chat request to Ollama API."""
        system_prompt, formatted_messages = self._format_messages(
            messages, agent_config
        )

        model = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        payload = {
            'model': model,
            'messages': formatted_messages,
            'stream': False,
            'options': {
                'temperature': temperature,
            }
        }

        if system_prompt:
            # Add system message as first message
            payload['messages'].insert(0, {
                'role': 'system',
                'content': system_prompt
            })

        if max_tokens:
            payload['options']['num_predict'] = max_tokens

        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=300  # 5 minute timeout for local inference
        )
        response.raise_for_status()

        return response.json()['message']['content']

    def stream_chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Stream chat response from Ollama API."""
        system_prompt, formatted_messages = self._format_messages(
            messages, agent_config
        )

        model = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        payload = {
            'model': model,
            'messages': formatted_messages,
            'stream': True,
            'options': {
                'temperature': temperature,
            }
        }

        if system_prompt:
            # Add system message as first message
            payload['messages'].insert(0, {
                'role': 'system',
                'content': system_prompt
            })

        if max_tokens:
            payload['options']['num_predict'] = max_tokens

        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            stream=True,
            timeout=300  # 5 minute timeout for local inference
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
