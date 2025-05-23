"""Unit tests for api_configs.repository module."""

import json
from pathlib import Path

import pytest

from api_configs.models import APIConfig, APIConfigUpdate
from api_configs.repository import APIConfigRepository

# Constants for test values
MULTIPLE_CONFIGS_COUNT = 5
CONCURRENT_CONFIGS_COUNT = 10
LARGE_DATA_COUNT = 1000


class TestAPIConfigRepository:
    """Test suite for APIConfigRepository."""

    @pytest.fixture()
    def temp_db_path(self, tmp_path: Path) -> str:
        """Create a temporary database path for testing."""
        db_path = tmp_path / "test_api_configs"
        return str(db_path)

    @pytest.fixture()
    def repository(self, temp_db_path: str) -> APIConfigRepository:
        """Create a repository instance with temporary storage."""
        return APIConfigRepository(database_path=temp_db_path)

    @pytest.fixture()
    def sample_config(self) -> APIConfig:
        """Create a sample API configuration for testing."""
        return APIConfig(
            config_id="test-config-123",
            users=["user1", "user2"],
            datasets=["dataset1", "dataset2", "dataset3"],
        )

    def test_repository_initialization(self, temp_db_path: str) -> None:
        """Test repository initialization creates directory."""
        APIConfigRepository(database_path=temp_db_path)

        assert Path(temp_db_path).exists()
        assert Path(temp_db_path).is_dir()

    def test_repository_nested_directory_creation(self, tmp_path: Path) -> None:
        """Test repository creates nested directories if needed."""
        nested_path = tmp_path / "deeply" / "nested" / "path"
        APIConfigRepository(database_path=str(nested_path))

        assert nested_path.exists()
        assert nested_path.is_dir()

    def test_create_api_config(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test creating a new API configuration."""
        created = repository.create(sample_config)

        assert created.config_id == sample_config.config_id
        assert created.users == sample_config.users
        assert created.datasets == sample_config.datasets

        # Verify file was created
        file_path = Path(repository.database_path) / f"{sample_config.config_id}.json"
        assert file_path.exists()

        # Verify index was updated
        index_path = Path(repository.database_path) / "_index.json"
        assert index_path.exists()
        with index_path.open() as f:
            index = json.load(f)
        assert sample_config.config_id in index

    def test_get_by_id_existing(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test retrieving an existing API configuration by ID."""
        repository.create(sample_config)

        retrieved = repository.get_by_id(sample_config.config_id)

        assert retrieved is not None
        assert retrieved.config_id == sample_config.config_id
        assert retrieved.users == sample_config.users
        assert retrieved.datasets == sample_config.datasets

    def test_get_by_id_non_existing(self, repository: APIConfigRepository) -> None:
        """Test retrieving a non-existent API configuration returns None."""
        result = repository.get_by_id("non-existent-id")
        assert result is None

    def test_get_all_empty(self, repository: APIConfigRepository) -> None:
        """Test get_all returns empty list when no configs exist."""
        configs = repository.get_all()
        assert configs == []

    def test_get_all_with_configs(self, repository: APIConfigRepository) -> None:
        """Test get_all returns all stored configurations."""
        # Create multiple configs
        configs = [
            APIConfig(
                config_id=f"config-{i}", users=[f"user{i}"], datasets=[f"dataset{i}"]
            )
            for i in range(MULTIPLE_CONFIGS_COUNT)
        ]

        for config in configs:
            repository.create(config)

        retrieved = repository.get_all()

        assert len(retrieved) == MULTIPLE_CONFIGS_COUNT
        retrieved_ids = {config.config_id for config in retrieved}
        expected_ids = {config.config_id for config in configs}
        assert retrieved_ids == expected_ids

    def test_update_users_only(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test updating only users field."""
        repository.create(sample_config)
        original_updated_at = sample_config.updated_at

        update = APIConfigUpdate(users=["new_user1", "new_user2", "new_user3"])
        updated = repository.update(sample_config.config_id, update)

        assert updated is not None
        assert updated.users == ["new_user1", "new_user2", "new_user3"]
        assert updated.datasets == sample_config.datasets  # Unchanged
        assert updated.updated_at > original_updated_at

    def test_update_datasets_only(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test updating only datasets field."""
        repository.create(sample_config)

        update = APIConfigUpdate(datasets=["new_dataset1"])
        updated = repository.update(sample_config.config_id, update)

        assert updated is not None
        assert updated.users == sample_config.users  # Unchanged
        assert updated.datasets == ["new_dataset1"]

    def test_update_both_fields(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test updating both users and datasets fields."""
        repository.create(sample_config)

        update = APIConfigUpdate(users=[], datasets=["dataset1", "dataset2"])
        updated = repository.update(sample_config.config_id, update)

        assert updated is not None
        assert updated.users == []
        assert updated.datasets == ["dataset1", "dataset2"]

    def test_update_non_existing(self, repository: APIConfigRepository) -> None:
        """Test updating non-existent config returns None."""
        update = APIConfigUpdate(users=["user1"])
        result = repository.update("non-existent-id", update)
        assert result is None

    def test_update_persisted_to_file(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test that updates are persisted to file."""
        repository.create(sample_config)

        update = APIConfigUpdate(users=["updated_user"])
        repository.update(sample_config.config_id, update)

        # Read directly from file
        file_path = Path(repository.database_path) / f"{sample_config.config_id}.json"
        with file_path.open() as f:
            data = json.load(f)

        assert data["users"] == ["updated_user"]

    def test_delete_existing(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test deleting an existing configuration."""
        repository.create(sample_config)

        result = repository.delete(sample_config.config_id)

        assert result is True

        # Verify file was deleted
        file_path = Path(repository.database_path) / f"{sample_config.config_id}.json"
        assert not file_path.exists()

        # Verify index was updated
        index_path = Path(repository.database_path) / "_index.json"
        with index_path.open() as f:
            index = json.load(f)
        assert sample_config.config_id not in index

        # Verify get_by_id returns None
        assert repository.get_by_id(sample_config.config_id) is None

    def test_delete_non_existing(self, repository: APIConfigRepository) -> None:
        """Test deleting non-existent config returns False."""
        result = repository.delete("non-existent-id")
        assert result is False

    def test_index_consistency_after_multiple_operations(
        self, repository: APIConfigRepository
    ) -> None:
        """Test index remains consistent after multiple operations."""
        # Create configs
        config1 = APIConfig(config_id="config-1")
        config2 = APIConfig(config_id="config-2")
        config3 = APIConfig(config_id="config-3")

        repository.create(config1)
        repository.create(config2)
        repository.create(config3)

        # Delete one
        repository.delete("config-2")

        # Check index
        all_configs = repository.get_all()
        config_ids = {config.config_id for config in all_configs}
        assert config_ids == {"config-1", "config-3"}

    def test_corrupted_json_handling(
        self, repository: APIConfigRepository, sample_config: APIConfig
    ) -> None:
        """Test handling of corrupted JSON files."""
        repository.create(sample_config)

        # Corrupt the file
        file_path = Path(repository.database_path) / f"{sample_config.config_id}.json"
        with file_path.open("w") as f:
            f.write("{ invalid json }")

        # Should handle gracefully
        with pytest.raises(json.JSONDecodeError):
            repository.get_by_id(sample_config.config_id)

    def test_missing_index_file_recovery(self, repository: APIConfigRepository) -> None:
        """Test repository handles missing index file gracefully."""
        # Create configs
        config1 = APIConfig(config_id="config-1")
        repository.create(config1)

        # Delete index file
        index_path = Path(repository.database_path) / "_index.json"
        index_path.unlink()

        # Should return empty list since index is missing
        configs = repository.get_all()
        assert configs == []

    def test_empty_index_file(self, repository: APIConfigRepository) -> None:
        """Test handling of empty index file."""
        index_path = Path(repository.database_path) / "_index.json"
        index_path.write_text("[]")

        configs = repository.get_all()
        assert configs == []

    def test_index_with_missing_files(self, repository: APIConfigRepository) -> None:
        """Test index pointing to missing files."""
        # Create index with non-existent config IDs
        index_path = Path(repository.database_path) / "_index.json"
        with index_path.open("w") as f:
            json.dump(["missing-1", "missing-2"], f)

        configs = repository.get_all()
        assert configs == []  # Should skip missing files

    def test_concurrent_access_simulation(
        self, repository: APIConfigRepository
    ) -> None:
        """Test simulated concurrent access patterns."""
        # Create multiple configs rapidly
        configs = []
        for i in range(CONCURRENT_CONFIGS_COUNT):
            config = APIConfig(config_id=f"concurrent-{i}")
            configs.append(repository.create(config))

        # Verify all were created
        all_configs = repository.get_all()
        assert len(all_configs) == CONCURRENT_CONFIGS_COUNT

    def test_large_data_handling(self, repository: APIConfigRepository) -> None:
        """Test handling of configurations with large data."""
        # Create config with many users and datasets
        large_config = APIConfig(
            config_id="large-config",
            users=[f"user_{i}" for i in range(LARGE_DATA_COUNT)],
            datasets=[f"dataset_{i}" for i in range(LARGE_DATA_COUNT)],
        )

        repository.create(large_config)
        retrieved = repository.get_by_id("large-config")

        assert len(retrieved.users) == LARGE_DATA_COUNT
        assert len(retrieved.datasets) == LARGE_DATA_COUNT
        assert retrieved.users == large_config.users
        assert retrieved.datasets == large_config.datasets
