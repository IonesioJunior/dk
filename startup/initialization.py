import asyncio
import logging
import threading
import time

from api.endpoints.agent import set_agent as set_agent_agent
from api.endpoints.config import set_agent as set_config_agent
from config.settings import Settings
from dependencies import (
    get_agent,
    get_api_config_manager,
    get_api_config_usage_tracker,
    get_scheduler_service,
    get_settings,
    get_syft_client,
    get_websocket_service,
)
from syftbox.jobs import register_jobs

logger = logging.getLogger(__name__)


async def initialize_logging(settings: Settings) -> None:
    """Initialize logging configuration."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Logging initialized")


async def initialize_agent() -> None:
    """Initialize the agent and set it in the config and agent modules."""
    agent = get_agent()
    set_config_agent(agent)
    set_agent_agent(agent)
    logger.info("Agent initialized and set in both config and agent modules")


async def initialize_syft_client() -> None:
    """Initialize the Syft client."""
    client = get_syft_client()
    client.initialize()
    logger.info("Syft client initialized")


async def initialize_api_config_manager() -> None:
    """Initialize the API configuration manager."""
    manager = get_api_config_manager()
    logger.info("API configuration manager initialized")


async def initialize_api_config_usage_tracker() -> None:
    """Initialize the API configuration usage tracker."""
    tracker = get_api_config_usage_tracker()
    logger.info("API configuration usage tracker initialized")


async def initialize_jobs() -> None:
    """Register periodic jobs with the scheduler."""
    register_jobs()
    logger.info("Jobs registered")


async def initialize_websocket_client(settings: Settings) -> None:
    """Initialize WebSocket client connection in a background thread."""

    def run_client() -> None:
        # Wait for app to fully initialize
        time.sleep(settings.websocket_startup_delay)

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            service = get_websocket_service()
            loop.run_until_complete(service.initialize())
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {e}", exc_info=True)

    client_thread = threading.Thread(target=run_client, daemon=True)
    client_thread.start()
    logger.info("WebSocket client initialization started in background")


async def initialize_scheduler(settings: Settings) -> None:
    """Initialize scheduler in a background thread."""

    def run_scheduler() -> None:
        # Wait for any startup delay
        time.sleep(settings.scheduler_startup_delay)

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            service = get_scheduler_service()
            loop.run_until_complete(service.start())
            loop.run_forever()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler started in background")


async def initialize_services() -> None:
    """Initialize all services in the correct order."""
    print("Starting service initialization...")
    settings = get_settings()

    # Initialize in dependency order
    await initialize_logging(settings)
    print("Logging initialized")

    await initialize_agent()
    print("Agent initialized")

    await initialize_syft_client()
    print("Syft client initialized")

    await initialize_api_config_manager()
    print("API config manager initialized")
    
    await initialize_api_config_usage_tracker()
    print("API config usage tracker initialized")

    await initialize_jobs()
    print("Jobs registered")

    # Start background services
    await initialize_websocket_client(settings)
    print("WebSocket client initialization started")

    await initialize_scheduler(settings)
    print("Scheduler initialization started")

    logger.info("All services initialized successfully")


async def cleanup_services() -> None:
    """Cleanup services on shutdown."""
    logger.info("Starting cleanup process")

    try:
        # Stop scheduler
        scheduler_service = get_scheduler_service()
        await scheduler_service.stop()
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

    try:
        # Close WebSocket connection
        websocket_service = get_websocket_service()
        await websocket_service.close()
    except Exception as e:
        logger.error(f"Error closing WebSocket: {e}")

    logger.info("Cleanup completed")
