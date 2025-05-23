import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastsyftbox import Syftbox

from api.routes import api_router
from dependencies import get_settings
from rpc.rpc_handler import ping_handler
from startup.initialization import cleanup_services, initialize_services

# Get logger without reconfiguring (logging is already configured in initialization.py)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    # Startup
    print("Starting application lifecycle...")
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting application lifecycle (logger)")
    try:
        await initialize_services()
        print("Services initialized successfully")
    except Exception as e:
        print(f"Error during initialization: {e}")
        import traceback

        traceback.print_exc()
    yield
    # Shutdown
    print("Shutting down application...")
    try:
        await cleanup_services()
        print("Cleanup completed")
    except Exception as e:
        print(f"Error during cleanup: {e}")
        import traceback

        traceback.print_exc()


def create_app() -> tuple[FastAPI, Syftbox]:
    """Factory function to create the FastAPI application and Syftbox wrapper."""
    logger.info("Creating FastAPI application...")
    settings = get_settings()

    # Create FastAPI app with lifespan context manager
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Include API routes
    app.include_router(api_router)

    # Mount main static directory
    static_path = Path(__file__).parent / "api" / "static"
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    # Setup Syftbox
    logger.info("Creating Syftbox wrapper...")
    syftbox = Syftbox(
        app=app,
        name=Path(__file__).resolve().parent.name,
    )

    # Register RPC handlers
    syftbox.on_request("/ping")(ping_handler)

    # Since Syftbox overrides the lifespan, we need to patch it
    # to include our initialization

    import asyncio

    def patched_attach_lifespan() -> None:
        @asynccontextmanager
        async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
            # Our startup logic
            logger.info("Patched lifespan startup")
            await initialize_services()
            logger.info("Services initialized in patched lifespan")

            # Original Syftbox startup
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, syftbox.box.run_forever)

            yield

            # Our shutdown logic
            logger.info("Patched lifespan shutdown")
            await cleanup_services()

        syftbox.app.router.lifespan_context = lifespan

    # Replace the lifespan attachment
    syftbox._attach_lifespan = patched_attach_lifespan
    syftbox._attach_lifespan()

    logger.info("App creation completed with patched lifespan")
    return app, syftbox
