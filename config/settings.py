from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    app_name: str = "syft_agent"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Syftbox settings
    syftbox_user_id: str = "syftbox_agent"
    syftbox_username: str = "Syftbox Agent"
    syftbox_email: Optional[str] = None

    # WebSocket settings
    websocket_server_url: str = "https://distributedknowledge.org"
    websocket_retry_attempts: int = 3
    websocket_retry_delay: int = 5

    # Key management
    key_directory: Path = Path.home() / ".syftbox" / "keys"
    private_key_filename: str = "websocket_private.pem"
    public_key_filename: str = "websocket_public.pem"

    # Threading settings
    scheduler_startup_delay: int = 0
    websocket_startup_delay: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
