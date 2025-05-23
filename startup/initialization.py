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
    _ = get_api_config_manager()
    logger.info("API configuration manager initialized")


async def initialize_api_config_usage_tracker() -> None:
    """Initialize the API configuration usage tracker."""
    _ = get_api_config_usage_tracker()
    logger.info("API configuration usage tracker initialized")


async def initialize_jobs() -> None:
    """Register periodic jobs with the scheduler."""
    register_jobs()
    logger.info("Jobs registered")


async def initialize_websocket_client(settings: Settings) -> None:
    """Initialize WebSocket client connection in a background thread."""
    logger.info(
        f"WebSocket initialization called - onboarding: {settings.onboarding}, "
        f"username: {settings.syftbox_username}"
    )

    # Skip websocket initialization if in onboarding mode
    if settings.onboarding:
        logger.info("Skipping WebSocket initialization - onboarding mode active")
        return

    # Skip if username not set
    if not settings.syftbox_username:
        logger.warning("Skipping WebSocket initialization - username not set")
        return

    def run_client() -> None:
        logger.info("WebSocket client thread started")
        # Wait for app to fully initialize
        logger.info(
            f"Waiting {settings.websocket_startup_delay} seconds before connecting..."
        )
        time.sleep(settings.websocket_startup_delay)

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            logger.info("Getting WebSocket service...")
            service = get_websocket_service()
            logger.info("Initializing WebSocket connection...")
            loop.run_until_complete(service.initialize())
            logger.info("WebSocket initialization completed")
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

    # Check if in onboarding mode
    if settings.onboarding:
        logger.info("Application in onboarding mode")
        print("Application in onboarding mode - some services will not be initialized")

    await initialize_agent()
    print("Agent initialized")

    await initialize_syft_client()
    print("Syft client initialized")

    await initialize_api_config_manager()
    print("API config manager initialized")

    await initialize_api_config_usage_tracker()
    print("API config usage tracker initialized")

    # Only register jobs if not in onboarding mode
    if not settings.onboarding:
        await initialize_jobs()
        print("Jobs registered")
    else:
        logger.info("Skipping job registration - onboarding mode active")

    # Start background services (websocket will check onboarding internally)
    await initialize_websocket_client(settings)
    print("WebSocket client initialization started")

    # Only start scheduler if not in onboarding mode (has jobs to run)
    if not settings.onboarding:
        await initialize_scheduler(settings)
        print("Scheduler initialization started")
    else:
        logger.info("Skipping scheduler initialization - onboarding mode active")

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


async def complete_onboarding_and_restart_services(
    username: str, llm_config: dict
) -> None:
    """Complete onboarding and restart necessary services.

    Args:
        username: Syftbox username
        llm_config: Model configuration dictionary
    """
    logger.info("Completing onboarding process")

    # Get and update settings
    settings = get_settings()
    from config.settings import ModelConfig, reload_settings
    from service_locator import service_locator

    llm_config_obj = ModelConfig(**llm_config)
    settings.complete_onboarding(username, llm_config_obj)

    # Clear cached settings to ensure fresh reload
    if "settings" in service_locator._services:
        del service_locator._services["settings"]

    # Force reload of settings
    settings = reload_settings()

    # Reload agent with new settings
    agent = get_agent()
    agent.reload_from_settings()

    # Verify agent is properly configured
    if not agent.is_configured():
        logger.error("Agent is not properly configured after onboarding!")
        raise RuntimeError("Agent configuration failed after onboarding")

    logger.info(
        f"Agent configured with provider: {agent.provider_name}, "
        f"model: {agent.model}"
    )

    # Clear cached WebSocket service to force recreation with updated agent
    if "websocket_service" in service_locator._services:
        # Close existing websocket if any
        try:
            old_ws_service = service_locator._services["websocket_service"]
            if old_ws_service and old_ws_service.client:
                await old_ws_service.close()
        except Exception as e:
            logger.warning(f"Error closing old websocket service: {e}")

        # Remove from service locator to force recreation
        del service_locator._services["websocket_service"]
        logger.info("Cleared cached WebSocket service")

    # Register jobs now that we're out of onboarding
    await initialize_jobs()

    # Start the scheduler (it wasn't started during onboarding)
    logger.info("Starting scheduler with registered jobs...")
    await initialize_scheduler(settings)

    # Initialize websocket connection with properly configured agent
    await initialize_websocket_client(settings)

    logger.info("Onboarding completed and services restarted")
