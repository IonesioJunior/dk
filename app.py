"""
Syft Agent Application

Main entry point for the Syft Agent FastAPI application.
Uses the factory pattern to create and configure the app.
"""

from dependencies import get_settings
from factory import create_app

# Add startup logging
print("Loading Syft Agent application...")

try:
    # Create the FastAPI app instance and Syftbox wrapper
    app, syftbox = create_app()
    print("Syft Agent application created successfully")
except Exception as e:
    print(f"Error creating application: {e}")
    import traceback

    traceback.print_exc()
    raise


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(syftbox.app, host=settings.host, port=settings.port)
