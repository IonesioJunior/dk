"""Unit tests for VectorDBManager singleton pattern."""

import threading
from unittest.mock import MagicMock, patch

from database.vector_db_manager import VectorDBManager


class TestVectorDBManagerSingleton:
    """Test suite for VectorDBManager singleton pattern implementation."""

    def test_singleton_instance_creation(self) -> None:
        """Test that VectorDBManager always returns the same instance."""
        manager1 = VectorDBManager()
        manager2 = VectorDBManager()

        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_singleton_thread_safety(self) -> None:
        """Test singleton pattern is thread-safe with concurrent access."""
        instances: list[VectorDBManager] = []

        def create_instance() -> None:
            instance = VectorDBManager()
            instances.append(instance)

        # Create multiple threads that try to create instances
        threads = [threading.Thread(target=create_instance) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len({id(inst) for inst in instances}) == 1
        assert all(inst is instances[0] for inst in instances)

    def test_singleton_persistence_across_imports(self) -> None:
        """Test that singleton persists across different module imports."""
        # This would typically be tested across different modules
        # For demonstration, we're testing within the same module

        # Clear the singleton instance
        VectorDBManager._instance = None

        # Create first instance
        manager1 = VectorDBManager()
        instance_id = id(manager1)

        # Simulate module reload by clearing and recreating
        manager2 = VectorDBManager()

        assert id(manager2) == instance_id

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    def test_singleton_with_mocked_client(self, mock_client: MagicMock) -> None:
        """Test singleton behavior with mocked ChromaDB client."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mock
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        # Create instances
        manager1 = VectorDBManager()
        manager2 = VectorDBManager()

        # Verify singleton behavior
        assert manager1 is manager2

        # Verify client was only created once
        mock_client.assert_called_once()

    def test_singleton_state_persistence(self) -> None:
        """Test that singleton maintains state across instances."""
        # This test verifies that any state changes in one reference
        # are reflected in all references to the singleton

        manager1 = VectorDBManager()
        manager2 = VectorDBManager()

        # Both should reference the same client
        assert manager1._client is manager2._client
