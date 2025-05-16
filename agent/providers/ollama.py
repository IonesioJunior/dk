"""Ollama provider implementation for local LLMs."""

import json
from collections.abc import AsyncIterator
from typing import Any, Optional, Union, cast

import httpx

from .base import (
    LLMProvider,
    LLMProviderException,
)


class OllamaStreamResponse:
    """Async stream response for Ollama."""

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

                    try:
                        data = json.loads(line)
                        if data.get("response"):
                            yield data["response"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise LLMProviderException(f"Ollama streaming API error: {e!s}")


class OllamaProvider(LLMProvider):
    """Ollama API provider implementation for local LLMs."""

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        """Initialize Ollama provider.

        Args:
            base_url: Base URL for the Ollama API, defaults to localhost
        """
        self.base_url = base_url
        self.headers = {
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
        """Send a message to Ollama and get a response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Ollama model name (e.g., "llama2", "mistral")
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional Ollama-specific parameters

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderException: If there's an error communicating with Ollama
        """
        try:
            # Convert OpenAI-style messages to Ollama format
            prompt = self._convert_messages_to_prompt(messages)

            # Prepare request payload
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            # Add options to payload
            options = payload["options"]
            if max_tokens is not None:
                options["num_predict"] = max_tokens

            if top_p is not None:
                options["top_p"] = top_p

            if stop_sequences:
                options["stop"] = stop_sequences

            # Add any additional Ollama-specific options
            for key, value in kwargs.items():
                if key != "options":
                    options[key] = value
                else:
                    # Merge options dictionaries
                    opt_dict = cast("dict[str, Any]", value)
                    for opt_key, opt_value in opt_dict.items():
                        options[opt_key] = opt_value

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()

                return {
                    "id": f"ollama-{model}-{data.get('created_at', '')}",
                    "model": model,
                    "content": data.get("response", ""),
                    "role": "assistant",
                    "finish_reason": None,
                    "usage": {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0)
                        + data.get("eval_count", 0),
                    },
                }
        except Exception as e:
            raise LLMProviderException(f"Ollama API error: {e!s}")

    async def _process_streaming_response(
        self,
        response_lines: AsyncIterator[str],
    ) -> AsyncIterator[str]:
        """Process streaming response lines from Ollama API.

        Args:
            response_lines: Async iterator of response lines from the API

        Returns:
            Async iterator yielding processed text chunks
        """
        async for line in response_lines:
            if not line or line.strip() == "":
                continue

            try:
                data = json.loads(line)
                if data.get("response"):
                    yield data["response"]
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
        """Send a message to Ollama and get a streaming response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Ollama model name (e.g., "llama2", "mistral")
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional Ollama-specific parameters

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            LLMProviderException: If there's an error communicating with Ollama
        """
        try:
            # Convert OpenAI-style messages to Ollama format
            prompt = self._convert_messages_to_prompt(messages)

            # Prepare request payload
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                },
            }

            # Add options to payload
            options = payload["options"]
            if max_tokens is not None:
                options["num_predict"] = max_tokens

            if top_p is not None:
                options["top_p"] = top_p

            if stop_sequences:
                options["stop"] = stop_sequences

            # Add any additional Ollama-specific options
            for key, value in kwargs.items():
                if key != "options":
                    options[key] = value
                else:
                    # Merge options dictionaries
                    opt_dict = cast("dict[str, Any]", value)
                    for opt_key, opt_value in opt_dict.items():
                        options[opt_key] = opt_value

            # Make the API request with streaming enabled
            async with (
                httpx.AsyncClient() as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
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
            raise LLMProviderException(f"Ollama streaming API error: {e!s}")

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available Ollama models.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderException: If there's an error communicating with Ollama
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "id": model.get("name"),
                        "name": model.get("name"),
                        "size": model.get("size"),
                        "modified_at": model.get("modified_at"),
                    }
                    for model in data.get("models", [])
                ]
        except Exception as e:
            raise LLMProviderException(f"Error fetching Ollama models: {e!s}")

    def _convert_messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """Convert OpenAI-style messages to an Ollama prompt string.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            A formatted prompt string for Ollama
        """
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"<|system|>\n{content}\n</|system|>")
            elif role == "user":
                prompt_parts.append(f"<|user|>\n{content}\n</|user|>")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}\n</|assistant|>")
            else:
                # For unsupported roles, add as user message with role prefix
                prompt_parts.append(f"<|user|>\n[{role}]: {content}\n</|user|>")

        # Add the final assistant prefix to prompt for generation
        prompt_parts.append("<|assistant|>")

        return "\n".join(prompt_parts)
