"""Unit tests for VectorDBManager collection operations."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from database.vector_db_manager import VectorDBManager


class TestCollectionOperations:
    """Test suite for collection CRUD operations."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        """Setup for each test."""
        # Clear singleton instance before each test
        VectorDBManager._instance = None
        VectorDBManager._client = None

    @pytest.fixture()
    def mock_manager(self) -> Generator[tuple[VectorDBManager, MagicMock], None, None]:
        """Fixture providing a mocked VectorDBManager."""
        with patch(
            "database.vector_db_manager.chromadb.PersistentClient"
        ) as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            mock_client_instance.list_collections.return_value = []

            manager = VectorDBManager()
            yield manager, mock_client_instance

    def test_create_collection_basic(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test creating a collection with just a name."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_client.create_collection.return_value = mock_collection

        # Create collection
        result = manager.create_collection("test_collection")

        # Verify client method was called correctly
        # The last call should be our test collection
        # (first might be the default documents collection)
        create_calls = mock_client.create_collection.call_args_list
        assert any(call == call(name="test_collection") for call in create_calls)

        # Verify return value
        assert result is mock_collection

    def test_create_collection_with_metadata(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test creating a collection with metadata."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_client.create_collection.return_value = mock_collection

        metadata = {"description": "Test collection", "version": "1.0"}

        # Create collection
        result = manager.create_collection("test_collection", metadata=metadata)

        # Verify client method was called with metadata
        create_calls = mock_client.create_collection.call_args_list
        assert any(
            call == call(name="test_collection", metadata=metadata)
            for call in create_calls
        )

        assert result is mock_collection

    def test_create_collection_with_embedding_function(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test creating a collection with custom embedding function."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_client.create_collection.return_value = mock_collection

        mock_embedding_fn = MagicMock()

        # Create collection
        result = manager.create_collection(
            "test_collection", embedding_function=mock_embedding_fn
        )

        # Verify client method was called with embedding function
        create_calls = mock_client.create_collection.call_args_list
        assert any(
            call == call(name="test_collection", embedding_function=mock_embedding_fn)
            for call in create_calls
        )

        assert result is mock_collection

    def test_create_collection_duplicate_name(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test creating a collection that already exists."""
        manager, mock_client = mock_manager

        # Configure mock to raise exception for duplicate
        mock_client.create_collection.side_effect = Exception(
            "Collection already exists"
        )

        # Attempt to create duplicate collection
        with pytest.raises(Exception, match="Collection already exists"):
            manager.create_collection("existing_collection")

    def test_get_collection_exists(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test getting an existing collection."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        # Get collection
        result = manager.get_collection("test_collection")

        # Verify client method was called
        mock_client.get_collection.assert_called_once_with(name="test_collection")

        # Verify return value
        assert result is mock_collection

    def test_get_collection_not_exists(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test getting a non-existent collection."""
        manager, mock_client = mock_manager

        # Configure mock to raise exception
        mock_client.get_collection.side_effect = Exception("Collection not found")

        # Attempt to get non-existent collection
        with pytest.raises(Exception, match="Collection not found"):
            manager.get_collection("non_existent")

    def test_get_or_create_collection_exists(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test get_or_create when collection exists."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Get or create collection
        result = manager.get_or_create_collection("test_collection")

        # Verify client method was called
        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_collection"
        )

        assert result is mock_collection

    def test_get_or_create_collection_with_metadata(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test get_or_create with metadata for new collection."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        metadata = {"type": "embeddings", "model": "test"}

        # Get or create collection
        result = manager.get_or_create_collection("test_collection", metadata=metadata)

        # Verify client method was called with metadata
        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_collection", metadata=metadata
        )

        assert result is mock_collection

    def test_delete_collection_exists(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test deleting an existing collection."""
        manager, mock_client = mock_manager

        # Delete collection
        manager.delete_collection("test_collection")

        # Verify client method was called
        mock_client.delete_collection.assert_called_once_with(name="test_collection")

    def test_delete_collection_not_exists(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test deleting a non-existent collection."""
        manager, mock_client = mock_manager

        # Configure mock to raise exception
        mock_client.delete_collection.side_effect = Exception("Collection not found")

        # Attempt to delete non-existent collection
        with pytest.raises(Exception, match="Collection not found"):
            manager.delete_collection("non_existent")

    def test_list_collections_empty(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test listing collections when database is empty."""
        manager, mock_client = mock_manager
        # Reset the mock to clear any calls from initialization
        mock_client.list_collections.reset_mock()
        mock_client.list_collections.return_value = []

        # List collections
        result = manager.list_collections()

        # Verify result
        assert result == []
        mock_client.list_collections.assert_called_once()

    def test_list_collections_multiple(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test listing multiple collections."""
        manager, mock_client = mock_manager
        # Reset the mock to clear any calls from initialization
        mock_client.list_collections.reset_mock()
        collection_names = ["collection1", "collection2", "collection3"]
        mock_client.list_collections.return_value = collection_names

        # List collections
        result = manager.list_collections()

        # Verify result
        assert result == collection_names
        mock_client.list_collections.assert_called_once()

    def test_get_collections_with_details(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test getting collections with metadata and counts."""
        manager, mock_client = mock_manager

        # Setup mock collections
        collection_names = ["col1", "col2"]
        mock_client.list_collections.return_value = collection_names

        mock_col1 = MagicMock()
        mock_col1.metadata = {"type": "documents"}
        mock_col1.count.return_value = 100

        mock_col2 = MagicMock()
        mock_col2.metadata = {"type": "embeddings"}
        mock_col2.count.return_value = 200

        # get_collection is called twice for each collection
        mock_client.get_collection.side_effect = [
            mock_col1,
            mock_col1,
            mock_col2,
            mock_col2,
        ]

        # Get collections with details
        result = manager.get_collections_with_details()

        # Verify result
        expected = [
            {"name": "col1", "metadata": {"type": "documents"}, "count": 100},
            {"name": "col2", "metadata": {"type": "embeddings"}, "count": 200},
        ]
        assert result == expected

    def test_get_collections_with_details_partial_failure(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test handling when some collections fail to retrieve details."""
        manager, mock_client = mock_manager

        # Setup mock collections
        collection_names = ["col1", "col2", "col3"]
        mock_client.list_collections.return_value = collection_names

        mock_col1 = MagicMock()
        mock_col1.metadata = {"type": "documents"}
        mock_col1.count.return_value = 100

        # col2 will fail
        mock_col3 = MagicMock()
        mock_col3.metadata = {"type": "vectors"}
        mock_col3.count.return_value = 300

        # Configure side effects
        # col1: get_collection succeeds, then succeeds again for count_items
        # col2: get_collection fails immediately
        # col3: get_collection succeeds, then succeeds again for count_items
        mock_client.get_collection.side_effect = [
            mock_col1,  # col1 get_collection
            mock_col1,  # col1 count_items
            Exception("Failed to get col2"),  # col2 get_collection fails
            mock_col3,  # col3 get_collection
            mock_col3,  # col3 count_items
        ]

        # Get collections with details
        result = manager.get_collections_with_details()

        # Should only return successful collections
        expected = [
            {"name": "col1", "metadata": {"type": "documents"}, "count": 100},
            {"name": "col3", "metadata": {"type": "vectors"}, "count": 300},
        ]
        assert result == expected

    def test_count_items_empty_collection(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test counting items in empty collection."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.get_collection.return_value = mock_collection

        # Count items
        result = manager.count_items("empty_collection")

        # Verify result
        assert result == 0
        mock_collection.count.assert_called_once()

    def test_count_items_populated_collection(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test counting items in populated collection."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        expected_count = 42
        mock_collection.count.return_value = expected_count
        mock_client.get_collection.return_value = mock_collection

        # Count items
        result = manager.count_items("test_collection")

        # Verify result
        assert result == expected_count
        mock_collection.count.assert_called_once()

    def test_peek_collection_default_limit(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test peeking with default limit."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        peek_data = {"ids": ["1", "2"], "documents": ["doc1", "doc2"]}
        mock_collection.peek.return_value = peek_data
        mock_client.get_collection.return_value = mock_collection

        # Peek collection
        result = manager.peek_collection("test_collection")

        # Verify result
        assert result == peek_data
        mock_collection.peek.assert_called_once_with(limit=10)

    def test_peek_collection_custom_limit(
        self, mock_manager: tuple[VectorDBManager, MagicMock]
    ) -> None:
        """Test peeking with custom limit."""
        manager, mock_client = mock_manager
        mock_collection = MagicMock()
        peek_data = {"ids": ["1", "2", "3"], "documents": ["doc1", "doc2", "doc3"]}
        mock_collection.peek.return_value = peek_data
        mock_client.get_collection.return_value = mock_collection

        # Peek collection with custom limit
        result = manager.peek_collection("test_collection", limit=3)

        # Verify result
        assert result == peek_data
        mock_collection.peek.assert_called_once_with(limit=3)
