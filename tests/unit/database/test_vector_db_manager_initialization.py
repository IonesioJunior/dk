"""Unit tests for VectorDBManager initialization."""

from unittest.mock import MagicMock, patch

import pytest

from database.vector_db_manager import VectorDBManager


class TestVectorDBManagerInitialization:
    """Test suite for VectorDBManager initialization."""

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    @patch("database.vector_db_manager.Path.mkdir")
    def test_client_initialization_success(
        self, mock_mkdir: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test successful ChromaDB client initialization."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.list_collections.return_value = []

        # Create manager
        manager = VectorDBManager()

        # Verify directory creation
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify client creation with correct path
        mock_client.assert_called_once()
        call_args = mock_client.call_args[1]
        assert "path" in call_args
        assert call_args["path"].endswith("cache/vectordb")

        # Verify client is set
        assert manager._client is mock_client_instance

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    def test_client_initialization_failure(self, mock_client: MagicMock) -> None:
        """Test handling of ChromaDB initialization failures."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mock to raise exception
        mock_client.side_effect = Exception("Connection failed")

        # Attempt to create manager should raise exception
        with pytest.raises(Exception, match="Connection failed"):
            VectorDBManager()

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    @patch("database.vector_db_manager.Path")
    def test_cache_directory_creation(
        self, mock_path_class: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test that cache/vectordb directory is created if it doesn't exist."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mocks
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
        mock_path_instance.resolve.return_value.parent.parent = mock_path_instance

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.list_collections.return_value = []

        # Create manager
        VectorDBManager()

        # Verify mkdir was called
        mock_path_instance.mkdir.assert_called_with(parents=True, exist_ok=True)

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    def test_default_collections_creation(self, mock_client: MagicMock) -> None:
        """Test that default 'documents' collection is created on init."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.list_collections.return_value = (
            []
        )  # No existing collections
        mock_collection = MagicMock()
        mock_client_instance.create_collection.return_value = mock_collection

        # Create manager
        VectorDBManager()

        # Verify documents collection was created
        mock_client_instance.create_collection.assert_called_once_with(
            name="documents",
            metadata={"description": "Collection for storing documents"},
        )

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    def test_default_collections_already_exist(self, mock_client: MagicMock) -> None:
        """Test behavior when default collections already exist."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.list_collections.return_value = [
            "documents"
        ]  # Collection exists

        # Create manager
        VectorDBManager()

        # Verify create_collection was NOT called
        mock_client_instance.create_collection.assert_not_called()

    @patch("database.vector_db_manager.logger")
    @patch("database.vector_db_manager.chromadb.PersistentClient")
    def test_initialization_error_propagation(
        self, mock_client: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that initialization errors are properly logged and raised."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mock to raise exception
        error_message = "Database connection failed"
        mock_client.side_effect = Exception(error_message)

        # Attempt to create manager
        with pytest.raises(Exception, match=error_message):
            VectorDBManager()

        # Verify error was logged
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to initialize ChromaDB client" in error_call
        assert error_message in error_call

    @patch("database.vector_db_manager.chromadb.PersistentClient")
    def test_initialization_idempotency(self, mock_client: MagicMock) -> None:
        """Test that initialization is idempotent."""
        # Clear any existing instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Configure mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.list_collections.return_value = ["documents"]

        # Create manager multiple times
        manager1 = VectorDBManager()
        manager2 = VectorDBManager()
        manager3 = VectorDBManager()

        # Client should only be created once
        mock_client.assert_called_once()

        # All managers should share the same client
        assert manager1._client is manager2._client is manager3._client
