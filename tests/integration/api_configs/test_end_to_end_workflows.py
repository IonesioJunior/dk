"""End-to-end integration tests for api_configs module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from api_configs.manager import APIConfigManager
from api_configs.models import APIConfig, APIConfigUpdate
from api_configs.repository import APIConfigRepository
from api_configs.usage_tracker import APIConfigUsageTracker

# Constants for test values
EXPECTED_TOTAL_REQUESTS_INITIAL = 3
EXPECTED_TOTAL_REQUESTS_AFTER_UPDATE = 4
EXPECTED_DATASETS_AFTER_UPDATE = 3
USAGE_COUNT_API1 = 5
USAGE_COUNT_API2 = 3
USAGE_COUNT_API3 = 7
CONCURRENT_CONFIGS_COUNT = 10
REQUESTS_PER_CONFIG = 5
EXPECTED_TOTAL_REQUESTS_AFTER_RESTART = 2
LARGE_SCALE_USERS_COUNT = 100
LARGE_SCALE_DATASETS_COUNT = 50
LARGE_SCALE_REQUESTS_COUNT = 100
PAGINATION_LIMIT = 10
PAGINATION_OFFSET = 10
ANALYTICS_ALICE_COUNT = 15
ANALYTICS_BOB_COUNT = 8
ANALYTICS_CHARLIE_COUNT = 20
ANALYTICS_DAVID_COUNT = 5
ANALYTICS_TOTAL_CONFIG1 = 23
ANALYTICS_TOTAL_CONFIG2 = 25


class TestAPIConfigsEndToEnd:
    """Test complete workflows across all api_configs components."""

    @pytest.fixture()
    def temp_paths(self, tmp_path: Path) -> dict[str, str]:
        """Create temporary paths for all components."""
        return {
            "configs": str(tmp_path / "api_configs"),
            "usage": str(tmp_path / "api_usage"),
        }

    @pytest.fixture()
    def integrated_system(self, temp_paths: dict[str, str]) -> dict:
        """Set up integrated api_configs system."""
        # Reset singletons
        APIConfigManager._instance = None
        APIConfigManager._repository = None
        APIConfigUsageTracker._instance = None

        # Create components
        repository = APIConfigRepository(database_path=temp_paths["configs"])

        # Create usage tracker and configure its paths
        usage_tracker = APIConfigUsageTracker()
        usage_tracker.database_path = temp_paths["usage"]
        usage_tracker.logs_path = Path(temp_paths["usage"]) / "logs"
        usage_tracker.metrics_path = Path(temp_paths["usage"]) / "metrics"
        usage_tracker.logs_path.mkdir(parents=True, exist_ok=True)
        usage_tracker.metrics_path.mkdir(parents=True, exist_ok=True)

        # Create manager with the repository
        with patch("api_configs.manager.APIConfigRepository", return_value=repository):
            manager = APIConfigManager()

        return {
            "repository": repository,
            "manager": manager,
            "usage_tracker": usage_tracker,
        }

    def test_complete_api_config_lifecycle(self, integrated_system: dict) -> None:
        """Test complete lifecycle: create, update, use, track, delete."""
        repo = integrated_system["repository"]
        manager = integrated_system["manager"]
        tracker = integrated_system["usage_tracker"]

        # Step 1: Create API configuration
        config = APIConfig(
            config_id="test-api-001",
            users=["alice", "bob"],
            datasets=["data1", "data2"],
        )
        created_config = repo.create(config)

        # Verify creation
        assert created_config.config_id == "test-api-001"
        assert manager.get_policy_for_user("alice") == "test-api-001"
        assert manager.get_policy_for_user("bob") == "test-api-001"

        # Step 2: Track usage
        tracker.track_usage(
            api_config_id="test-api-001",
            user_id="alice",
            input_prompt="What is the weather today?",
            output_prompt="I cannot access real-time weather data.",
        )

        tracker.track_usage(
            api_config_id="test-api-001",
            user_id="bob",
            input_prompt="Tell me a joke",
            output_prompt="Why did the programmer quit? They didn't get arrays!",
        )

        tracker.track_usage(
            api_config_id="test-api-001",
            user_id="alice",
            input_prompt="Another question",
            output_prompt="Another response",
        )

        # Verify usage metrics
        metrics = tracker.get_metrics("test-api-001")
        assert metrics.total_requests == EXPECTED_TOTAL_REQUESTS_INITIAL
        assert metrics.user_frequency == {"alice": 2, "bob": 1}

        # Step 3: Update configuration
        update = APIConfigUpdate(
            users=["alice", "charlie"],  # Remove bob, add charlie
            datasets=["data1", "data2", "data3"],  # Add data3
        )
        updated_config = repo.update("test-api-001", update)

        # Verify update
        assert "charlie" in updated_config.users
        assert "bob" not in updated_config.users
        assert len(updated_config.datasets) == EXPECTED_DATASETS_AFTER_UPDATE

        # Verify manager sees the update
        assert manager.get_policy_for_user("charlie") == "test-api-001"
        assert manager.get_policy_for_user("bob") is None

        # Step 4: Continue tracking usage with new user
        tracker.track_usage(
            api_config_id="test-api-001",
            user_id="charlie",
            input_prompt="Hello!",
            output_prompt="Hi there!",
        )

        # Verify updated metrics
        metrics = tracker.get_metrics("test-api-001")
        assert metrics.total_requests == EXPECTED_TOTAL_REQUESTS_AFTER_UPDATE
        assert "charlie" in metrics.user_frequency

        # Step 5: Delete configuration
        deleted = repo.delete("test-api-001")
        assert deleted is True

        # Verify deletion
        assert repo.get_by_id("test-api-001") is None
        assert manager.get_policy_for_user("alice") is None

        # Metrics should still be available after config deletion
        metrics = tracker.get_metrics("test-api-001")
        assert metrics is not None
        assert metrics.total_requests == EXPECTED_TOTAL_REQUESTS_AFTER_UPDATE

    def test_user_policy_constraint_enforcement(self, integrated_system: dict) -> None:
        """Test that user can only be in one policy constraint is enforced."""
        repo = integrated_system["repository"]
        manager = integrated_system["manager"]

        # Create first policy
        policy1 = APIConfig(
            config_id="policy-001", users=["user1", "user2"], datasets=["dataset1"]
        )
        repo.create(policy1)

        # Verify users are in policy1
        assert manager.get_policy_for_user("user1") == "policy-001"
        assert manager.get_policy_for_user("user2") == "policy-001"

        # Try to create second policy with overlapping users
        policy2 = APIConfig(
            config_id="policy-002",
            users=["user2", "user3"],  # user2 is already in policy-001
            datasets=["dataset2"],
        )

        # Check validation before creating
        can_add, conflicts = manager.can_add_users_to_policy(["user2", "user3"])
        assert can_add is False
        assert "user2" in conflicts

        # Create policy2 anyway (in real app, this would be prevented)
        repo.create(policy2)

        # Manager should still return first policy for user2 (first found)
        assert manager.get_policy_for_user("user2") == "policy-001"
        assert manager.get_policy_for_user("user3") == "policy-002"

    def test_usage_tracking_across_multiple_configs(
        self, integrated_system: dict
    ) -> None:
        """Test usage tracking works correctly with multiple configurations."""
        repo = integrated_system["repository"]
        tracker = integrated_system["usage_tracker"]

        # Create multiple configurations
        configs = [
            APIConfig(config_id="api-1", users=["user1"], datasets=["data1"]),
            APIConfig(config_id="api-2", users=["user2"], datasets=["data2"]),
            APIConfig(config_id="api-3", users=["user3"], datasets=["data3"]),
        ]

        for config in configs:
            repo.create(config)

        # Track usage for each configuration
        test_cases = [
            ("api-1", "user1", 5),
            ("api-2", "user2", 3),
            ("api-3", "user3", 7),
        ]

        for api_id, user_id, count in test_cases:
            for i in range(count):
                tracker.track_usage(
                    api_config_id=api_id,
                    user_id=user_id,
                    input_prompt=f"Question {i}",
                    output_prompt=f"Answer {i}",
                )

        # Verify metrics for each configuration
        all_metrics = tracker.get_all_metrics()
        assert len(all_metrics) == EXPECTED_DATASETS_AFTER_UPDATE

        metrics_by_id = {m.api_config_id: m for m in all_metrics}
        assert metrics_by_id["api-1"].total_requests == USAGE_COUNT_API1
        assert metrics_by_id["api-2"].total_requests == USAGE_COUNT_API2
        assert metrics_by_id["api-3"].total_requests == USAGE_COUNT_API3

    def test_concurrent_operations_simulation(self, integrated_system: dict) -> None:
        """Test system behavior under simulated concurrent operations."""
        repo = integrated_system["repository"]
        integrated_system["manager"]
        tracker = integrated_system["usage_tracker"]

        # Simulate concurrent configuration creation
        configs = []
        for i in range(CONCURRENT_CONFIGS_COUNT):
            config = APIConfig(
                config_id=f"concurrent-{i}",
                users=[f"user-{i}-a", f"user-{i}-b"],
                datasets=[f"dataset-{i}"],
            )
            configs.append(repo.create(config))

        # Simulate concurrent usage tracking
        for i in range(CONCURRENT_CONFIGS_COUNT):
            for j in range(REQUESTS_PER_CONFIG):  # 5 requests per config
                user = f"user-{i}-a" if j % 2 == 0 else f"user-{i}-b"
                tracker.track_usage(
                    api_config_id=f"concurrent-{i}",
                    user_id=user,
                    input_prompt=f"Concurrent request {j}",
                    output_prompt=f"Concurrent response {j}",
                )

        # Verify all operations succeeded
        all_configs = repo.get_all()
        assert len(all_configs) == CONCURRENT_CONFIGS_COUNT

        all_metrics = tracker.get_all_metrics()
        assert len(all_metrics) == CONCURRENT_CONFIGS_COUNT

        for metrics in all_metrics:
            assert metrics.total_requests == REQUESTS_PER_CONFIG

    def test_data_persistence_across_restarts(self, temp_paths: dict[str, str]) -> None:
        """Test that data persists when components are recreated."""
        # Phase 1: Create initial data
        repo1 = APIConfigRepository(database_path=temp_paths["configs"])

        # Create and configure tracker1
        APIConfigUsageTracker._instance = None
        tracker1 = APIConfigUsageTracker()
        tracker1.database_path = temp_paths["usage"]
        tracker1.logs_path = Path(temp_paths["usage"]) / "logs"
        tracker1.metrics_path = Path(temp_paths["usage"]) / "metrics"
        tracker1.logs_path.mkdir(parents=True, exist_ok=True)
        tracker1.metrics_path.mkdir(parents=True, exist_ok=True)

        config = APIConfig(
            config_id="persistent-001", users=["user1", "user2"], datasets=["dataset1"]
        )
        repo1.create(config)

        tracker1.track_usage(
            api_config_id="persistent-001",
            user_id="user1",
            input_prompt="Test persistence",
            output_prompt="Response",
        )

        # Phase 2: Recreate components (simulate restart)
        APIConfigUsageTracker._instance = None  # Reset singleton

        repo2 = APIConfigRepository(database_path=temp_paths["configs"])

        # Create and configure tracker2
        tracker2 = APIConfigUsageTracker()
        tracker2.database_path = temp_paths["usage"]
        tracker2.logs_path = Path(temp_paths["usage"]) / "logs"
        tracker2.metrics_path = Path(temp_paths["usage"]) / "metrics"

        # Verify data persisted
        loaded_config = repo2.get_by_id("persistent-001")
        assert loaded_config is not None
        assert loaded_config.users == ["user1", "user2"]

        metrics = tracker2.get_metrics("persistent-001")
        assert metrics is not None
        assert metrics.total_requests == 1

        # Continue operations
        tracker2.track_usage(
            api_config_id="persistent-001",
            user_id="user2",
            input_prompt="After restart",
            output_prompt="Still working",
        )

        metrics = tracker2.get_metrics("persistent-001")
        assert metrics.total_requests == EXPECTED_TOTAL_REQUESTS_AFTER_RESTART

    def test_large_scale_operations(self, integrated_system: dict) -> None:
        """Test system performance with large-scale data."""
        repo = integrated_system["repository"]
        tracker = integrated_system["usage_tracker"]

        # Create configuration with many users and datasets
        large_config = APIConfig(
            config_id="large-scale-001",
            users=[f"user-{i}" for i in range(LARGE_SCALE_USERS_COUNT)],
            datasets=[f"dataset-{i}" for i in range(LARGE_SCALE_DATASETS_COUNT)],
        )
        repo.create(large_config)

        # Track many usage events
        for i in range(LARGE_SCALE_REQUESTS_COUNT):
            user_id = f"user-{i % LARGE_SCALE_USERS_COUNT}"
            tracker.track_usage(
                api_config_id="large-scale-001",
                user_id=user_id,
                input_prompt=f"Large scale test input {i} " * 20,  # Long prompt
                output_prompt=f"Large scale test output {i} " * 30,  # Longer output
            )

        # Verify system handles large data correctly
        config = repo.get_by_id("large-scale-001")
        assert len(config.users) == LARGE_SCALE_USERS_COUNT
        assert len(config.datasets) == LARGE_SCALE_DATASETS_COUNT

        metrics = tracker.get_metrics("large-scale-001")
        assert metrics.total_requests == LARGE_SCALE_REQUESTS_COUNT

        # Test pagination with large dataset
        logs_page1 = tracker.get_usage_logs(
            "large-scale-001", limit=PAGINATION_LIMIT, offset=0
        )
        logs_page2 = tracker.get_usage_logs(
            "large-scale-001", limit=PAGINATION_LIMIT, offset=PAGINATION_OFFSET
        )

        assert len(logs_page1) == PAGINATION_LIMIT
        assert len(logs_page2) == PAGINATION_LIMIT
        assert logs_page1[0].log_id != logs_page2[0].log_id

    def test_error_recovery_scenarios(self, integrated_system: dict) -> None:
        """Test system recovery from various error scenarios."""
        repo = integrated_system["repository"]
        tracker = integrated_system["usage_tracker"]

        # Create valid configuration
        config = APIConfig(config_id="error-test-001")
        repo.create(config)

        # Test tracking with very large prompts (potential memory issue)
        huge_prompt = "x" * 1_000_000  # 1MB of text
        log = tracker.track_usage(
            api_config_id="error-test-001",
            user_id="stress-tester",
            input_prompt=huge_prompt,
            output_prompt="Response to huge input",
        )

        assert log is not None
        assert log.input_word_count == 1  # One giant "word"

        # Test repository operations with corrupted data
        config_path = Path(repo.database_path) / "error-test-001.json"
        config_path.write_text('{"invalid": json content}')

        # Repository should handle corrupted file
        with pytest.raises(Exception, match=".*"):  # JSONDecodeError or similar
            repo.get_by_id("error-test-001")

        # Other operations should still work
        new_config = APIConfig(config_id="error-test-002")
        created = repo.create(new_config)
        assert created is not None

    def test_usage_analytics_queries(self, integrated_system: dict) -> None:
        """Test complex analytics queries across the system."""
        repo = integrated_system["repository"]
        tracker = integrated_system["usage_tracker"]

        # Set up test data
        configs = [
            APIConfig(config_id="analytics-1", users=["alice", "bob"]),
            APIConfig(config_id="analytics-2", users=["charlie", "david"]),
        ]

        for config in configs:
            repo.create(config)

        # Generate usage patterns
        usage_patterns = [
            ("analytics-1", "alice", ANALYTICS_ALICE_COUNT),
            ("analytics-1", "bob", ANALYTICS_BOB_COUNT),
            ("analytics-2", "charlie", ANALYTICS_CHARLIE_COUNT),
            ("analytics-2", "david", ANALYTICS_DAVID_COUNT),
        ]

        for config_id, user_id, count in usage_patterns:
            for _ in range(count):
                tracker.track_usage(
                    api_config_id=config_id,
                    user_id=user_id,
                    input_prompt="Analytics test",
                    output_prompt="Response",
                )

        # Test top users functionality
        top_users_1 = tracker.get_top_users("analytics-1", limit=10)
        assert top_users_1[0] == ("alice", ANALYTICS_ALICE_COUNT)
        assert top_users_1[1] == ("bob", ANALYTICS_BOB_COUNT)

        top_users_2 = tracker.get_top_users("analytics-2", limit=1)
        assert len(top_users_2) == 1
        assert top_users_2[0] == ("charlie", ANALYTICS_CHARLIE_COUNT)

        # Test user frequency across configs
        freq_1 = tracker.get_user_frequency("analytics-1")
        freq_2 = tracker.get_user_frequency("analytics-2")

        assert sum(freq_1.values()) == ANALYTICS_TOTAL_CONFIG1  # 15 + 8
        assert sum(freq_2.values()) == ANALYTICS_TOTAL_CONFIG2  # 20 + 5
