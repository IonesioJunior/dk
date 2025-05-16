from functools import lru_cache
from typing import Optional

from agent.agent import Agent
from config.settings import Settings
from services.websocket_service import WebSocketService
from services.scheduler_service import SchedulerService
from syftbox.client import syft_client

# Singleton instances
_agent: Optional[Agent] = None
_websocket_service: Optional[WebSocketService] = None
_scheduler_service: Optional[SchedulerService] = None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_agent() -> Agent:
    """Get singleton agent instance."""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def get_syft_client():
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


def get_websocket_client():
    """Get the WebSocket client instance."""
    websocket_service = get_websocket_service()
    if websocket_service and websocket_service.client:
        return websocket_service.client
    return None
