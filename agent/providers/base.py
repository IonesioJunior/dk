"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import (
    Any,
    Generic,
    Optional,
    Protocol,
    TypeVar,
    Union,
)

# No imports needed from .config with MessageConfig implemented here


class LLMProviderError(Exception):
    """Exception raised for LLM provider errors."""


@dataclass
class MessageConfig:
    """Configuration for sending messages to LLM providers."""

    messages: list[dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
    kwargs: dict[str, Any] = field(default_factory=dict)


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
        config: MessageConfig,
    ) -> dict[str, Any]:
        """Send a message to the LLM provider and get a response.

        Args:
            config: MessageConfig object with all parameters for the API call

        Returns:
            Dictionary containing the response data

        Raises:
            LLMProviderError: If there's an error communicating with the provider
        """

    @abstractmethod
    async def send_streaming_message(
        self,
        config: MessageConfig,
    ) -> AsyncIterator[str]:
        """Send a message to the LLM provider and get a streaming response.

        Args:
            config: MessageConfig object with all parameters for the API call

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
