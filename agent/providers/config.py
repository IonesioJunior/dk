"""Configuration classes for LLM providers."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMProviderConfig:
    """Configuration for LLM provider API calls.

    This class centralizes all common parameters used across different LLM providers
    to address the "too many parameters" (PLR0913) issue in the provider interface.

    Attributes:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: Model identifier to use
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        top_p: Nucleus sampling parameter
        stop_sequences: List of sequences that will stop generation
        stream: Whether to stream the response
        timeout: Request timeout in seconds
        extra_params: Additional provider-specific parameters
    """

    messages: list[dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
    stream: bool = False
    timeout: float = 60.0
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to a dictionary for API requests.

        Returns:
            Dictionary containing all parameters, suitable for API requests
        """
        result = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            "stream": self.stream,
        }

        # Include optional parameters only if they are set
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens

        if self.top_p is not None:
            result["top_p"] = self.top_p

        if self.stop_sequences:
            result["stop"] = self.stop_sequences

        # Include any extra provider-specific parameters
        result.update(self.extra_params)

        return result


@dataclass
class OpenAIConfig(LLMProviderConfig):
    """OpenAI-specific configuration.

    Extends the base configuration with parameters specific to OpenAI API.

    Attributes:
        frequency_penalty: Penalty for token frequency (OpenAI specific)
        presence_penalty: Penalty for token presence (OpenAI specific)
        logit_bias: Modify likelihood of specific tokens appearing (OpenAI specific)
        user: End-user identifier for OpenAI usage monitoring
    """

    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    logit_bias: Optional[dict[str, float]] = None
    user: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to an OpenAI-specific dictionary.

        Returns:
            Dictionary containing all parameters for OpenAI API
        """
        result = super().to_dict()

        # Add OpenAI-specific parameters
        if self.frequency_penalty is not None:
            result["frequency_penalty"] = self.frequency_penalty

        if self.presence_penalty is not None:
            result["presence_penalty"] = self.presence_penalty

        if self.logit_bias:
            result["logit_bias"] = self.logit_bias

        if self.user:
            result["user"] = self.user

        return result


@dataclass
class AnthropicConfig(LLMProviderConfig):
    """Anthropic-specific configuration.

    Extends the base configuration with parameters specific to Anthropic API.

    Attributes:
        system: System prompt for Claude models
        metadata: Additional metadata for Anthropic API
    """

    system: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to an Anthropic-specific dictionary.

        Returns:
            Dictionary containing all parameters for Anthropic API
        """
        result = super().to_dict()

        # Add Anthropic-specific parameters
        if self.system:
            result["system"] = self.system

        if self.metadata:
            result["metadata"] = self.metadata

        # Anthropic uses "stop_sequences" instead of "stop"
        if "stop" in result and self.stop_sequences:
            result["stop_sequences"] = result.pop("stop")

        return result


@dataclass
class OllamaConfig(LLMProviderConfig):
    """Ollama-specific configuration.

    Extends the base configuration with parameters specific to Ollama API.

    Attributes:
        repeat_penalty: Penalty for repeated tokens (Ollama specific)
        repeat_last_n: Number of tokens to look back for repetitions
        seed: Random seed for deterministic sampling
        num_predict: Number of tokens to predict (similar to max_tokens)
        mirostat: Enable Mirostat sampling algorithm (0, 1, or 2)
        mirostat_tau: Mirostat target entropy
        mirostat_eta: Mirostat learning rate
    """

    repeat_penalty: Optional[float] = None
    repeat_last_n: Optional[int] = None
    seed: Optional[int] = None
    num_predict: Optional[int] = None
    mirostat: Optional[int] = None
    mirostat_tau: Optional[float] = None
    mirostat_eta: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to an Ollama-specific dictionary.

        Returns:
            Dictionary containing all parameters for Ollama API
        """
        result = super().to_dict()

        # Ollama uses "options" object for many parameters
        options = {}

        if self.repeat_penalty is not None:
            options["repeat_penalty"] = self.repeat_penalty

        if self.repeat_last_n is not None:
            options["repeat_last_n"] = self.repeat_last_n

        if self.seed is not None:
            options["seed"] = self.seed

        if self.num_predict is not None:
            options["num_predict"] = self.num_predict

        if self.mirostat is not None:
            options["mirostat"] = self.mirostat

        if self.mirostat_tau is not None:
            options["mirostat_tau"] = self.mirostat_tau

        if self.mirostat_eta is not None:
            options["mirostat_eta"] = self.mirostat_eta

        # Add options if any are set
        if options:
            result["options"] = options

        return result


@dataclass
class OpenRouterConfig(LLMProviderConfig):
    """OpenRouter-specific configuration.

    Extends the base configuration with parameters specific to OpenRouter API.

    Attributes:
        transforms: Transformation options for OpenRouter
        route: Routing preferences for OpenRouter
        prompt_format: Format for parsing prompt (e.g., "openai", "anthropic")
    """

    transforms: Optional[list[str]] = None
    route: Optional[str] = None
    prompt_format: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to an OpenRouter-specific dictionary.

        Returns:
            Dictionary containing all parameters for OpenRouter API
        """
        result = super().to_dict()

        # Add OpenRouter-specific parameters
        if self.transforms:
            result["transforms"] = self.transforms

        if self.route:
            result["route"] = self.route

        if self.prompt_format:
            result["prompt_format"] = self.prompt_format

        return result
