"""OpenRouter provider implementation."""

import json
from collections.abc import AsyncIterator
from typing import Any, Optional, Union

import httpx

from .base import (
    LLMProvider,
    LLMProviderError,
    MessageConfig,
)


class OpenRouterStreamResponse:
    """Async stream response for OpenRouter."""

    def __init__(self, stream_context: httpx.Response, timeout: float = 60.0) -> None:
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
                        if (
                            "choices" in data
                            and data["choices"]
                            and "delta" in data["choices"][0]
                        ):
                            delta = data["choices"][0]["delta"]
                            if delta.get("content"):
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise LLMProviderError(f"OpenRouter streaming API error: {e!s}") from e


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider implementation for accessing multiple LLM providers."""

    def __init__(self, api_key: str, base_url: Optional[str] = None) -> None:
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key
            base_url: Optional custom base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url or "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://syft_agent",  # Required by OpenRouter
            "X-Title": "Syft Agent",  # Optional title for request tracking
        }

    async def send_message(
        self,
        config: MessageConfig,
    ) -> dict[str, Any]:
        """Send a message to OpenRouter and get a response.

        Args:
            config: MessageConfig object with all parameters for the API call

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderError: If there's an error communicating with OpenRouter
        """
        try:
            payload = {
                "model": config.model,
                "messages": config.messages,
                "temperature": config.temperature,
                "stop": config.stop_sequences,
            }

            if config.max_tokens is not None:
                payload["max_tokens"] = config.max_tokens

            if config.top_p is not None:
                payload["top_p"] = config.top_p

            # Add any additional parameters
            payload.update(config.kwargs)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()

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
                    "usage": data.get("usage", {}),
                }
        except Exception as e:
            raise LLMProviderError(f"OpenRouter API error: {e!s}") from e

    async def _process_streaming_response(
        self,
        response_lines: AsyncIterator[str],
    ) -> AsyncIterator[str]:
        """Process streaming response lines from OpenRouter API.

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
                if (
                    "choices" in data
                    and data["choices"]
                    and "delta" in data["choices"][0]
                ):
                    delta = data["choices"][0]["delta"]
                    if delta.get("content"):
                        yield delta["content"]
            except json.JSONDecodeError:
                continue

    async def send_streaming_message(
        self,
        config: MessageConfig,
    ) -> AsyncIterator[str]:
        """Send a message to OpenRouter and get a streaming response.

        Args:
            config: MessageConfig object with all parameters for the API call

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            LLMProviderError: If there's an error communicating with OpenRouter
        """
        try:
            payload = {
                "model": config.model,
                "messages": config.messages,
                "temperature": config.temperature,
                "stream": True,
                "stop": config.stop_sequences,
            }

            if config.max_tokens is not None:
                payload["max_tokens"] = config.max_tokens

            if config.top_p is not None:
                payload["top_p"] = config.top_p

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
                    timeout=60.0,
                ) as response,
            ):
                response.raise_for_status()
                async for chunk in self._process_streaming_response(
                    response.aiter_lines(),
                ):
                    yield chunk
        except Exception as e:
            raise LLMProviderError(f"OpenRouter streaming API error: {e!s}") from e

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available models from OpenRouter.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderError: If there's an error communicating with OpenRouter
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
                        "name": model.get("name"),
                        "description": model.get("description"),
                        "context_length": model.get("context_length"),
                        "provider": model.get("provider", {}).get("name"),
                    }
                    for model in data.get("data", [])
                ]
        except Exception as e:
            raise LLMProviderError(f"Error fetching OpenRouter models: {e!s}") from e
