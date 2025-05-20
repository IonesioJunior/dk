"""
APIConfigUsageTracker - Tracks usage metrics for API configurations

Provides a centralized tracker for API usage statistics including requests,
input/output sizes, and user frequency data.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class APIConfigUsageLog:
    """Individual API usage log entry"""

    api_config_id: str
    user_id: str
    input_prompt: str
    output_prompt: str
    input_size: int
    output_size: int
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.log_id,
            "api_config_id": self.api_config_id,
            "user_id": self.user_id,
            "input_prompt": self.input_prompt,
            "output_prompt": self.output_prompt,
            "input_size": self.input_size,
            "output_size": self.output_size,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "APIConfigUsageLog":
        usage_log = cls(
            api_config_id=data.get("api_config_id"),
            user_id=data.get("user_id"),
            input_prompt=data.get("input_prompt", ""),
            output_prompt=data.get("output_prompt", ""),
            input_size=data.get("input_size", 0),
            output_size=data.get("output_size", 0),
            log_id=data.get("id", str(uuid.uuid4())),
        )
        if "timestamp" in data:
            usage_log.timestamp = datetime.fromisoformat(data["timestamp"])
        return usage_log


@dataclass
class APIConfigMetrics:
    """Aggregated metrics for an API configuration"""

    api_config_id: str
    total_requests: int = 0
    total_input_size: int = 0
    total_output_size: int = 0
    user_frequency: dict[str, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "api_config_id": self.api_config_id,
            "total_requests": self.total_requests,
            "total_input_size": self.total_input_size,
            "total_output_size": self.total_output_size,
            "user_frequency": self.user_frequency,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "APIConfigMetrics":
        metrics = cls(
            api_config_id=data.get("api_config_id"),
            total_requests=data.get("total_requests", 0),
            total_input_size=data.get("total_input_size", 0),
            total_output_size=data.get("total_output_size", 0),
            user_frequency=data.get("user_frequency", {}),
        )
        if "last_updated" in data:
            metrics.last_updated = datetime.fromisoformat(data["last_updated"])
        return metrics


class APIConfigUsageTracker:
    """
    Tracks usage of API configurations and provides metrics.

    This class is responsible for recording API usage and computing metrics
    like input/output sizes, request counts, and user frequency.
    """

    _instance = None

    def __new__(cls) -> "APIConfigUsageTracker":
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, database_path: str = "./cache/api_usage") -> None:
        """Initialize the tracker"""
        if getattr(self, "_initialized", False):
            return

        self.database_path = database_path
        self.logs_path = Path(database_path) / "logs"
        self.metrics_path = Path(database_path) / "metrics"

        Path(self.logs_path).mkdir(parents=True, exist_ok=True)
        Path(self.metrics_path).mkdir(parents=True, exist_ok=True)

        self._initialized = True
        logger.info("APIConfigUsageTracker initialized")

    def track_usage(
        self, api_config_id: str, user_id: str, input_prompt: str, output_prompt: str
    ) -> APIConfigUsageLog:
        """
        Track usage of an API configuration.

        Args:
            api_config_id: The ID of the API configuration
            user_id: The ID of the user making the request
            input_prompt: The input prompt text
            output_prompt: The output prompt text

        Returns:
            The created usage log entry
        """
        try:
            # Calculate sizes in words
            input_size = len(input_prompt.split())
            output_size = len(output_prompt.split())

            # Create usage log
            usage_log = APIConfigUsageLog(
                api_config_id=api_config_id,
                user_id=user_id,
                input_prompt=input_prompt,
                output_prompt=output_prompt,
                input_size=input_size,
                output_size=output_size,
            )

            # Save the log
            self._save_usage_log(usage_log)

            # Update metrics
            self._update_metrics(usage_log)

            return usage_log

        except Exception as e:
            logger.error(f"Error tracking API config usage: {e}")
            # Create a basic log entry even if there's an error
            return APIConfigUsageLog(
                api_config_id=api_config_id,
                user_id=user_id,
                input_prompt=input_prompt,
                output_prompt=output_prompt,
                input_size=len(input_prompt.split()),
                output_size=len(output_prompt.split()),
            )

    def _save_usage_log(self, usage_log: APIConfigUsageLog) -> None:
        """Save a usage log to the filesystem"""
        file_path = Path(self.logs_path) / f"{usage_log.log_id}.json"
        with file_path.open("w") as f:
            json.dump(usage_log.to_dict(), f, indent=2)

    def _update_metrics(self, usage_log: APIConfigUsageLog) -> None:
        """
        Update metrics for the API configuration based on a new usage log.

        Args:
            usage_log: The usage log to incorporate into metrics
        """
        try:
            # Get existing metrics or create new ones
            metrics = self.get_metrics(usage_log.api_config_id)
            if not metrics:
                metrics = APIConfigMetrics(api_config_id=usage_log.api_config_id)

            # Update metrics
            metrics.total_requests += 1
            metrics.total_input_size += usage_log.input_size
            metrics.total_output_size += usage_log.output_size

            # Update user frequency
            if usage_log.user_id in metrics.user_frequency:
                metrics.user_frequency[usage_log.user_id] += 1
            else:
                metrics.user_frequency[usage_log.user_id] = 1

            # Update timestamp
            metrics.last_updated = datetime.utcnow()

            # Save updated metrics
            self._save_metrics(metrics)

        except Exception as e:
            logger.error(
                f"Error updating metrics for API config {usage_log.api_config_id}: {e}"
            )

    def _save_metrics(self, metrics: APIConfigMetrics) -> None:
        """Save metrics to the filesystem"""
        file_path = Path(self.metrics_path) / f"{metrics.api_config_id}.json"
        with file_path.open("w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

    def get_metrics(self, api_config_id: str) -> Optional[APIConfigMetrics]:
        """
        Get metrics for a specific API configuration.

        Args:
            api_config_id: The ID of the API configuration

        Returns:
            The metrics for the API configuration, or None if not found
        """
        file_path = Path(self.metrics_path) / f"{api_config_id}.json"
        if not file_path.exists():
            return None

        with file_path.open() as f:
            try:
                data = json.load(f)
                return APIConfigMetrics.from_dict(data)
            except json.JSONDecodeError:
                return None

    def get_all_metrics(self) -> list[APIConfigMetrics]:
        """
        Get metrics for all API configurations.

        Returns:
            A list of metrics for all API configurations
        """
        metrics_list = []
        for file_path in self.metrics_path.iterdir():
            if not file_path.name.endswith(".json"):
                continue
            with file_path.open() as f:
                try:
                    data = json.load(f)
                    metrics_list.append(APIConfigMetrics.from_dict(data))
                except json.JSONDecodeError:
                    continue

        return metrics_list

    def get_usage_logs(
        self, api_config_id: str, limit: int = 100, offset: int = 0
    ) -> list[APIConfigUsageLog]:
        """
        Get usage logs for a specific API configuration.

        Args:
            api_config_id: The ID of the API configuration
            limit: Maximum number of logs to return
            offset: Number of logs to skip

        Returns:
            A list of usage logs
        """
        logs = []
        for file_path in self.logs_path.iterdir():
            if not file_path.name.endswith(".json"):
                continue
            with file_path.open() as f:
                try:
                    data = json.load(f)
                    if data.get("api_config_id") == api_config_id:
                        logs.append(APIConfigUsageLog.from_dict(data))
                except json.JSONDecodeError:
                    continue

        # Sort by timestamp descending
        logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        return logs[offset : offset + limit]

    def get_top_users(self, api_config_id: str, limit: int = 10) -> list[tuple]:
        """
        Get the top users for a specific API configuration.

        Args:
            api_config_id: The ID of the API configuration
            limit: Maximum number of users to return

        Returns:
            A list of (user_id, count) tuples sorted by count descending
        """
        metrics = self.get_metrics(api_config_id)
        if not metrics:
            return []

        sorted_users = sorted(
            metrics.user_frequency.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_users[:limit]

    def get_user_frequency(self, api_config_id: str) -> dict[str, int]:
        """
        Get the frequency of usage by user for a specific API configuration.

        Args:
            api_config_id: The ID of the API configuration

        Returns:
            A dictionary mapping user IDs to usage counts
        """
        metrics = self.get_metrics(api_config_id)
        if metrics:
            return metrics.user_frequency
        return {}
