from __future__ import annotations

from typing import Any

from syft_core import Client


class SyftClient:
    """Singleton class for managing the Syft client instance.

    This class ensures only one SyftClient instance exists throughout the application.
    """

    _instance: SyftClient | None = None
    _client: Client | None = None

    def __new__(cls) -> SyftClient:
        """Ensure only one instance of SyftClient is created."""
        if cls._instance is None:
            instance = super().__new__(cls)
            cls._instance = instance
            # Initialize client to None using protected method
            instance._set_client_none()
        return cls._instance

    def _set_client_none(self) -> None:
        """Initialize the client attribute to None."""
        self._client = None

    @property
    def client(self) -> Client:
        """Return the Syft client instance, creating it if it doesn't exist."""
        if self._client is None:
            self.initialize()
        assert self._client is not None  # for mypy
        return self._client

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the Syft client with the provided configuration.

        Args:
            config: Optional configuration dictionary for client initialization.
                   If None, default settings will be used.
        """
        if self._client is None:
            # Use default settings if no config is provided
            if config is None:
                config = {}

            self._client = Client.load()
            # Extract configuration values or use defaults
            # email = config.get("email", "user@example.com")
            # data_dir = config.get("data_dir", Path.home() / "SyftBox")
            # server_url = config.get("server_url", "https://syftbox.openmined.org")
            # client_url = config.get("client_url", "http://localhost:8080")
            # config.get("name", "SyftAgentClient")

            # Create the client config
            # client_config = SyftClientConfig(
            #     email=email,
            #     data_dir=data_dir,
            #     server_url=server_url,
            #     client_url=client_url,
            #     path=data_dir,  # Required field, using data_dir as the path
            # )

            # Create the client
            # self._client = Client(client_config)

    def reset(self) -> None:
        """Reset the client instance, forcing reinitialization on next use."""
        self._client = None


# Provide a singleton instance
syft_client = SyftClient()
