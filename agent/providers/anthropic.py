"""Anthropic provider implementation using direct HTTP requests."""

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Optional

import httpx

from .base import LLMProvider, LLMProviderError

if TYPE_CHECKING:
    from .config import LLMProviderConfig


class AnthropicProvider(LLMProvider):
    """Anthropic API provider implementation for Claude models.

    Uses direct HTTP requests."""

    def __init__(self, api_key: str, base_url: Optional[str] = None) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            base_url: Optional custom base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def send_message(
        self,
        config: "LLMProviderConfig",
    ) -> dict[str, Any]:
        """Send a message to Anthropic Claude and get a response.

        Args:
            config: LLMProviderConfig containing all necessary parameters

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderError: If there's an error communicating with Anthropic
        """
        try:
            # Convert messages format from OpenAI-style to Anthropic format
            anthropic_messages = self._convert_messages_format(config.messages)

            # Prepare the request payload
            payload = {
                "model": config.model,
                "messages": anthropic_messages,
                "temperature": config.temperature,
            }

            if config.max_tokens is not None:
                payload["max_tokens"] = config.max_tokens

            if config.top_p is not None:
                payload["top_p"] = config.top_p

            if config.stop_sequences:
                payload["stop_sequences"] = config.stop_sequences

            # Add any additional parameters
            payload.update(config.extra_params)

            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()

                # Extract and return the relevant information
                return {
                    "id": data.get("id"),
                    "model": data.get("model"),
                    "content": data.get("content", [{}])[0].get("text", ""),
                    "role": "assistant",
                    "usage": {
                        "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                    },
                }
        except Exception as e:
            raise LLMProviderError(f"Anthropic API error: {e!s}") from e

    async def _process_streaming_response(
        self,
        response_lines: AsyncIterator[str],
    ) -> AsyncIterator[str]:
        """Process a streaming response from Anthropic API.

        Args:
            response_lines: Async iterator of response lines from the API

        Returns:
            Async iterator that yields processed text chunks
        """
        async for line in response_lines:
            if not line or line.strip() == "":
                continue

            # Remove "data: " prefix if present
            processed_line = line[6:] if line.startswith("data: ") else line

            if processed_line == "[DONE]":
                break

            try:
                data = json.loads(processed_line)

                # Check for delta content in the event type
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("text", ""):
                        yield delta["text"]

                # Check for content in the message_start type
                elif data.get("type") == "message_start":
                    content_blocks = data.get("message", {}).get("content_blocks", [])
                    if content_blocks and content_blocks[0].get("text", ""):
                        yield content_blocks[0]["text"]
            except json.JSONDecodeError:
                continue

    async def send_streaming_message(
        self,
        config: "LLMProviderConfig",
    ) -> AsyncIterator[str]:
        """Send a message to Anthropic Claude and get a streaming response.

        Args:
            config: LLMProviderConfig containing all necessary parameters

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            LLMProviderError: If there's an error communicating with Anthropic
        """
        try:
            # Convert messages format from OpenAI-style to Anthropic format
            anthropic_messages = self._convert_messages_format(config.messages)

            # Prepare the request payload
            payload = {
                "model": config.model,
                "messages": anthropic_messages,
                "temperature": config.temperature,
                "stream": True,
            }

            if config.max_tokens is not None:
                payload["max_tokens"] = config.max_tokens

            if config.top_p is not None:
                payload["top_p"] = config.top_p

            if config.stop_sequences:
                payload["stop_sequences"] = config.stop_sequences

            # Add any additional parameters
            payload.update(config.extra_params)

            # Make the API request with streaming enabled
            async with (
                httpx.AsyncClient() as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json=payload,
                    timeout=120.0,
                ) as response,
            ):
                response.raise_for_status()
                async for chunk in self._process_streaming_response(
                    response.aiter_lines(),
                ):
                    yield chunk
        except Exception as e:
            raise LLMProviderError(f"Anthropic streaming API error: {e!s}") from e

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available Anthropic models.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderError: If there's an error communicating with Anthropic
        """
        # Anthropic doesn't have a models.list() endpoint like OpenAI
        # Return a static list of supported models
        return [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "description": "Most powerful Claude model for highly complex tasks",
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "description": "Balanced model for most tasks",
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "Fastest and most compact Claude model",
            },
            {
                "id": "claude-2.1",
                "name": "Claude 2.1",
                "description": "Previous generation Claude model",
            },
            {
                "id": "claude-2.0",
                "name": "Claude 2.0",
                "description": "Previous generation Claude model",
            },
            {
                "id": "claude-instant-1.2",
                "name": "Claude Instant 1.2",
                "description": "Older, faster Claude model",
            },
        ]

    def _convert_messages_format(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Convert messages from OpenAI format to Anthropic format.

        Anthropic expects messages in a specific format, and this function ensures
        compatibility with OpenAI-style message format that might be used elsewhere.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            Messages formatted for the Anthropic API
        """
        anthropic_messages: list[dict[str, str]] = []

        for msg in messages:
            role = msg.get("role", "").lower()

            # Map OpenAI roles to Anthropic roles
            if role == "system":
                # For Claude API, we need to handle system messages specially
                if not anthropic_messages:
                    # If this is the first message, it will be the system prompt
                    anthropic_messages.append(
                        {
                            "role": "user",
                            "content": msg["content"],
                        },
                    )
                    # Add an expected assistant reply to keep the alternating pattern
                    anthropic_messages.append(
                        {
                            "role": "assistant",
                            "content": "I'll help you with that.",
                        },
                    )
                else:
                    # For system messages after the first, inject as user messages
                    anthropic_messages.append(
                        {
                            "role": "user",
                            "content": f"[System message: {msg['content']}]",
                        },
                    )
                    # Add an expected assistant acknowledgment
                    anthropic_messages.append(
                        {
                            "role": "assistant",
                            "content": "I understand.",
                        },
                    )
            elif role == "user":
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": msg["content"],
                    },
                )
            elif role == "assistant":
                anthropic_messages.append(
                    {
                        "role": "assistant",
                        "content": msg["content"],
                    },
                )
            else:
                # For unsupported roles, add as user message with role prefix
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": f"[{role}: {msg['content']}]",
                    },
                )

        # Ensure the last message is from user, as required by Anthropic's API
        if anthropic_messages and anthropic_messages[-1]["role"] == "assistant":
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": "Please continue.",
                },
            )

        return anthropic_messages
