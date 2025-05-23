"""Periodic jobs for SyftBox integration.

This module provides prepackaged jobs that can be registered with the scheduler.
"""

import json
import logging
import socket
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from config.settings import get_settings

from .client import syft_client
from .message_handler import message_handler
from .scheduler import scheduler

logger = logging.getLogger(__name__)


def get_ip_address() -> str:
    """Get the local IP address.

    Returns:
        The IP address as a string, or "127.0.0.1" if unable to determine
    """
    try:
        # This creates a socket that doesn't actually connect anywhere
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # This tells the socket to try to reach a public IP (doesn't actually connect)
        s.connect(("8.8.8.8", 80))
        ip: str = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.warning(f"Could not determine IP address: {e}")
        return "127.0.0.1"


def get_location_data() -> dict[str, Any]:
    """Get location data based on IP address.

    Returns:
        A dictionary with location information or empty dict if failed
    """
    try:
        # First try to get the public IP
        ipify_url = "https://api.ipify.org/"

        # Use httpx instead of urllib.request
        with httpx.Client(timeout=10.0) as client:
            response = client.get(ipify_url)
            response.raise_for_status()
            ip = response.text

            # Get location data from ip-api.com
            api_url = f"https://ip-api.com/json/{ip}"
            response = client.get(api_url)
            response.raise_for_status()
            location_data = response.json()

        if location_data.get("status") == "success":
            return {
                "location": {
                    "latitude": location_data.get("lat"),
                    "longitude": location_data.get("lon"),
                    "city": location_data.get("city"),
                    "region": location_data.get("regionName"),
                    "country": location_data.get("country"),
                },
            }
    except Exception as e:
        logger.warning(f"Could not retrieve location data: {e}")

    # Return empty location data if any step fails
    return {"location": {"latitude": None, "longitude": None}}


async def write_status_file(app_name: str = "syft_agent") -> None:
    """Write a status JSON file to the application data directory.

    This job creates a JSON file with current timestamp and status information
    in the application data directory provided by Syft-Core.

    Args:
        app_name: The name of the application data directory to use
    """
    try:
        # Get the application data path from Syft-Core
        app_data_path = syft_client.client.app_data(app_name)

        app_data_path = syft_client.client.my_datasite / "public" / app_name

        # Get settings
        settings = get_settings()

        # Create status data
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "agent_version": "1.0.0",
            "last_update": datetime.now().isoformat(),
            "ip_address": get_ip_address(),
            "user_id": settings.syftbox_username,
        }

        # Add location data
        location_data = get_location_data()
        status_data.update(location_data)

        # Create the file path
        status_file_path = Path(app_data_path) / "status.json"

        # Ensure parent directory exists
        status_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the JSON file
        with status_file_path.open("w") as f:
            json.dump(status_data, f, indent=2)

        # Create permissions file only if it doesn't exist
        permissions_file = status_file_path.parent / "syftperm.yaml"

        if not permissions_file.exists():
            # Write permissions file
            with permissions_file.open("w") as f:
                # Simple YAML format
                f.write("rules:\n")
                f.write('  - path: "status.json"\n')
                f.write('    user: "*"\n')
                f.write('    allow: ["READ"]\n')

            logger.info(f"Created permissions file at {permissions_file}")

        # Log status file update
        logger.debug(f"Updated status file at {status_file_path}")

    except Exception as e:
        logger.error(f"Error writing status file: {e}")


async def process_websocket_messages() -> None:
    """Process incoming websocket messages.

    This job continuously processes messages from the websocket client queue
    using the WebSocketService message handler.
    """
    logger.debug("process_websocket_messages called")
    # Delegate to the message handler class
    await message_handler.process_messages()


def set_websocket_service(service: Any) -> None:
    """Set the websocket service for message processing.

    Args:
        service: The WebSocketService instance to use for message handling
    """
    # Use the message handler class instead of global variable
    message_handler.websocket_service = service


def register_jobs() -> None:
    """Register all periodic jobs with the scheduler."""
    logger.info("Starting job registration...")

    # Log current scheduler state
    logger.info(f"Scheduler running: {scheduler._is_running}")
    logger.info(f"Current jobs: {list(scheduler._jobs.keys())}")

    # Register the status file job to run every 10 seconds
    logger.info("Registering status_file_writer job...")
    scheduler.register_job(
        job_id="status_file_writer",
        coroutine_func=write_status_file,
        interval=10.0,  # 10 seconds
        initial_delay=1.0,  # Start after 1 second delay
        app_name="syft_agent",  # Pass as parameter to the job
    )

    # Register the websocket message processor job to run every 0.1 seconds
    logger.info("Registering websocket_message_processor job...")
    scheduler.register_job(
        job_id="websocket_message_processor",
        coroutine_func=process_websocket_messages,
        interval=0.1,  # Process messages frequently (100ms)
        initial_delay=2.0,  # Start after 2 second delay to allow client initialization
    )

    logger.info(
        f"Job registration complete. Jobs registered: {list(scheduler._jobs.keys())}"
    )
