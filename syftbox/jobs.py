"""Periodic jobs for SyftBox integration.

This module provides prepackaged jobs that can be registered with the scheduler.
"""

import json
import logging
import socket
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from .client import syft_client
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
        with urllib.request.urlopen("https://api.ipify.org/") as response:
            ip = response.read().decode("utf-8")

        # Get location data from ip-api.com
        api_url = f"http://ip-api.com/json/{ip}"
        with urllib.request.urlopen(api_url) as response:
            location_data = json.loads(response.read().decode("utf-8"))

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

        # logger.info(f"Client workspace : {syft_client.client.workspace.data_dir}")
        app_data_path = syft_client.client.my_datasite / "app_data" / app_name

        # Create status data
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "agent_version": "1.0.0",
            "last_update": datetime.now().isoformat(),
            "ip_address": get_ip_address(),
        }

        # Add location data
        location_data = get_location_data()
        status_data.update(location_data)

        # Create the file path
        status_file_path = Path(app_data_path) / "status.json"

        # Ensure parent directory exists
        status_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the JSON file
        with open(status_file_path, "w") as f:
            json.dump(status_data, f, indent=2)

        # Create permissions file only if it doesn't exist
        permissions_file = status_file_path.parent / "syftperm.yaml"

        if not permissions_file.exists():
            # Write permissions file
            with open(permissions_file, "w") as f:
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


def register_jobs() -> None:
    """Register all periodic jobs with the scheduler."""
    # Register the status file job to run every 10 seconds
    scheduler.register_job(
        job_id="status_file_writer",
        coroutine_func=write_status_file,
        interval=10.0,  # 10 seconds
        initial_delay=1.0,  # Start after 1 second delay
        app_name="syft_agent",  # Pass as parameter to the job
    )

    logger.info("Registered periodic jobs with scheduler")
