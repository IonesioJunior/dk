"""API endpoint for getting active users."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from syftbox.client import syft_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/syftbox/active-users", response_model=Dict[str, Any])
async def get_active_users():
    """
    Get active users from datasites.
    
    Returns a JSON structure where the keys are the datasite folder names
    and the values are their respective status.json values.
    """
    try:
        # Get the path to datasites from the syft_client
        try:
            datasites_dir = syft_client.client.datasites
            
            if not datasites_dir or not isinstance(datasites_dir, Path) or not datasites_dir.exists():
                logger.warning("Datasites directory does not exist or is not accessible")
                return {}
        except (AttributeError, TypeError) as e:
            logger.warning(f"Error accessing datasites property: {e}")
            return {}
        
        active_users = {}
        
        # Iterate over each folder in datasites directory
        try:
            folders = os.listdir(datasites_dir)
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Could not list datasites directory: {e}")
            return {}
            
        for folder in folders:
            folder_path = datasites_dir / folder
            if not folder_path.is_dir():
                continue
            
            # Check if status.json exists in the expected path
            status_file_path = folder_path / "public" / "syft_agent" / "status.json"
            if not status_file_path.exists():
                continue
            
            # Read and parse status.json
            try:
                with open(status_file_path, "r") as f:
                    status_data = json.load(f)
                active_users[folder] = status_data
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Error reading status.json for {folder}: {e}")
                # Skip this folder if there's an error reading the file
                continue
        
        return active_users
    except Exception as e:
        logger.error(f"Failed to get active users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active users: {str(e)}")
