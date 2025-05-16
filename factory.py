from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastsyftbox import Syftbox

from api.routes import api_router
from dependencies import get_settings
from rpc.rpc_handler import ping_handler
from startup.initialization import cleanup_services, initialize_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    print("Starting application lifecycle...")
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
    settings = get_settings()

    # Create FastAPI app with lifespan context manager
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Include API routes
    app.include_router(api_router)

    # Setup Syftbox
    syftbox = Syftbox(
        app=app,
        name=Path(__file__).resolve().parent.name,
    )

    # Register RPC handlers
    syftbox.on_request("/ping")(ping_handler)

    # Schedule initialization to run after startup
    import asyncio
    import threading

    print("Scheduling initialization...")

    def run_initialization() -> None:
        """Run initialization in a separate thread"""
        # Wait a bit for the main event loop to start
        import time

        time.sleep(2)

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            print("Running initialization in background thread...")
            loop.run_until_complete(initialize_services())
            print("Background initialization completed")
        except Exception as e:
            print(f"Error during background initialization: {e}")
            import traceback

            traceback.print_exc()
        finally:
            loop.close()

    # Start initialization in a background thread
    init_thread = threading.Thread(target=run_initialization, daemon=True)
    init_thread.start()
    print("Initialization scheduled")

    return app, syftbox
