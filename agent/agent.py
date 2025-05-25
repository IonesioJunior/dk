"""Agent class that loads LLM configuration and initializes the appropriate provider."""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Optional

from .providers.anthropic import AnthropicProvider
from .providers.base import LLMProvider, MessageConfig
from .providers.config import (
    AnthropicConfig,
    LLMProviderConfig,
    OllamaConfig,
    OpenAIConfig,
    OpenRouterConfig,
)
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
from .providers.openrouter import OpenRouterProvider

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MessageParams:
    """Parameters for LLM message sending to reduce function argument count."""

    messages: list[dict[str, str]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
    stream: bool = False
    extra_params: dict[str, Any] = None


class Agent:
    """Agent that manages LLM provider initialization and communication."""

    def __init__(self, settings: Optional[Any] = None) -> None:
        """Initialize the agent with configuration from settings.

        Args:
            settings: Settings instance. If not provided, will get from dependencies
        """
        if settings is None:
            from config.settings import get_settings

            settings = get_settings()

        logger.info("Initializing agent with settings")

        self.settings = settings

        # Check if llm_config is available
        if not settings.llm_config:
            logger.warning(
                "No model configuration available. Agent initialization skipped."
            )
            self.provider = None
            self.provider_name = None
            self.model = None
            self.parameters = {}
            self.api_key = None
            self.base_url = None
            self.conversations = {}
            return

        # Store configuration from settings
        model_config = settings.llm_config
        self.provider_name = model_config.provider
        self.model = model_config.model
        self.parameters = model_config.parameters or {}
        self.api_key = model_config.api_key
        self.base_url = model_config.base_url

        logger.info(
            f"Agent initialized with provider: {self.provider_name}, "
            f"model: {self.model}",
        )

        # Initialize provider after storing attributes
        self.provider = self._initialize_provider()

        if not self.model:
            raise ValueError("No model specified in configuration")

        # Initialize conversation history storage
        self.conversations = {}

    def reload_from_settings(self) -> None:
        """Reload configuration from settings."""
        from config.settings import reload_settings

        self.settings = reload_settings()

        if not self.settings.llm_config:
            logger.warning("No model configuration available after reload.")
            self.provider = None
            self.provider_name = None
            self.model = None
            self.parameters = {}
            self.api_key = None
            self.base_url = None
            return

        # Update configuration from settings
        model_config = self.settings.llm_config
        self.provider_name = model_config.provider
        self.model = model_config.model
        self.parameters = model_config.parameters or {}
        self.api_key = model_config.api_key
        self.base_url = model_config.base_url

        logger.info(
            f"Agent reloaded with provider: {self.provider_name}, "
            f"model: {self.model}",
        )

        # Re-initialize provider
        self.provider = self._initialize_provider()

    def _initialize_provider(self) -> LLMProvider:
        """Initialize the appropriate LLM provider based on configuration.

        Returns:
            Initialized LLMProvider instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        provider_name = self.provider_name.lower()

        if provider_name == "anthropic":
            if not self.api_key:
                raise ValueError(
                    "Anthropic provider requires 'api_key' in configuration",
                )
            return AnthropicProvider(
                api_key=self.api_key,
                base_url=self.base_url,
            )

        if provider_name == "openai":
            if not self.api_key:
                raise ValueError("OpenAI provider requires 'api_key' in configuration")
            return OpenAIProvider(
                api_key=self.api_key,
                base_url=self.base_url,
            )

        if provider_name == "ollama":
            return OllamaProvider(
                base_url=self.base_url or "http://localhost:11434",
            )

        if provider_name == "openrouter":
            if not self.api_key:
                raise ValueError(
                    "OpenRouter provider requires 'api_key' in configuration",
                )
            return OpenRouterProvider(
                api_key=self.api_key,
                base_url=self.base_url,
            )

        raise ValueError(f"Unsupported provider: {provider_name}")

    def _create_provider_config(
        self,
        params: MessageParams,
        **kwargs: Any,
    ) -> LLMProviderConfig:
        """Create a provider-specific config object.

        Args:
            params: MessageParams object containing all message parameters
            **kwargs: Additional provider-specific parameters not in MessageParams

        Returns:
            A provider-specific configuration object
        """
        provider_type = self.provider_name.lower()
        # Combine any additional kwargs with params.extra_params
        extra_params = params.extra_params or {}
        extra_params.update(kwargs)
        # Common config parameters
        config_params = {
            "messages": params.messages,
            "model": params.model,
            # Set default temperature if not provided
            "temperature": (
                params.temperature if params.temperature is not None else 0.7
            ),
            "max_tokens": params.max_tokens,
            "top_p": params.top_p,
            "stop_sequences": params.stop_sequences,
            "stream": params.stream,
            "extra_params": extra_params,
        }

        # Create a config object based on the provider type
        if provider_type == "openai":
            return OpenAIConfig(**config_params)
        if provider_type == "anthropic":
            return AnthropicConfig(**config_params)
        if provider_type == "ollama":
            return OllamaConfig(**config_params)
        if provider_type == "openrouter":
            return OpenRouterConfig(**config_params)
        # Use the generic config as fallback
        return LLMProviderConfig(**config_params)

    async def send_message_with_params(
        self,
        params: MessageParams,
    ) -> dict[str, Any]:
        """Send a message to the LLM with parameters object.

        Args:
            params: MessageParams object containing all parameters

        Returns:
            Dictionary containing the response data
        """
        # Check if provider is initialized
        if self.provider is None:
            raise ValueError(
                "Agent not properly configured. No LLM provider available."
            )

        # Get temperature from params or fall back to config value
        temp = (
            params.temperature
            if params.temperature is not None
            else self.parameters.get("temperature", 0.7)
        )
        message_config = MessageConfig(
            messages=params.messages,
            model=params.model or self.model,
            temperature=temp,
            max_tokens=params.max_tokens,
            top_p=params.top_p,
            stop_sequences=params.stop_sequences,
            kwargs=params.extra_params or {},
        )
        return await self.provider.send_message(message_config)

    async def send_message(  # noqa: PLR0913
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a message to the LLM and get a response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Optional model override. Uses config model if not specified
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
        model = model or self.model
        temperature = (
            temperature
            if temperature is not None
            else self.parameters.get("temperature", 0.7)
        )

        # Create MessageParams object to bundle all parameters
        params = MessageParams(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences,
            extra_params=kwargs,
        )

        # Use the wrapper method that takes MessageParams
        return await self.send_message_with_params(params)

    async def process_message(
        self,
        conversation_id: str,  # noqa: ARG002
        user_message: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Process a user message within a conversation context.

        Args:
            conversation_id: Unique identifier for the conversation
            user_message: The user's message to process
            conversation_history: Optional list of previous messages in the conversation

        Returns:
            The agent's response text
        """
        # Build the full message list
        messages = []

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        # Send to the LLM
        try:
            response = await self.send_message(messages)

            # Extract the response text
            # The response format may vary by provider, handle common formats
            if "content" in response:
                return response["content"]
            if "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            if "text" in response:
                return response["text"]
            logger.warning(f"Unexpected response format: {response}")
            return str(response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def send_streaming_message_with_params(
        self,
        params: MessageParams,
    ) -> AsyncIterator[str]:
        """Send a message to the LLM with parameters object.

        Uses the provider's streaming capability.

        Args:
            params: MessageParams object containing all parameters

        Returns:
            Async iterator that yields chunks of the response
        """
        # Check if provider is initialized
        if self.provider is None:
            raise ValueError(
                "Agent not properly configured. No LLM provider available."
            )

        # Ensure streaming is enabled
        params.stream = True
        # Get temperature from params or fall back to config value
        temp = (
            params.temperature
            if params.temperature is not None
            else self.parameters.get("temperature", 0.7)
        )
        message_config = MessageConfig(
            messages=params.messages,
            model=params.model or self.model,
            temperature=temp,
            max_tokens=params.max_tokens,
            top_p=params.top_p,
            stop_sequences=params.stop_sequences,
            kwargs=params.extra_params or {},
        )
        # Provider's send_streaming_message returns an async generator directly
        async for chunk in self.provider.send_streaming_message(message_config):
            yield chunk

    async def send_streaming_message(  # noqa: PLR0913
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Send a message to the LLM and get a streaming response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Optional model override. Uses config model if not specified
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            stop_sequences: List of sequences that will stop generation
            **kwargs: Additional provider-specific parameters

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            LLMProviderError: If there's an error communicating with the provider
        """
        model = model or self.model
        temperature = (
            temperature
            if temperature is not None
            else self.parameters.get("temperature", 0.7)
        )

        # Create MessageParams object to bundle all parameters
        params = MessageParams(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences,
            stream=True,  # Ensure streaming is enabled
            extra_params=kwargs,
        )

        # Use the wrapper method that takes MessageParams
        async for chunk in self.send_streaming_message_with_params(params):
            yield chunk

    async def get_available_models(self) -> list[dict[str, Any]]:
        """Get a list of available models from the provider.

        Returns:
            List of model information dictionaries

        Raises:
            LLMProviderError: If there's an error communicating with the provider
        """
        return await self.provider.get_available_models()

    def get_provider_name(self) -> str:
        """Get the name of the active provider.

        Returns:
            Provider name as string
        """
        return self.provider_name

    def get_model_name(self) -> str:
        """Get the name of the active model.

        Returns:
            Model name as string
        """
        return self.model

    def get_config_copy(self) -> dict[str, Any]:
        """Get a copy of the current configuration.

        Returns:
            Configuration dictionary copy
        """
        if not self.settings.llm_config:
            return {}

        return {
            "provider": self.provider_name,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "parameters": self.parameters.copy() if self.parameters else {},
        }

    def get_config(self) -> dict[str, Any]:
        """Get configuration information with current config and available providers.

        Returns:
            Dictionary with current configuration and providers information
        """
        # Build current configuration
        current_config = {}
        if self.provider_name:
            current_config = {
                "provider": self.provider_name,
                "model": self.model,
                "api_key": self.api_key if self.api_key else None,
                "base_url": self.base_url if self.base_url else None,
                "parameters": self.parameters.copy() if self.parameters else {},
            }
            # Remove None values for cleaner output
            current_config = {k: v for k, v in current_config.items() if v is not None}

        # Define available models for each provider
        providers = {
            "openai": [
                "gpt-4.1",
                "gpt-4.1-mini",
                "gpt-4o",
                "gpt-4o-mini",
            ],
            "anthropic": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
            ],
            "ollama": [
                "llama2",
                "llama2:70b",
                "mistral",
                "gemma3:4b",
            ],
            "openrouter": [
                "openai/gpt-4",
                "anthropic/claude-3-opus",
                "google/gemini-pro",
                "meta-llama/llama-3-70b-instruct",
            ],
        }

        return {
            "current_config": current_config,
            "providers": providers,
            "onboarding": (
                self.settings.onboarding if hasattr(self, "settings") else True
            ),
        }

    def update_config(self, new_config: dict[str, Any]) -> dict[str, Any]:
        """Update the agent configuration with new settings.

        This method updates the model configuration in settings,
        reinitializes the provider, and saves to config.json.

        Args:
            new_config: Dictionary containing new configuration settings
                       Expected fields: provider, model, api_key, base_url, parameters

        Returns:
            Dictionary with status and current configuration

        Raises:
            ValueError: If configuration is invalid
            Exception: If there's an error saving the configuration
        """
        try:
            logger.info(f"Updating config with: {new_config}")

            # Validate required fields
            if "provider" not in new_config:
                raise ValueError("Configuration must include 'provider' field")
            if "model" not in new_config:
                raise ValueError("Configuration must include 'model' field")

            # Store old configuration in case of failure
            old_provider_name = self.provider_name
            old_model = self.model
            old_parameters = self.parameters.copy() if self.parameters else {}
            old_api_key = self.api_key
            old_base_url = self.base_url
            old_provider = self.provider

            # Update attributes from new config
            self.provider_name = new_config.get("provider")
            self.model = new_config.get("model")
            self.parameters = new_config.get("parameters", {})
            self.api_key = new_config.get("api_key")
            self.base_url = new_config.get("base_url")

            # If API key is not provided in new config but we had one before, keep it
            if not self.api_key and old_api_key:
                self.api_key = old_api_key

            logger.info(
                f"Updated attributes - provider: {self.provider_name}, "
                f"model: {self.model}",
            )

            try:
                # Re-initialize the provider with new configuration
                self.provider = self._initialize_provider()

                # Update settings with new model config
                from config.settings import ModelConfig

                model_config = ModelConfig(
                    provider=self.provider_name,
                    model=self.model,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    parameters=self.parameters,
                )
                self.settings.llm_config = model_config
                self.settings.save()

                logger.info("Configuration saved to config.json")

                return {
                    "status": "success",
                    "message": "Configuration updated successfully",
                    "config": self.get_config(),
                }
            except Exception as provider_error:
                # Restore old configuration on provider initialization failure
                logger.error(
                    f"Failed to initialize provider, restoring old config: "
                    f"{provider_error!s}",
                )
                self.provider_name = old_provider_name
                self.model = old_model
                self.parameters = old_parameters
                self.api_key = old_api_key
                self.base_url = old_base_url
                self.provider = old_provider
                raise provider_error

        except Exception as e:
            logger.error(f"Error updating config: {e!s}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "config": self.get_config(),
            }

    def is_configured(self) -> bool:
        """Check if the agent is properly configured.

        Returns:
            True if agent has a valid model configuration, False otherwise
        """
        return self.provider is not None and self.model is not None

    def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        """Create a new conversation and return its ID.

        Args:
            conversation_id: Optional ID for the conversation. If not provided,
                one will be generated.

        Returns:
            The conversation ID
        """
        import uuid

        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        self.conversations[conversation_id] = []
        logger.info(f"Created new conversation: {conversation_id}")
        return conversation_id

    def add_message_to_conversation(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """Add a message to a conversation's history.

        Args:
            conversation_id: The conversation ID
            role: The role of the message sender ('user' or 'assistant')
            content: The message content

        Raises:
            KeyError: If the conversation doesn't exist
        """
        from datetime import datetime, timezone

        if conversation_id not in self.conversations:
            raise KeyError(f"Conversation {conversation_id} not found")

        self.conversations[conversation_id].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.debug(f"Added {role} message to conversation {conversation_id}")

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        """Get the message history for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            List of message dictionaries

        Raises:
            KeyError: If the conversation doesn't exist
        """
        if conversation_id not in self.conversations:
            raise KeyError(f"Conversation {conversation_id} not found")

        return self.conversations[conversation_id].copy()

    async def send_message_with_history(
        self,
        conversation_id: str,
        message: str,
        include_history: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a message with conversation history and get a response.

        Args:
            conversation_id: The conversation ID
            message: The user's message
            include_history: Whether to include conversation history
            **kwargs: Additional parameters for send_message

        Returns:
            Dictionary containing the response data

        Raises:
            KeyError: If the conversation doesn't exist
        """
        if conversation_id not in self.conversations:
            raise KeyError(f"Conversation {conversation_id} not found")

        # Add user message to history
        self.add_message_to_conversation(conversation_id, "user", message)

        # Get messages to send
        if include_history:
            messages = self.get_conversation_history(conversation_id)
        else:
            messages = [{"role": "user", "content": message}]

        # Send to LLM
        response = await self.send_message(messages, **kwargs)

        # Add assistant response to history
        assistant_content = response.get("content", "")
        if assistant_content:
            self.add_message_to_conversation(
                conversation_id,
                "assistant",
                assistant_content,
            )

        return response

    async def send_peer_query_streaming(
        self,
        message: str,
        peers: list[str],
        conversation_id: Optional[str] = None,  # noqa: ARG002
    ) -> AsyncIterator[str]:
        """Handle a query with peer mentions.

        Logs and returns mock response for now."""
        logger.info(f"Peer query received - Prompt: {message}, Peers: {peers}")

        # Log the individual message creation for each peer

        for peer in peers:
            logger.info(f"Creating forward message to {peer} with content: {message}")

        # Mock streaming response for now
        mock_response = (
            f"I've forwarded your message to: {', '.join(peers)}. "
            f"This is a mock response for the peer query functionality."
        )

        # Simulate streaming by yielding chunks
        words = mock_response.split()
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            yield chunk

    async def send_streaming_message_with_history(
        self,
        conversation_id: str,
        message: str,
        include_history: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Send a message with conversation history and get a streaming response.

        Args:
            conversation_id: The conversation ID
            message: The user's message
            include_history: Whether to include conversation history
            **kwargs: Additional parameters for send_streaming_message

        Returns:
            Async iterator that yields chunks of the response

        Raises:
            KeyError: If the conversation doesn't exist
        """
        if conversation_id not in self.conversations:
            raise KeyError(f"Conversation {conversation_id} not found")

        # Add user message to history
        self.add_message_to_conversation(conversation_id, "user", message)

        # Get messages to send
        if include_history:
            messages = self.get_conversation_history(conversation_id)
        else:
            messages = [{"role": "user", "content": message}]

        # Stream response and collect it
        assistant_content = ""
        async for chunk in self.send_streaming_message(messages, **kwargs):
            assistant_content += chunk
            yield chunk

        # Add complete assistant response to history
        if assistant_content:
            self.add_message_to_conversation(
                conversation_id,
                "assistant",
                assistant_content,
            )
