from functools import lru_cache
from typing import Optional, TYPE_CHECKING, Any

from agent.agent import Agent
from config.settings import Settings
from services.scheduler_service import SchedulerService
from services.websocket_service import WebSocketService
from syftbox.client import SyftClient, syft_client
from client.client import Client

# Type checking imports - only used for type hints
if TYPE_CHECKING:
    from services.api_config_service import APIConfigService

# Singleton instances
_agent: Optional[Agent] = None
_websocket_service: Optional[WebSocketService] = None
_scheduler_service: Optional[SchedulerService] = None
_api_config_service: Optional[Any] = None  # Use Any at runtime, APIConfigService during type checking


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_agent() -> Agent:
    """Get singleton agent instance."""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def get_syft_client() -> SyftClient:
    """Get singleton syft client instance."""
    return syft_client


def get_websocket_service() -> WebSocketService:
    """Get singleton WebSocket service instance."""
    global _websocket_service
    if _websocket_service is None:
        settings = get_settings()
        agent = get_agent()
        _websocket_service = WebSocketService(settings, agent)
    return _websocket_service


def get_scheduler_service() -> SchedulerService:
    """Get singleton scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        settings = get_settings()
        _scheduler_service = SchedulerService(settings)
    return _scheduler_service


def get_websocket_client() -> Optional[Client]:
    """Get the WebSocket client instance."""
    websocket_service = get_websocket_service()
    if websocket_service and websocket_service.client:
        return websocket_service.client
    return None


def get_api_config_service():
    """Get singleton API config service instance."""
    global _api_config_service
    if _api_config_service is None:
        from services.api_config_service import APIConfigService
        
        _api_config_service = APIConfigService()
    return _api_config_service