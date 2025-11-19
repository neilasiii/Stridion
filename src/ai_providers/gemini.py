"""
Google Gemini AI provider implementation.
"""

import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from .base import AIProvider, Message, AgentConfig


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    # Model mappings
    # Note: Using Gemini 2.x models (1.5 models are deprecated)
    MODELS = {
        "fast": "gemini-2.5-flash",
        "default": "gemini-2.5-flash",  # Using flash as default for better availability
        "powerful": "gemini-2.5-pro"
    }

    def validate_config(self) -> None:
        """Validate Gemini API configuration."""
        api_key = self.config.get('api_key') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment "
                "variable or provide 'api_key' in config."
            )
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

    def get_model_name(self, preference: str = "default") -> str:
        """Get Gemini model name based on preference."""
        return self.MODELS.get(preference, self.MODELS["default"])

    def _format_messages(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Format messages for Gemini API.

        Returns:
            Tuple of (system_instruction, formatted_messages)
        """
        system_instruction = None
        formatted_messages = []

        # Extract system message
        for msg in messages:
            if msg.role == 'system':
                system_instruction = msg.content
            elif msg.role == 'assistant':
                # Gemini uses 'model' instead of 'assistant'
                formatted_messages.append({
                    'role': 'model',
                    'parts': [msg.content]
                })
            else:
                formatted_messages.append({
                    'role': msg.role,
                    'parts': [msg.content]
                })

        # Use agent system prompt if provided
        if agent_config and agent_config.system_prompt:
            system_instruction = agent_config.system_prompt

        return system_instruction, formatted_messages

    def chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Send chat request to Gemini API.

        Args:
            messages: Conversation messages
            agent_config: Agent configuration
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool definitions for function calling

        Returns:
            Assistant's response text
        """
        system_instruction, formatted_messages = self._format_messages(
            messages, agent_config
        )

        model_name = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        # Create model with configuration
        generation_config = {
            'temperature': temperature,
        }
        if max_tokens:
            generation_config['max_output_tokens'] = max_tokens

        # Convert tools to Gemini format if provided
        gemini_tools = None
        if tools:
            gemini_tools = [genai.protos.Tool(
                function_declarations=[
                    genai.protos.FunctionDeclaration(
                        name=tool["name"],
                        description=tool["description"],
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                k: genai.protos.Schema(
                                    type=self._get_gemini_type(v.get("type", "string")),
                                    description=v.get("description", "")
                                )
                                for k, v in tool["parameters"].get("properties", {}).items()
                            },
                            required=tool["parameters"].get("required", [])
                        )
                    )
                    for tool in tools
                ]
            )]

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_instruction,
            tools=gemini_tools
        )

        # Start chat with history
        chat = model.start_chat(history=formatted_messages[:-1] if len(formatted_messages) > 1 else [])

        # Send the last message
        last_message = formatted_messages[-1]['parts'][0] if formatted_messages else ""
        response = chat.send_message(last_message)

        # Check if response contains function calls (will be handled by caller)
        # For now, just return the text. Tool calling loop will be in CoachService
        return response

    def _get_gemini_type(self, type_str: str) -> genai.protos.Type:
        """Convert JSON schema type to Gemini type."""
        type_map = {
            "string": genai.protos.Type.STRING,
            "integer": genai.protos.Type.INTEGER,
            "number": genai.protos.Type.NUMBER,
            "boolean": genai.protos.Type.BOOLEAN,
            "object": genai.protos.Type.OBJECT,
            "array": genai.protos.Type.ARRAY
        }
        return type_map.get(type_str, genai.protos.Type.STRING)

    def stream_chat(
        self,
        messages: List[Message],
        agent_config: Optional[AgentConfig] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Stream chat response from Gemini API."""
        system_instruction, formatted_messages = self._format_messages(
            messages, agent_config
        )

        model_name = self.get_model_name(
            agent_config.model_preference if agent_config else "default"
        )

        # Create model with configuration
        generation_config = {
            'temperature': temperature,
        }
        if max_tokens:
            generation_config['max_output_tokens'] = max_tokens

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_instruction
        )

        # Start chat with history
        chat = model.start_chat(history=formatted_messages[:-1] if len(formatted_messages) > 1 else [])

        # Stream the last message
        last_message = formatted_messages[-1]['parts'][0] if formatted_messages else ""
        response = chat.send_message(last_message, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text
