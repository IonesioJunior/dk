"""Unit tests for api_configs.manager module."""

from unittest.mock import MagicMock, patch

import pytest

from api_configs.manager import APIConfigManager
from api_configs.models import APIConfig


class TestAPIConfigManager:
    """Test suite for APIConfigManager."""

    @pytest.fixture()
    def mock_repository(self) -> MagicMock:
        """Create a mock repository for testing."""
        return MagicMock()

    @pytest.fixture()
    def manager(self, mock_repository: MagicMock) -> APIConfigManager:
        """Create a manager instance with mocked repository."""
        # Reset singleton instance
        APIConfigManager._instance = None
        APIConfigManager._repository = None

        with patch(
            "api_configs.manager.APIConfigRepository", return_value=mock_repository
        ):
            manager = APIConfigManager()
            manager._repository = mock_repository
            return manager

    def test_singleton_pattern(self) -> None:
        """Test that APIConfigManager follows singleton pattern."""
        # Reset singleton
        APIConfigManager._instance = None

        manager1 = APIConfigManager()
        manager2 = APIConfigManager()

        assert manager1 is manager2

    def test_initialization_with_repository(self, mock_repository: MagicMock) -> None:
        """Test manager initialization creates repository."""
        APIConfigManager._instance = None
        APIConfigManager._repository = None

        with patch(
            "api_configs.manager.APIConfigRepository", return_value=mock_repository
        ):
            manager = APIConfigManager()

        assert manager._repository is not None

    def test_initialization_failure(self) -> None:
        """Test manager handles repository initialization failure."""
        APIConfigManager._instance = None
        APIConfigManager._repository = None

        with (
            patch(
                "api_configs.manager.APIConfigRepository",
                side_effect=Exception("Init failed"),
            ),
            pytest.raises(Exception, match="Init failed"),
        ):
            APIConfigManager()

    def test_get_policy_for_user_found(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test getting policy for user when user is in a policy."""
        # Setup mock data
        config1 = APIConfig(config_id="policy-1", users=["user-1", "user-2"])
        config2 = APIConfig(config_id="policy-2", users=["user-3", "user-4"])
        config3 = APIConfig(config_id="policy-3", users=["user-5"])

        mock_repository.get_all.return_value = [config1, config2, config3]

        # Test finding users in different policies
        assert manager.get_policy_for_user("user-1") == "policy-1"
        assert manager.get_policy_for_user("user-2") == "policy-1"
        assert manager.get_policy_for_user("user-3") == "policy-2"
        assert manager.get_policy_for_user("user-5") == "policy-3"

    def test_get_policy_for_user_not_found(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test getting policy for user when user is not in any policy."""
        config1 = APIConfig(config_id="policy-1", users=["user-1"])
        mock_repository.get_all.return_value = [config1]

        result = manager.get_policy_for_user("user-999")
        assert result is None

    def test_get_policy_for_user_empty_configs(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test getting policy for user when no configs exist."""
        mock_repository.get_all.return_value = []

        result = manager.get_policy_for_user("any-user")
        assert result is None

    def test_get_policy_for_user_error_handling(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test error handling in get_policy_for_user."""
        mock_repository.get_all.side_effect = Exception("Database error")

        result = manager.get_policy_for_user("user-1")
        assert result is None

    def test_get_datasets_for_policy_found(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test getting datasets for existing policy."""
        datasets = ["dataset-1", "dataset-2"]
        config = APIConfig(config_id="policy-1", datasets=datasets)
        mock_repository.get_by_id.return_value = config

        result = manager.get_datasets_for_policy("policy-1")
        assert result == datasets

    def test_get_datasets_for_policy_not_found(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test getting datasets for non-existent policy."""
        mock_repository.get_by_id.return_value = None

        result = manager.get_datasets_for_policy("non-existent")
        assert result == []

    def test_get_datasets_for_policy_error_handling(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test error handling in get_datasets_for_policy."""
        mock_repository.get_by_id.side_effect = Exception("Database error")

        result = manager.get_datasets_for_policy("policy-1")
        assert result == []

    def test_can_add_users_to_policy_all_valid(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test checking if all users can be added (no conflicts)."""
        mock_repository.get_all.return_value = []  # No existing configs

        can_add, conflicts = manager.can_add_users_to_policy(
            ["user-1", "user-2", "user-3"]
        )

        assert can_add is True
        assert conflicts == []

    def test_can_add_users_to_policy_some_conflicts(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test checking users with some conflicts."""
        # user-2 is already in policy-1
        config = APIConfig(config_id="policy-1", users=["user-2"])
        mock_repository.get_all.return_value = [config]

        can_add, conflicts = manager.can_add_users_to_policy(
            ["user-1", "user-2", "user-3"]
        )

        assert can_add is False
        assert conflicts == ["user-2"]

    def test_can_add_users_to_policy_all_conflicts(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test checking users when all have conflicts."""
        # All users are in different policies
        config1 = APIConfig(config_id="policy-1", users=["user-1"])
        config2 = APIConfig(config_id="policy-2", users=["user-2"])
        config3 = APIConfig(config_id="policy-3", users=["user-3"])
        mock_repository.get_all.return_value = [config1, config2, config3]

        can_add, conflicts = manager.can_add_users_to_policy(
            ["user-1", "user-2", "user-3"]
        )

        assert can_add is False
        assert set(conflicts) == {"user-1", "user-2", "user-3"}

    def test_can_add_users_to_policy_with_policy_id(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test checking users for update scenario (with policy_id)."""
        # user-1 and user-2 are in policy-1
        config = APIConfig(config_id="policy-1", users=["user-1", "user-2"])
        mock_repository.get_all.return_value = [config]

        # Can add these users to policy-1 (they're already there)
        can_add, conflicts = manager.can_add_users_to_policy(
            ["user-1", "user-2", "user-3"], policy_id="policy-1"
        )

        assert can_add is True
        assert conflicts == []

        # Cannot add these users to policy-2 (they're in policy-1)
        can_add, conflicts = manager.can_add_users_to_policy(
            ["user-1", "user-2", "user-3"], policy_id="policy-2"
        )

        assert can_add is False
        assert set(conflicts) == {"user-1", "user-2"}

    def test_can_add_empty_users_list(self, manager: APIConfigManager) -> None:
        """Test checking empty users list."""
        can_add, conflicts = manager.can_add_users_to_policy([])

        assert can_add is True
        assert conflicts == []

    def test_manager_with_large_number_of_configs(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test manager performance with large number of configs."""
        # Create 1000 configs with different users
        configs = []
        for i in range(1000):
            config = APIConfig(
                config_id=f"policy-{i}", users=[f"user-{i}-1", f"user-{i}-2"]
            )
            configs.append(config)

        mock_repository.get_all.return_value = configs

        # Should find user in correct policy
        result = manager.get_policy_for_user("user-500-1")
        assert result == "policy-500"

        # Should not find non-existent user
        result = manager.get_policy_for_user("user-9999")
        assert result is None

    def test_manager_handles_duplicate_users_in_policy(
        self, manager: APIConfigManager, mock_repository: MagicMock
    ) -> None:
        """Test manager handles policies with duplicate users gracefully."""
        # Policy with duplicate users (shouldn't happen but test resilience)
        config = APIConfig(
            config_id="policy-1",
            users=["user-1", "user-1", "user-2"],  # user-1 appears twice
        )
        mock_repository.get_all.return_value = [config]

        # Should still find the user
        result = manager.get_policy_for_user("user-1")
        assert result == "policy-1"
