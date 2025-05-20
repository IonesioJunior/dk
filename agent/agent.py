"""Agent class that loads LLM configuration and initializes the appropriate provider."""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
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

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the agent with configuration from file.

        Args:
            config_path: Path to configuration file. Defaults to
                model_config.json in app directory
        """
        if config_path is None:
            app_dir = Path(__file__).resolve().parent.parent
            config_path = app_dir / "model_config.json"

        logger.info(f"Initializing agent with config path: {config_path}")

        self.config_path = config_path
        self.config = self._load_config()

        # Store configuration structure as attributes
        self.provider_name = self.config.get("provider")
        self.model = self.config.get("model")
        self.parameters = self.config.get("parameters", {})
        self.api_key = self.config.get("api_key")
        self.base_url = self.config.get("base_url")

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

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from JSON file.

        Returns:
            Dictionary containing configuration data

        Raises:
            json.JSONDecodeError: If configuration file is invalid JSON
        """
        config_path = Path(self.config_path)
        if not config_path.exists():
            # Create default configuration
            default_config = {
                "provider": "ollama",
                "model": "gemma3:4b",
                "parameters": {
                    "temperature": 0.6,
                },
            }

            # Create the directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write default configuration to file
            with config_path.open("w") as f:
                json.dump(default_config, f, indent=2)

            return default_config

        with config_path.open() as f:
            config = json.load(f)

        # Validate required fields
        if "provider" not in config:
            raise ValueError("Configuration must include 'provider' field")

        return config

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
        return self.config.copy()

    def get_config(self) -> dict[str, Any]:
        """Get configuration information with current config and available providers.

        Returns:
            Dictionary with current configuration and providers information
        """
        # Build current configuration
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
        }

    def update_config(self, new_config: dict[str, Any]) -> dict[str, Any]:
        """Update the agent configuration with new settings.

        This method updates the configuration, reinitializes the provider,
        and saves the new configuration to the file.

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
            logger.debug(f"Config path: {self.config_path}")

            # Validate required fields
            if "provider" not in new_config:
                raise ValueError("Configuration must include 'provider' field")
            if "model" not in new_config:
                raise ValueError("Configuration must include 'model' field")

            # Store old configuration in case of failure
            old_config = self.config.copy()
            old_provider = self.provider

            # Update internal configuration
            self.config = new_config.copy()

            # If API key is not provided in new config but we had one before, keep it
            if "api_key" not in self.config and self.api_key:
                self.config["api_key"] = self.api_key

            # Update attributes
            self.provider_name = self.config.get("provider")
            self.model = self.config.get("model")
            self.parameters = self.config.get("parameters", {})
            self.api_key = self.config.get("api_key")
            self.base_url = self.config.get("base_url")

            logger.info(
                f"Updated attributes - provider: {self.provider_name}, "
                f"model: {self.model}",
            )

            try:
                # Re-initialize the provider with new configuration
                self.provider = self._initialize_provider()

                # Save configuration to file
                self._save_config()

                logger.info(f"Configuration saved to {self.config_path}")

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
                self.config = old_config
                self.provider = old_provider
                self.provider_name = old_config.get("provider")
                self.model = old_config.get("model")
                self.parameters = old_config.get("parameters", {})
                self.api_key = old_config.get("api_key")
                self.base_url = old_config.get("base_url")
                raise provider_error

        except Exception as e:
            logger.error(f"Error updating config: {e!s}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "config": self.get_config(),
            }

    def _save_config(self) -> None:
        """Save the current configuration to the config file.

        Raises:
            Exception: If there's an error writing the file
        """
        try:
            # Prepare configuration for saving
            config_to_save = {
                "provider": self.provider_name,
                "model": self.model,
                "parameters": self.parameters,
            }

            # Add optional fields if they exist
            if self.api_key:
                config_to_save["api_key"] = self.api_key
            if self.base_url:
                config_to_save["base_url"] = self.base_url

            logger.debug(f"Saving configuration: {config_to_save}")
            logger.debug(f"To path: {self.config_path}")

            # Ensure directory exists
            config_path = Path(self.config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file is writable
            if config_path.exists() and not config_path.is_file():
                raise Exception(f"Config path {config_path} is not a file")

            # Write configuration to file
            with config_path.open("w") as f:
                json.dump(config_to_save, f, indent=2)
                f.flush()  # Ensure data is written to disk

            logger.info(
                f"Configuration file written successfully to {self.config_path}",
            )

            # Verify the file was written
            with config_path.open() as f:
                saved_content = json.load(f)
                logger.debug(f"Verified saved content: {saved_content}")

        except Exception as e:
            logger.error(f"Error in _save_config: {e!s}", exc_info=True)
            raise Exception(f"Failed to save configuration: {e!s}") from e

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
        from datetime import datetime

        if conversation_id not in self.conversations:
            raise KeyError(f"Conversation {conversation_id} not found")

        self.conversations[conversation_id].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
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
