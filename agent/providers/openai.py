"""OpenAI provider implementation using direct HTTP requests."""

import json
from collections.abc import AsyncIterator
from typing import Any, Optional, TypeVar, Union

import httpx

from .base import LLMProvider, LLMProviderError, MessageConfig

# Type for httpx stream context
StreamContextT = TypeVar("StreamContextT")


class OpenAIStreamResponse:
    """Async stream response for OpenAI."""

    def __init__(self, stream_context: Any, timeout: float = 120.0) -> None:
        """Initialize the stream response.

        Args:
            stream_context: Streaming context from httpx
            timeout: Timeout in seconds
        """
        self.stream_context = stream_context
        self.timeout = timeout

    async def __aiter__(self) -> AsyncIterator[Union[str, dict[str, Any]]]:
        """Async iterator for the stream response."""
        try:
            async with self.stream_context as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or line.strip() == "":
                        continue

                    processed_line = (
                        line[6:] if line.startswith("data: ") else line
                    )  # Handle data prefix

                    if processed_line == "[DONE]":
                        break

                    try:
                        data = json.loads(processed_line)
                        delta = data.get("choices", [{}])[0].get("delta", {})

                        if delta.get("content"):
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise LLMProviderError(f"OpenAI streaming API error: {e!s}") from e


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation using direct HTTP requests."""

    def __init__(self, api_key: str, base_url: Optional[str] = None) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            base_url: Optional custom base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def send_message(
        self,
        config: MessageConfig,
    ) -> dict[str, Any]:
        """Send a message to OpenAI and get a response.

        Args:
            config: MessageConfig object with all parameters for the API call

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderError: If there's an error communicating with OpenAI
        """
        try:
            # Prepare the request payload
            payload = {
                "model": config.model,
                "messages": config.messages,
                "temperature": config.temperature,
            }

            if config.max_tokens is not None:
                payload["max_tokens"] = config.max_tokens

            if config.top_p is not None:
                payload["top_p"] = config.top_p

            if config.stop_sequences:
                payload["stop"] = config.stop_sequences

            # Add any additional parameters
            payload.update(config.kwargs)

            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
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
                    "content": data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content"),
                    "role": data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("role", "assistant"),
                    "finish_reason": data.get("choices", [{}])[0].get("finish_reason"),
                    "usage": {
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get(
                            "completion_tokens",
                            0,
                        ),
                        "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                    },
                }
        except Exception as e:
            raise LLMProviderError(f"OpenAI API error: {e!s}") from e

    async def _process_streaming_response(
        self,
        response_lines: AsyncIterator[str],
    ) -> AsyncIterator[str]:
        """Process streaming response lines from OpenAI API.

        Args:
            response_lines: Async iterator of response lines from the API

        Returns:
            Async iterator yielding processed text chunks
        """
        async for line in response_lines:
            if not line or line.strip() == "":
                continue

            processed_line = (
                line[6:] if line.startswith("data: ") else line
            )  # Handle data prefix

            if processed_line == "[DONE]":
                break

            try:
                data = json.loads(processed_line)
                delta = data.get("choices", [{}])[0].get("delta", {})

                if delta.get("content"):
                    yield delta["content"]
            except json.JSONDecodeError:
                continue

    async def send_streaming_message(
        self,
        config: MessageConfig,
    ) -> AsyncIterator[str]:
        """Send a message to OpenAI and get a streaming response.

        Args:
            config: MessageConfig object with all parameters for the API call

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            LLMProviderError: If there's an error communicating with OpenAI
        """
        try:
            # Prepare the request payload
            payload = {
                "model": config.model,
                "messages": config.messages,
                "temperature": config.temperature,
                "stream": True,
            }

            if config.max_tokens is not None:
                payload["max_tokens"] = config.max_tokens

            if config.top_p is not None:
                payload["top_p"] = config.top_p

            if config.stop_sequences:
                payload["stop"] = config.stop_sequences

            # Add any additional parameters
            payload.update(config.kwargs)

            # Make the API request with streaming enabled
            async with (
                httpx.AsyncClient() as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
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
            raise LLMProviderError(f"OpenAI streaming API error: {e!s}") from e

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available OpenAI models.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderError: If there's an error communicating with OpenAI
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "id": model.get("id"),
                        "created": model.get("created"),
                        "owned_by": model.get("owned_by"),
                    }
                    for model in data.get("data", [])
                ]
        except Exception as e:
            raise LLMProviderError(f"Error fetching OpenAI models: {e!s}") from e
