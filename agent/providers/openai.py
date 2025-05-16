"""OpenAI provider implementation using direct HTTP requests."""

import json
from collections.abc import AsyncIterator
from typing import Any, Optional, TypeVar, Union

import httpx

from .base import LLMProvider, LLMProviderException

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

                    if line.startswith("data: "):
                        line = line[6:]  # Remove the "data: " prefix

                    if line == "[DONE]":
                        break

                    try:
                        data = json.loads(line)
                        delta = data.get("choices", [{}])[0].get("delta", {})

                        if delta.get("content"):
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise LLMProviderException(f"OpenAI streaming API error: {e!s}")


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
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a message to OpenAI and get a response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: OpenAI model to use (e.g., "gpt-4", "gpt-3.5-turbo")
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional OpenAI API parameters

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderException: If there's an error communicating with OpenAI
        """
        try:
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            if top_p is not None:
                payload["top_p"] = top_p

            if stop_sequences:
                payload["stop"] = stop_sequences

            # Add any additional parameters
            payload.update(kwargs)

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
            raise LLMProviderException(f"OpenAI API error: {e!s}")

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

            if line.startswith("data: "):
                line = line[6:]  # Remove the "data: " prefix

            if line == "[DONE]":
                break

            try:
                data = json.loads(line)
                delta = data.get("choices", [{}])[0].get("delta", {})

                if delta.get("content"):
                    yield delta["content"]
            except json.JSONDecodeError:
                continue

    async def send_streaming_message(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Send a message to OpenAI and get a streaming response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: OpenAI model to use (e.g., "gpt-4", "gpt-3.5-turbo")
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional OpenAI API parameters

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            LLMProviderException: If there's an error communicating with OpenAI
        """
        try:
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }

            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            if top_p is not None:
                payload["top_p"] = top_p

            if stop_sequences:
                payload["stop"] = stop_sequences

            # Add any additional parameters
            payload.update(kwargs)

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
            raise LLMProviderException(f"OpenAI streaming API error: {e!s}")

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available OpenAI models.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderException: If there's an error communicating with OpenAI
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
            raise LLMProviderException(f"Error fetching OpenAI models: {e!s}")
