"""Repository for Triage request persistence."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from .triage_models import TriageRequest, TriageUpdate

logger = logging.getLogger(__name__)


class TriageRepository:
    """File-based repository for triage requests."""

    def __init__(self, base_path: str = "./cache/triage") -> None:
        """Initialize the repository with a base path."""
        self.base_path = Path(base_path)
        self._ensure_directory_exists()
        self._index_file = self.base_path / "_index.json"
        self._ensure_index_exists()

    def _ensure_directory_exists(self) -> None:
        """Ensure the base directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _ensure_index_exists(self) -> None:
        """Ensure the index file exists."""
        if not self._index_file.exists():
            self._write_index({})

    def _read_index(self) -> dict[str, Any]:
        """Read the index file."""
        try:
            with self._index_file.open() as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading index file: {e}")
            return {}

    def _write_index(self, index: dict[str, Any]) -> None:
        """Write the index file."""
        try:
            with self._index_file.open("w") as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing index file: {e}")

    def _get_triage_file_path(self, triage_id: str) -> Path:
        """Get the file path for a triage request."""
        return self.base_path / f"{triage_id}.json"

    def create(self, triage_request: TriageRequest) -> TriageRequest:
        """Create a new triage request."""
        # Save the triage request file
        file_path = self._get_triage_file_path(triage_request.triage_id)
        with file_path.open("w") as f:
            json.dump(triage_request.to_dict(), f, indent=2)

        # Update the index
        index = self._read_index()
        index[triage_request.triage_id] = {
            "user_id": triage_request.user_id,
            "prompt_id": triage_request.prompt_id,
            "api_config_id": triage_request.api_config_id,
            "status": triage_request.status,
            "created_at": triage_request.created_at.isoformat(),
        }
        self._write_index(index)

        logger.info(f"Created triage request: {triage_request.triage_id}")
        return triage_request

    def get(self, triage_id: str) -> Optional[TriageRequest]:
        """Get a triage request by ID."""
        file_path = self._get_triage_file_path(triage_id)
        if not file_path.exists():
            return None

        try:
            with file_path.open() as f:
                data = json.load(f)
                return TriageRequest.from_dict(data)
        except Exception as e:
            logger.error(f"Error reading triage request {triage_id}: {e}")
            return None

    def get_by_prompt_id(self, prompt_id: str) -> Optional[TriageRequest]:
        """Get a triage request by prompt ID."""
        index = self._read_index()
        for triage_id, metadata in index.items():
            if metadata.get("prompt_id") == prompt_id:
                return self.get(triage_id)
        return None

    def update_status(
        self, triage_id: str, update: TriageUpdate
    ) -> Optional[TriageRequest]:
        """Update the status of a triage request."""
        triage_request = self.get(triage_id)
        if not triage_request:
            return None

        # Update the triage request
        triage_request.status = update.status
        triage_request.reviewed_at = update.reviewed_at
        triage_request.reviewed_by = update.reviewed_by
        if update.rejection_reason:
            triage_request.rejection_reason = update.rejection_reason

        # Save the updated request
        file_path = self._get_triage_file_path(triage_id)
        with file_path.open("w") as f:
            json.dump(triage_request.to_dict(), f, indent=2)

        # Update the index
        index = self._read_index()
        if triage_id in index:
            index[triage_id]["status"] = update.status
            self._write_index(index)

        logger.info(f"Updated triage request {triage_id} to status: {update.status}")
        return triage_request

    def list_pending(self) -> list[TriageRequest]:
        """List all pending triage requests."""
        return self._list_by_status("pending")

    def list_by_user(self, user_id: str) -> list[TriageRequest]:
        """List all triage requests for a specific user."""
        index = self._read_index()
        requests = []

        for triage_id, metadata in index.items():
            if metadata.get("user_id") == user_id:
                request = self.get(triage_id)
                if request:
                    requests.append(request)

        # Sort by created_at descending
        requests.sort(key=lambda r: r.created_at, reverse=True)
        return requests

    def list_by_api_config(self, api_config_id: str) -> list[TriageRequest]:
        """List all triage requests for a specific API configuration."""
        index = self._read_index()
        requests = []

        for triage_id, metadata in index.items():
            if metadata.get("api_config_id") == api_config_id:
                request = self.get(triage_id)
                if request:
                    requests.append(request)

        # Sort by created_at descending
        requests.sort(key=lambda r: r.created_at, reverse=True)
        return requests

    def _list_by_status(self, status: str) -> list[TriageRequest]:
        """List all triage requests with a specific status."""
        index = self._read_index()
        requests = []

        for triage_id, metadata in index.items():
            if metadata.get("status") == status:
                request = self.get(triage_id)
                if request:
                    requests.append(request)

        # Sort by created_at ascending (oldest first for pending)
        requests.sort(key=lambda r: r.created_at)
        return requests

    def delete(self, triage_id: str) -> bool:
        """Delete a triage request."""
        file_path = self._get_triage_file_path(triage_id)
        if not file_path.exists():
            return False

        try:
            # Remove the file
            file_path.unlink()

            # Update the index
            index = self._read_index()
            if triage_id in index:
                del index[triage_id]
                self._write_index(index)

            logger.info(f"Deleted triage request: {triage_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting triage request {triage_id}: {e}")
            return False

    def cleanup_old_requests(self, days: int = 30) -> int:
        """Clean up old reviewed triage requests."""
        from datetime import datetime, timedelta, timezone

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        index = self._read_index()
        deleted_count = 0

        for triage_id in list(index.keys()):
            request = self.get(triage_id)
            if (
                request
                and request.status in ["approved", "rejected"]
                and request.reviewed_at
                and request.reviewed_at < cutoff_date
                and self.delete(triage_id)
            ):
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old triage requests")
        return deleted_count
