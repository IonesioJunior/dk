"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import (
    Any,
    Generic,
    Optional,
    Protocol,
    TypeVar,
    Union,
)


class LLMProviderError(Exception):
    """Exception raised for LLM provider errors."""


# Type for stream response
StreamT = TypeVar("StreamT", bound="AsyncStreamResponse")

# Generic type for stream responses
T = TypeVar("T")


class StreamResponseType(Generic[T]):
    """Generic type for stream responses."""


class AsyncStreamResponse(Protocol):
    """Protocol for async stream responses from LLM providers."""

    async def __aiter__(self) -> AsyncIterator[Union[str, dict[str, Any]]]:
        """Async iterator for the stream response."""
        ...


class LLMProvider(ABC):
    """Abstract base class defining the interface for LLM providers."""

    @abstractmethod
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
        """Send a message to the LLM provider and get a response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderError: If there's an error communicating with the provider
        """

    @abstractmethod
    def send_streaming_message(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Send a message to the LLM provider and get a streaming response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional provider-specific parameters

        Returns:
            Async iterator that yields chunks of the response as strings

        Raises:
            LLMProviderError: If there's an error communicating with the provider
        """

    @abstractmethod
    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available models from the provider.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderError: If there's an error communicating with the provider
        """
