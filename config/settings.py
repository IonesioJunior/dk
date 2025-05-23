import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    """Model configuration."""

    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Settings(BaseModel):
    # Application settings
    app_name: str = "syft_agent"
    host: str = "127.0.0.1"  # Bind to localhost only for security
    port: int = 8082
    log_level: str = "INFO"

    # Onboarding state
    onboarding: bool = True

    # Syftbox settings
    syftbox_username: Optional[str] = None
    syftbox_email: Optional[str] = None

    # WebSocket settings
    websocket_server_url: str = "https://distributedknowledge.org"
    websocket_retry_attempts: int = 3
    websocket_retry_delay: int = 5

    # Key management
    private_key_filename: str = "websocket_private.pem"
    public_key_filename: str = "websocket_public.pem"

    # Threading settings
    scheduler_startup_delay: int = 0
    websocket_startup_delay: int = 5

    # Model configuration
    llm_config: Optional[ModelConfig] = None

    @property
    def key_directory(self) -> Path:
        """Get the key directory relative to the app root."""
        app_root = Path(__file__).resolve().parent.parent
        return app_root / "cache" / "keys"

    @property
    def config_path(self) -> Path:
        """Get the config.json path."""
        app_root = Path(__file__).resolve().parent.parent
        return app_root / "config.json"

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from config.json or create default."""
        app_root = Path(__file__).resolve().parent.parent
        config_path = app_root / "config.json"

        if config_path.exists():
            try:
                with config_path.open() as f:
                    data = json.load(f)
                logger.info(
                    f"Loaded config data: onboarding={data.get('onboarding')}, "
                    f"username={data.get('syftbox_username')}"
                )
                # Convert llm_config dict to ModelConfig object if present
                if "llm_config" in data and data["llm_config"]:
                    data["llm_config"] = ModelConfig(**data["llm_config"])
                # Handle legacy model_config field
                elif data.get("model_config"):
                    data["llm_config"] = ModelConfig(**data.pop("model_config"))
                return cls(**data)
            except Exception as e:
                logger.error(f"Error loading config.json: {e}")
                # Return default settings if error
                return cls._create_default()
        else:
            # Create default config if doesn't exist
            settings = cls._create_default()
            settings.save()
            return settings

    @classmethod
    def _create_default(cls) -> "Settings":
        """Create default settings for first-time setup."""
        return cls(
            app_name="syft_agent",
            host="127.0.0.1",  # Bind to localhost only for security
            port=8082,
            log_level="INFO",
            onboarding=True,
            syftbox_username=None,
            websocket_server_url="https://distributedknowledge.org",
            websocket_retry_attempts=3,
            websocket_retry_delay=5,
            private_key_filename="websocket_private.pem",
            public_key_filename="websocket_public.pem",
            scheduler_startup_delay=0,
            websocket_startup_delay=5,
            llm_config=None,
        )

    def save(self) -> None:
        """Save settings to config.json."""
        data = self.model_dump(exclude_none=False)
        # model_dump already converts ModelConfig to dict, no need for extra conversion

        with self.config_path.open("w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Settings saved to {self.config_path}")

    def complete_onboarding(self, username: str, llm_config: ModelConfig) -> None:
        """Complete onboarding by setting user info and model config."""
        self.onboarding = False
        self.syftbox_username = username
        self.llm_config = llm_config
        self.save()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from config.json."""
    global _settings
    _settings = Settings.load()
    return _settings
