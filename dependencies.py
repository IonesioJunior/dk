"""Dependency injection for the application.

This module provides factory functions for singleton service instances.
It uses the ServiceLocator pattern to avoid global variables.
"""

from typing import Any, Optional

from agent.agent import Agent
from client.client import Client
from config.settings import Settings
from service_locator import service_locator
from services.scheduler_service import SchedulerService
from services.websocket_service import WebSocketService
from syftbox.client import SyftClient, syft_client


def get_settings() -> Settings:
    """Get cached settings instance."""
    return service_locator.get(
        "settings",
        lambda: Settings()
    )


def get_agent() -> Agent:
    """Get singleton agent instance."""
    return service_locator.get("agent", lambda: Agent())


def get_syft_client() -> SyftClient:
    """Get singleton syft client instance."""
    return syft_client


def get_websocket_service() -> WebSocketService:
    """Get singleton WebSocket service instance."""
    def create_websocket_service() -> WebSocketService:
        settings = get_settings()
        agent = get_agent()
        return WebSocketService(settings, agent)

    return service_locator.get("websocket_service", create_websocket_service)


def get_scheduler_service() -> SchedulerService:
    """Get singleton scheduler service instance."""
    def create_scheduler_service() -> SchedulerService:
        settings = get_settings()
        return SchedulerService(settings)

    return service_locator.get("scheduler_service", create_scheduler_service)


def get_websocket_client() -> Optional[Client]:
    """Get the WebSocket client instance."""
    websocket_service = get_websocket_service()
    if websocket_service and websocket_service.client:
        return websocket_service.client
    return None


def get_api_config_service() -> Any:
    """Get singleton API config service instance."""
    def create_api_config_service() -> Any:
        from services.api_config_service import APIConfigService
        return APIConfigService()

    return service_locator.get("api_config_service", create_api_config_service)


def get_api_config_manager() -> Any:
    """Get singleton API config manager instance."""
    def create_api_config_manager() -> Any:
        from api_configs.manager import APIConfigManager
        return APIConfigManager()

    return service_locator.get("api_config_manager", create_api_config_manager)


def get_api_config_usage_tracker() -> Any:
    """Get singleton API config usage tracker instance."""
    def create_api_config_usage_tracker() -> Any:
        from api_configs.usage_tracker import APIConfigUsageTracker
        return APIConfigUsageTracker()

    return service_locator.get(
        "api_config_usage_tracker",
        create_api_config_usage_tracker
    )
