"""Unit tests for api_configs.usage_tracker module."""

from datetime import datetime
from pathlib import Path

import pytest

from api_configs.usage_tracker import (
    APIConfigMetrics,
    APIConfigUsageLog,
    APIConfigUsageTracker,
)

# Constants for test values
WORD_COUNT_THREE = 3
WORD_COUNT_TWO = 2
DATETIME_TEST_YEAR = 2024
TEST_REQUESTS_TEN = 10
TEST_INPUT_WORD_COUNT_100 = 100
TEST_OUTPUT_WORD_COUNT_200 = 200
TEST_REQUESTS_25 = 25
TEST_INPUT_WORD_COUNT_500 = 500
TEST_OUTPUT_WORD_COUNT_750 = 750
LARGE_INPUT_WORD_COUNT = 1000
LARGE_OUTPUT_WORD_COUNT = 500
METRICS_TOTAL_REQUESTS = 3
METRICS_TOTAL_WORD_COUNT = 6
LOGS_COUNT_FIVE = 5
LOGS_COUNT_TWENTY = 20
USER1_USAGE_COUNT = 10
USER2_USAGE_COUNT = 7
USER3_USAGE_COUNT = 5
USER4_USAGE_COUNT = 3
TOP_USERS_LIMIT = 3
CONCURRENT_REQUESTS = 50
DIFFERENT_USERS = 5


class TestAPIConfigUsageLog:
    """Test suite for APIConfigUsageLog dataclass."""

    def test_usage_log_creation(self) -> None:
        """Test creating a usage log with all fields."""
        log = APIConfigUsageLog(
            api_config_id="config-123",
            user_id="user-456",
            input_prompt="Test input prompt",
            output_prompt="Test output prompt",
            input_word_count=WORD_COUNT_THREE,
            output_word_count=WORD_COUNT_THREE,
        )

        assert log.api_config_id == "config-123"
        assert log.user_id == "user-456"
        assert log.input_prompt == "Test input prompt"
        assert log.output_prompt == "Test output prompt"
        assert log.input_word_count == WORD_COUNT_THREE
        assert log.output_word_count == WORD_COUNT_THREE
        assert isinstance(log.log_id, str)
        assert isinstance(log.timestamp, datetime)

    def test_usage_log_to_dict(self) -> None:
        """Test converting usage log to dictionary."""
        log = APIConfigUsageLog(
            api_config_id="config-123",
            user_id="user-456",
            input_prompt="Input",
            output_prompt="Output",
            input_word_count=1,
            output_word_count=1,
        )

        result = log.to_dict()

        assert result["api_config_id"] == "config-123"
        assert result["user_id"] == "user-456"
        assert result["input_prompt"] == "Input"
        assert result["output_prompt"] == "Output"
        assert result["input_word_count"] == 1
        assert result["output_word_count"] == 1
        assert "id" in result
        assert "timestamp" in result

    def test_usage_log_from_dict(self) -> None:
        """Test creating usage log from dictionary."""
        data = {
            "api_config_id": "config-789",
            "user_id": "user-999",
            "input_prompt": "Test input",
            "output_prompt": "Test output",
            "input_word_count": 2,
            "output_word_count": 2,
            "id": "log-123",
            "timestamp": "2024-01-15T10:30:00",
        }

        log = APIConfigUsageLog.from_dict(data)

        assert log.api_config_id == "config-789"
        assert log.user_id == "user-999"
        assert log.log_id == "log-123"
        assert log.timestamp.year == DATETIME_TEST_YEAR

    def test_usage_log_from_dict_minimal(self) -> None:
        """Test creating usage log from minimal dictionary."""
        data = {"api_config_id": "config-minimal", "user_id": "user-minimal"}

        log = APIConfigUsageLog.from_dict(data)

        assert log.api_config_id == "config-minimal"
        assert log.user_id == "user-minimal"
        assert log.input_prompt == ""
        assert log.output_prompt == ""
        assert log.input_word_count == 0
        assert log.output_word_count == 0


class TestAPIConfigMetrics:
    """Test suite for APIConfigMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Test creating metrics with default values."""
        metrics = APIConfigMetrics(api_config_id="config-123")

        assert metrics.api_config_id == "config-123"
        assert metrics.total_requests == 0
        assert metrics.total_input_word_count == 0
        assert metrics.total_output_word_count == 0
        assert metrics.user_frequency == {}
        assert isinstance(metrics.last_updated, datetime)

    def test_metrics_to_dict(self) -> None:
        """Test converting metrics to dictionary."""
        metrics = APIConfigMetrics(
            api_config_id="config-123",
            total_requests=TEST_REQUESTS_TEN,
            total_input_word_count=TEST_INPUT_WORD_COUNT_100,
            total_output_word_count=TEST_OUTPUT_WORD_COUNT_200,
            user_frequency={"user1": 5, "user2": 3, "user3": 2},
            user_input_words={"user1": 50, "user2": 30, "user3": 20},
            user_output_words={"user1": 100, "user2": 60, "user3": 40},
        )

        result = metrics.to_dict()

        assert result["api_config_id"] == "config-123"
        assert result["total_requests"] == TEST_REQUESTS_TEN
        assert result["total_input_word_count"] == TEST_INPUT_WORD_COUNT_100
        assert result["total_output_word_count"] == TEST_OUTPUT_WORD_COUNT_200
        assert result["user_frequency"] == {"user1": 5, "user2": 3, "user3": 2}
        assert result["user_input_words"] == {"user1": 50, "user2": 30, "user3": 20}
        assert result["user_output_words"] == {"user1": 100, "user2": 60, "user3": 40}
        assert "last_updated" in result

    def test_metrics_from_dict(self) -> None:
        """Test creating metrics from dictionary."""
        data = {
            "api_config_id": "config-456",
            "total_requests": TEST_REQUESTS_25,
            "total_input_word_count": TEST_INPUT_WORD_COUNT_500,
            "total_output_word_count": TEST_OUTPUT_WORD_COUNT_750,
            "user_frequency": {"userA": 15, "userB": 10},
            "user_input_words": {"userA": 300, "userB": 200},
            "user_output_words": {"userA": 450, "userB": 300},
            "last_updated": "2024-01-15T12:00:00",
        }

        metrics = APIConfigMetrics.from_dict(data)

        assert metrics.api_config_id == "config-456"
        assert metrics.total_requests == TEST_REQUESTS_25
        assert metrics.total_input_word_count == TEST_INPUT_WORD_COUNT_500
        assert metrics.total_output_word_count == TEST_OUTPUT_WORD_COUNT_750
        assert metrics.user_frequency == {"userA": 15, "userB": 10}
        assert metrics.user_input_words == {"userA": 300, "userB": 200}
        assert metrics.user_output_words == {"userA": 450, "userB": 300}


class TestAPIConfigUsageTracker:
    """Test suite for APIConfigUsageTracker."""

    @pytest.fixture()
    def temp_db_path(self, tmp_path: Path) -> str:
        """Create a temporary database path for testing."""
        db_path = tmp_path / "test_api_usage"
        return str(db_path)

    @pytest.fixture()
    def tracker(self, temp_db_path: str) -> APIConfigUsageTracker:
        """Create a tracker instance with temporary storage."""
        # Reset singleton instance for each test
        APIConfigUsageTracker._instance = None
        tracker = APIConfigUsageTracker()
        tracker.database_path = temp_db_path
        tracker.logs_path = Path(temp_db_path) / "logs"
        tracker.metrics_path = Path(temp_db_path) / "metrics"
        tracker.logs_path.mkdir(parents=True, exist_ok=True)
        tracker.metrics_path.mkdir(parents=True, exist_ok=True)
        return tracker

    def test_singleton_pattern(self) -> None:
        """Test that APIConfigUsageTracker follows singleton pattern."""
        # Reset singleton
        APIConfigUsageTracker._instance = None

        tracker1 = APIConfigUsageTracker()
        tracker2 = APIConfigUsageTracker()

        assert tracker1 is tracker2

    def test_tracker_initialization(self) -> None:
        """Test tracker initialization creates necessary directories."""
        APIConfigUsageTracker._instance = None
        tracker = APIConfigUsageTracker()

        # The default paths should be created
        default_logs_path = Path(tracker.logs_path)
        default_metrics_path = Path(tracker.metrics_path)

        assert default_logs_path.exists()
        assert default_logs_path.is_dir()
        assert default_metrics_path.exists()
        assert default_metrics_path.is_dir()

    def test_track_usage_basic(self, tracker: APIConfigUsageTracker) -> None:
        """Test basic usage tracking."""
        log = tracker.track_usage(
            api_config_id="config-123",
            user_id="user-456",
            input_prompt="Hello world",
            output_prompt="Hi there",
        )

        assert log.api_config_id == "config-123"
        assert log.user_id == "user-456"
        assert log.input_prompt == "Hello world"
        assert log.output_prompt == "Hi there"
        assert log.input_word_count == WORD_COUNT_TWO  # "Hello world" = 2 words
        assert log.output_word_count == WORD_COUNT_TWO  # "Hi there" = 2 words

    def test_track_usage_empty_prompts(self, tracker: APIConfigUsageTracker) -> None:
        """Test tracking with empty prompts."""
        log = tracker.track_usage(
            api_config_id="config-123",
            user_id="user-456",
            input_prompt="",
            output_prompt="",
        )

        assert log.input_word_count == 0
        assert log.output_word_count == 0

    def test_track_usage_large_prompts(self, tracker: APIConfigUsageTracker) -> None:
        """Test tracking with large prompts."""
        large_input = " ".join([f"word{i}" for i in range(LARGE_INPUT_WORD_COUNT)])
        large_output = " ".join(
            [f"response{i}" for i in range(LARGE_OUTPUT_WORD_COUNT)]
        )

        log = tracker.track_usage(
            api_config_id="config-123",
            user_id="user-456",
            input_prompt=large_input,
            output_prompt=large_output,
        )

        assert log.input_word_count == LARGE_INPUT_WORD_COUNT
        assert log.output_word_count == LARGE_OUTPUT_WORD_COUNT

    def test_metrics_creation_on_first_usage(
        self, tracker: APIConfigUsageTracker
    ) -> None:
        """Test that metrics are created on first usage."""
        tracker.track_usage(
            api_config_id="new-config",
            user_id="user-1",
            input_prompt="Test input",
            output_prompt="Test output",
        )

        metrics = tracker.get_metrics("new-config")

        assert metrics is not None
        assert metrics.total_requests == 1
        assert metrics.total_input_word_count == WORD_COUNT_TWO
        assert metrics.total_output_word_count == WORD_COUNT_TWO
        assert metrics.user_frequency == {"user-1": 1}
        assert metrics.user_input_words == {"user-1": WORD_COUNT_TWO}
        assert metrics.user_output_words == {"user-1": WORD_COUNT_TWO}

    def test_metrics_update_on_subsequent_usage(
        self, tracker: APIConfigUsageTracker
    ) -> None:
        """Test that metrics are updated correctly on subsequent usage."""
        # First usage
        tracker.track_usage(
            api_config_id="config-123",
            user_id="user-1",
            input_prompt="First input",
            output_prompt="First output",
        )

        # Second usage by same user
        tracker.track_usage(
            api_config_id="config-123",
            user_id="user-1",
            input_prompt="Second input",
            output_prompt="Second output",
        )

        # Third usage by different user
        tracker.track_usage(
            api_config_id="config-123",
            user_id="user-2",
            input_prompt="Third input",
            output_prompt="Third output",
        )

        metrics = tracker.get_metrics("config-123")

        assert metrics.total_requests == METRICS_TOTAL_REQUESTS
        assert metrics.total_input_word_count == METRICS_TOTAL_WORD_COUNT  # 2 + 2 + 2
        assert metrics.total_output_word_count == METRICS_TOTAL_WORD_COUNT  # 2 + 2 + 2
        assert metrics.user_frequency == {"user-1": 2, "user-2": 1}
        assert metrics.user_input_words == {
            "user-1": 4,
            "user-2": 2,
        }  # 2 + 2 for user-1, 2 for user-2
        assert metrics.user_output_words == {
            "user-1": 4,
            "user-2": 2,
        }  # 2 + 2 for user-1, 2 for user-2

    def test_get_metrics_non_existing(self, tracker: APIConfigUsageTracker) -> None:
        """Test getting metrics for non-existing config returns None."""
        metrics = tracker.get_metrics("non-existent")
        assert metrics is None

    def test_get_all_metrics(self, tracker: APIConfigUsageTracker) -> None:
        """Test getting all metrics."""
        # Track usage for multiple configs
        tracker.track_usage("config-1", "user-1", "input1", "output1")
        tracker.track_usage("config-2", "user-2", "input2", "output2")
        tracker.track_usage("config-3", "user-3", "input3", "output3")

        all_metrics = tracker.get_all_metrics()

        assert len(all_metrics) == METRICS_TOTAL_REQUESTS
        config_ids = {m.api_config_id for m in all_metrics}
        assert config_ids == {"config-1", "config-2", "config-3"}

    def test_get_usage_logs(self, tracker: APIConfigUsageTracker) -> None:
        """Test retrieving usage logs for a specific config."""
        # Create multiple logs
        for i in range(LOGS_COUNT_FIVE):
            tracker.track_usage(
                api_config_id="config-123",
                user_id=f"user-{i}",
                input_prompt=f"Input {i}",
                output_prompt=f"Output {i}",
            )

        logs = tracker.get_usage_logs("config-123")

        assert len(logs) == LOGS_COUNT_FIVE
        # Should be sorted by timestamp descending (most recent first)
        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp

    def test_get_usage_logs_pagination(self, tracker: APIConfigUsageTracker) -> None:
        """Test pagination of usage logs."""
        # Create 20 logs
        for i in range(LOGS_COUNT_TWENTY):
            tracker.track_usage(
                api_config_id="config-123",
                user_id="user-1",
                input_prompt=f"Input {i}",
                output_prompt=f"Output {i}",
            )

        # Test limit
        logs_limited = tracker.get_usage_logs("config-123", limit=LOGS_COUNT_FIVE)
        assert len(logs_limited) == LOGS_COUNT_FIVE

        # Test offset
        logs_offset = tracker.get_usage_logs(
            "config-123", limit=LOGS_COUNT_FIVE, offset=LOGS_COUNT_FIVE
        )
        assert len(logs_offset) == LOGS_COUNT_FIVE

        # Verify no overlap
        limited_prompts = {log.input_prompt for log in logs_limited}
        offset_prompts = {log.input_prompt for log in logs_offset}
        assert limited_prompts.isdisjoint(offset_prompts)

    def test_get_usage_logs_empty(self, tracker: APIConfigUsageTracker) -> None:
        """Test getting logs for config with no usage."""
        logs = tracker.get_usage_logs("no-usage-config")
        assert logs == []

    def test_get_top_users(self, tracker: APIConfigUsageTracker) -> None:
        """Test getting top users for a config."""
        # Create usage with different frequencies
        for _ in range(USER1_USAGE_COUNT):
            tracker.track_usage("config-123", "user-1", "input", "output")
        for _ in range(USER2_USAGE_COUNT):
            tracker.track_usage("config-123", "user-2", "input", "output")
        for _ in range(USER3_USAGE_COUNT):
            tracker.track_usage("config-123", "user-3", "input", "output")
        for _ in range(USER4_USAGE_COUNT):
            tracker.track_usage("config-123", "user-4", "input", "output")

        top_users = tracker.get_top_users("config-123", limit=TOP_USERS_LIMIT)

        assert len(top_users) == TOP_USERS_LIMIT
        assert top_users[0] == ("user-1", USER1_USAGE_COUNT)
        assert top_users[1] == ("user-2", USER2_USAGE_COUNT)
        assert top_users[2] == ("user-3", USER3_USAGE_COUNT)

    def test_get_top_users_empty(self, tracker: APIConfigUsageTracker) -> None:
        """Test getting top users for non-existent config."""
        top_users = tracker.get_top_users("non-existent")
        assert top_users == []

    def test_get_user_frequency(self, tracker: APIConfigUsageTracker) -> None:
        """Test getting user frequency map."""
        tracker.track_usage("config-123", "user-1", "input", "output")
        tracker.track_usage("config-123", "user-1", "input", "output")
        tracker.track_usage("config-123", "user-2", "input", "output")

        frequency = tracker.get_user_frequency("config-123")

        assert frequency == {"user-1": 2, "user-2": 1}

    def test_error_handling_in_track_usage(
        self, tracker: APIConfigUsageTracker
    ) -> None:
        """Test error handling during usage tracking."""
        # Make logs_path read-only to trigger an error
        logs_path = Path(tracker.logs_path)
        logs_path.chmod(0o444)

        try:
            # Should still return a log even if saving fails
            log = tracker.track_usage(
                api_config_id="config-123",
                user_id="user-456",
                input_prompt="Test",
                output_prompt="Test",
            )

            assert log is not None
            assert log.api_config_id == "config-123"
        finally:
            # Restore permissions
            logs_path.chmod(0o755)

    def test_corrupted_metrics_file(self, tracker: APIConfigUsageTracker) -> None:
        """Test handling of corrupted metrics file."""
        # Create valid metrics first
        tracker.track_usage("config-123", "user-1", "input", "output")

        # Corrupt the metrics file
        metrics_file = Path(tracker.metrics_path) / "config-123.json"
        metrics_file.write_text("{ invalid json }")

        # Should return None for corrupted file
        metrics = tracker.get_metrics("config-123")
        assert metrics is None

    def test_concurrent_tracking_simulation(
        self, tracker: APIConfigUsageTracker
    ) -> None:
        """Test simulated concurrent usage tracking."""
        # Simulate multiple rapid usage tracking calls
        for i in range(CONCURRENT_REQUESTS):
            tracker.track_usage(
                api_config_id="config-concurrent",
                user_id=f"user-{i % DIFFERENT_USERS}",  # 5 different users
                input_prompt=f"Concurrent input {i}",
                output_prompt=f"Concurrent output {i}",
            )

        metrics = tracker.get_metrics("config-concurrent")
        assert metrics.total_requests == CONCURRENT_REQUESTS
        assert len(metrics.user_frequency) == DIFFERENT_USERS
        assert sum(metrics.user_frequency.values()) == CONCURRENT_REQUESTS
