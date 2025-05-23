"""Shared fixtures for api_configs unit tests."""

from collections.abc import Generator
from pathlib import Path

import pytest

from api_configs.manager import APIConfigManager
from api_configs.models import APIConfig
from api_configs.repository import APIConfigRepository
from api_configs.usage_tracker import APIConfigUsageTracker


@pytest.fixture()
def temp_api_configs_path(tmp_path: Path) -> str:
    """Create a temporary path for API configs storage."""
    api_path = tmp_path / "api_configs"
    return str(api_path)


@pytest.fixture()
def temp_usage_path(tmp_path: Path) -> str:
    """Create a temporary path for usage tracking storage."""
    usage_path = tmp_path / "api_usage"
    return str(usage_path)


@pytest.fixture()
def sample_api_configs() -> list[APIConfig]:
    """Create sample API configurations for testing."""
    return [
        APIConfig(
            config_id="config-1",
            users=["user-1", "user-2"],
            datasets=["dataset-1", "dataset-2"],
        ),
        APIConfig(
            config_id="config-2",
            users=["user-3", "user-4", "user-5"],
            datasets=["dataset-3"],
        ),
        APIConfig(
            config_id="config-3",
            users=["user-6"],
            datasets=["dataset-4", "dataset-5", "dataset-6"],
        ),
    ]


@pytest.fixture()
def api_config_repository(temp_api_configs_path: str) -> APIConfigRepository:
    """Create a clean API config repository instance."""
    return APIConfigRepository(database_path=temp_api_configs_path)


@pytest.fixture()
def api_config_manager() -> Generator[APIConfigManager, None, None]:
    """Create a clean API config manager instance."""
    # Reset singleton instances
    APIConfigManager._instance = None
    APIConfigManager._repository = None

    manager = APIConfigManager()
    yield manager

    # Cleanup
    APIConfigManager._instance = None
    APIConfigManager._repository = None


@pytest.fixture()
def usage_tracker(temp_usage_path: str) -> Generator[APIConfigUsageTracker, None, None]:
    """Create a clean usage tracker instance."""
    # Reset singleton instance
    APIConfigUsageTracker._instance = None

    tracker = APIConfigUsageTracker()
    tracker.database_path = temp_usage_path
    tracker.logs_path = Path(temp_usage_path) / "logs"
    tracker.metrics_path = Path(temp_usage_path) / "metrics"
    tracker.logs_path.mkdir(parents=True, exist_ok=True)
    tracker.metrics_path.mkdir(parents=True, exist_ok=True)
    yield tracker

    # Cleanup
    APIConfigUsageTracker._instance = None


@pytest.fixture()
def populated_repository(
    api_config_repository: APIConfigRepository, sample_api_configs: list[APIConfig]
) -> APIConfigRepository:
    """Create a repository populated with sample data."""
    for config in sample_api_configs:
        api_config_repository.create(config)
    return api_config_repository


@pytest.fixture()
def sample_prompts() -> dict[str, str]:
    """Sample prompts for usage tracking tests."""
    return {
        "short_input": "Hello world",
        "short_output": "Hi there",
        "medium_input": "This is a medium length input prompt with several words",
        "medium_output": "This is a medium length output response with several words",
        "long_input": " ".join([f"word{i}" for i in range(100)]),
        "long_output": " ".join([f"response{i}" for i in range(100)]),
        "empty_input": "",
        "empty_output": "",
    }
