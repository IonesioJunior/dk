"""Unit tests for api_configs.models module."""

import uuid
from datetime import datetime, timezone

from api_configs.models import APIConfig, APIConfigUpdate

# Constants for test values
UNIQUE_IDS_COUNT = 10
DATETIME_TEST_YEAR = 2024
DATETIME_TEST_DAY = 15


class TestAPIConfig:
    """Test suite for APIConfig dataclass."""

    def test_apiconfig_creation_with_defaults(self) -> None:
        """Test APIConfig creation with default values."""
        config = APIConfig()

        assert isinstance(config.config_id, str)
        assert uuid.UUID(config.config_id)  # Verify it's a valid UUID
        assert config.users == []
        assert config.datasets == []
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)
        assert config.created_at <= config.updated_at

    def test_apiconfig_creation_with_values(self) -> None:
        """Test APIConfig creation with specified values."""
        test_id = "test-config-123"
        test_users = ["user1", "user2"]
        test_datasets = ["dataset1", "dataset2"]

        config = APIConfig(config_id=test_id, users=test_users, datasets=test_datasets)

        assert config.config_id == test_id
        assert config.users == test_users
        assert config.datasets == test_datasets

    def test_apiconfig_config_id_field(self) -> None:
        """Test the config_id field is properly set."""
        config = APIConfig()
        assert config.config_id is not None
        assert isinstance(config.config_id, str)
        assert uuid.UUID(config.config_id)  # Verify it's a valid UUID

    def test_apiconfig_to_dict(self) -> None:
        """Test conversion of APIConfig to dictionary."""
        config = APIConfig(config_id="test-123", users=["user1"], datasets=["dataset1"])

        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "test-123"
        assert result["users"] == ["user1"]
        assert result["datasets"] == ["dataset1"]
        assert "created_at" in result
        assert "updated_at" in result
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)

    def test_apiconfig_from_dict_complete(self) -> None:
        """Test creation of APIConfig from complete dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "id": "test-456",
            "users": ["user1", "user2"],
            "datasets": ["dataset1"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        config = APIConfig.from_dict(data)

        assert config.config_id == "test-456"
        assert config.users == ["user1", "user2"]
        assert config.datasets == ["dataset1"]
        assert config.created_at.isoformat() == now.isoformat()
        assert config.updated_at.isoformat() == now.isoformat()

    def test_apiconfig_from_dict_minimal(self) -> None:
        """Test creation of APIConfig from minimal dictionary."""
        data = {"id": "test-789"}

        config = APIConfig.from_dict(data)

        assert config.config_id == "test-789"
        assert config.users == []
        assert config.datasets == []
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)

    def test_apiconfig_from_dict_empty(self) -> None:
        """Test creation of APIConfig from empty dictionary."""
        data = {}

        config = APIConfig.from_dict(data)

        assert config.config_id is None
        assert config.users == []
        assert config.datasets == []

    def test_apiconfig_from_dict_missing_fields(self) -> None:
        """Test creation of APIConfig with some missing fields."""
        data = {
            "id": "test-partial",
            "users": ["user1"],
            # datasets missing
        }

        config = APIConfig.from_dict(data)

        assert config.config_id == "test-partial"
        assert config.users == ["user1"]
        assert config.datasets == []

    def test_apiconfig_roundtrip_conversion(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = APIConfig(
            config_id="roundtrip-test",
            users=["user1", "user2", "user3"],
            datasets=["data1", "data2"],
        )

        dict_form = original.to_dict()
        restored = APIConfig.from_dict(dict_form)

        assert restored.config_id == original.config_id
        assert restored.users == original.users
        assert restored.datasets == original.datasets
        assert restored.created_at.isoformat() == original.created_at.isoformat()
        assert restored.updated_at.isoformat() == original.updated_at.isoformat()

    def test_apiconfig_unique_ids(self) -> None:
        """Test that multiple APIConfig instances get unique IDs."""
        configs = [APIConfig() for _ in range(UNIQUE_IDS_COUNT)]
        config_ids = [config.config_id for config in configs]

        assert len(set(config_ids)) == UNIQUE_IDS_COUNT  # All IDs should be unique

    def test_apiconfig_datetime_parsing_edge_cases(self) -> None:
        """Test datetime parsing with various formats."""
        # Test with microseconds
        data = {
            "id": "datetime-test",
            "created_at": "2024-01-15T10:30:45.123456",
            "updated_at": "2024-01-15T10:30:45.123456",
        }

        config = APIConfig.from_dict(data)
        assert config.created_at.year == DATETIME_TEST_YEAR
        assert config.created_at.month == 1
        assert config.created_at.day == DATETIME_TEST_DAY


class TestAPIConfigUpdate:
    """Test suite for APIConfigUpdate dataclass."""

    def test_apiconfigupdate_all_none(self) -> None:
        """Test APIConfigUpdate with all None values."""
        update = APIConfigUpdate()

        assert update.users is None
        assert update.datasets is None

    def test_apiconfigupdate_with_users(self) -> None:
        """Test APIConfigUpdate with only users specified."""
        update = APIConfigUpdate(users=["new_user1", "new_user2"])

        assert update.users == ["new_user1", "new_user2"]
        assert update.datasets is None

    def test_apiconfigupdate_with_datasets(self) -> None:
        """Test APIConfigUpdate with only datasets specified."""
        update = APIConfigUpdate(datasets=["new_dataset1"])

        assert update.users is None
        assert update.datasets == ["new_dataset1"]

    def test_apiconfigupdate_with_both_fields(self) -> None:
        """Test APIConfigUpdate with both fields specified."""
        update = APIConfigUpdate(
            users=["user1", "user2"], datasets=["dataset1", "dataset2", "dataset3"]
        )

        assert update.users == ["user1", "user2"]
        assert update.datasets == ["dataset1", "dataset2", "dataset3"]

    def test_apiconfigupdate_empty_lists(self) -> None:
        """Test APIConfigUpdate with empty lists (to clear values)."""
        update = APIConfigUpdate(users=[], datasets=[])

        assert update.users == []
        assert update.datasets == []
        assert update.users is not None  # Empty list is different from None
        assert update.datasets is not None
