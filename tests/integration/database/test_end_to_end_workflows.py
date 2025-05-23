"""Integration tests for VectorDBManager end-to-end workflows."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

from database.vector_db_manager import GetParams, QueryParams, VectorDBManager


class TestEndToEndWorkflows:
    """Integration tests for complete database workflows."""

    @pytest.fixture()
    def temp_db_path(self) -> Generator[Path, None, None]:
        """Fixture providing a temporary database path."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture()
    def real_manager(
        self, temp_db_path: Path, monkeypatch: MonkeyPatch
    ) -> Generator[VectorDBManager, None, None]:
        """Fixture providing a real VectorDBManager with temporary storage."""
        # Clear singleton
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Monkey patch the specific path construction in _initialize_client
        import database.vector_db_manager

        def mock_initialize_client(self: Any) -> None:
            """Initialize the ChromaDB persistent client with temp path."""
            try:
                import logging

                import chromadb

                db_path = temp_db_path / "vectordb"
                db_path.mkdir(parents=True, exist_ok=True)

                self._client = chromadb.PersistentClient(path=str(db_path))
                logging.getLogger("database.vector_db_manager").info(
                    f"ChromaDB client initialized with path: {db_path}"
                )

                # Ensure the documents collection exists
                self._ensure_default_collections()
            except Exception as e:
                logging.getLogger("database.vector_db_manager").error(
                    f"Failed to initialize ChromaDB client: {e}"
                )
                raise

        monkeypatch.setattr(
            database.vector_db_manager.VectorDBManager,
            "_initialize_client",
            mock_initialize_client,
        )

        manager = VectorDBManager()
        yield manager

        # Cleanup
        VectorDBManager._instance = None
        VectorDBManager._client = None

    def test_complete_document_workflow(self, real_manager: VectorDBManager) -> None:
        """Test complete workflow: create collection, add, query, update, delete."""
        manager = real_manager

        # Step 1: Create a collection
        collection_name = "test_documents"
        metadata = {"description": "Test collection for documents"}
        manager.create_collection(collection_name, metadata=metadata)

        # Verify collection exists
        collections = manager.list_collections()
        assert collection_name in collections

        # Step 2: Add documents
        documents = [
            "Python is a versatile programming language.",
            "Machine learning transforms data into insights.",
            "Vector databases enable semantic search.",
            "Testing ensures code quality and reliability.",
            "ChromaDB is a vector database for AI applications.",
        ]
        ids = [f"doc_{i}" for i in range(1, 6)]
        metadatas = [
            {"topic": "programming", "language": "python"},
            {"topic": "ai", "subtopic": "ml"},
            {"topic": "database", "type": "vector"},
            {"topic": "engineering", "practice": "testing"},
            {"topic": "database", "product": "chromadb"},
        ]

        add_params = manager.AddDataParams(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        manager.add_data(add_params)

        # Verify documents were added
        expected_count = 5
        count = manager.count_items(collection_name)
        assert count == expected_count

        # Step 3: Query documents
        query_params = QueryParams(
            collection_name=collection_name,
            query_texts=["programming languages"],
            n_results=3,
        )
        results = manager.query(query_params)

        # Verify query results
        max_results = 3
        assert len(results["ids"][0]) <= max_results
        assert "doc_1" in results["ids"][0]  # Python document should be relevant

        # Step 4: Update a document
        update_params = manager.UpdateDataParams(
            collection_name=collection_name,
            ids=["doc_1"],
            documents=[
                "Python is an amazing and versatile programming language used in AI."
            ],
            metadatas=[{"topic": "programming", "language": "python", "updated": True}],
        )
        manager.update_data(update_params)

        # Verify update
        get_params = GetParams(collection_name=collection_name, ids=["doc_1"])
        updated_doc = manager.get(get_params)
        assert "amazing" in updated_doc["documents"][0]
        assert updated_doc["metadatas"][0]["updated"] is True

        # Step 5: Delete documents
        manager.delete_data(collection_name, ids=["doc_5"])

        # Verify deletion
        expected_remaining = 4
        count = manager.count_items(collection_name)
        assert count == expected_remaining

        # Step 6: Clean up - delete collection
        manager.delete_collection(collection_name)

        # Verify collection is gone
        collections = manager.list_collections()
        assert collection_name not in collections

    def test_multi_collection_workflow(self, real_manager: VectorDBManager) -> None:
        """Test working with multiple collections simultaneously."""
        manager = real_manager

        # Create multiple collections
        collections_config = [
            ("products", {"type": "catalog", "version": "1.0"}),
            ("customers", {"type": "users", "version": "1.0"}),
            ("reviews", {"type": "feedback", "version": "1.0"}),
        ]

        for name, metadata in collections_config:
            manager.create_collection(name, metadata=metadata)

        # Verify all collections exist
        collections = manager.list_collections()
        min_collections = 3
        assert len(collections) >= min_collections
        for name, _ in collections_config:
            assert name in collections

        # Add data to each collection
        docs_per_collection = 3
        for name, _ in collections_config:
            docs = [f"Sample {name} document {i}" for i in range(docs_per_collection)]
            ids = [f"{name}_{i}" for i in range(docs_per_collection)]

            add_params = manager.AddDataParams(
                collection_name=name, ids=ids, documents=docs
            )
            manager.add_data(add_params)

        # Verify data in each collection
        for name, _ in collections_config:
            count = manager.count_items(name)
            assert count == docs_per_collection

        # Get collections with details
        details = manager.get_collections_with_details()
        assert len(details) >= min_collections

        for detail in details:
            if detail["name"] in ["products", "customers", "reviews"]:
                assert detail["count"] == docs_per_collection
                assert "type" in detail["metadata"]

    def test_batch_operations_workflow(self, real_manager: VectorDBManager) -> None:
        """Test batch add, update, and delete operations."""
        manager = real_manager
        collection_name = "batch_test"

        # Create collection
        manager.create_collection(collection_name)

        # Batch add - 100 documents
        batch_size = 100
        documents = [
            f"Document {i}: " + " ".join([f"word{j}" for j in range(10)])
            for i in range(batch_size)
        ]
        ids = [f"batch_doc_{i}" for i in range(batch_size)]
        metadatas = [{"batch": 1, "index": i} for i in range(batch_size)]

        add_params = manager.AddDataParams(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        manager.add_data(add_params)

        # Verify batch add
        count = manager.count_items(collection_name)
        assert count == batch_size

        # Batch update - update first 50 documents
        update_ids = ids[:50]
        update_docs = [f"Updated: {doc}" for doc in documents[:50]]
        update_metadatas = [
            {"batch": 2, "index": i, "updated": True} for i in range(50)
        ]

        update_params = manager.UpdateDataParams(
            collection_name=collection_name,
            ids=update_ids,
            documents=update_docs,
            metadatas=update_metadatas,
        )
        manager.update_data(update_params)

        # Verify batch update
        expected_updated = 50
        get_params = GetParams(collection_name=collection_name, where={"updated": True})
        updated_docs = manager.get(get_params)
        assert len(updated_docs["ids"]) == expected_updated

        # Batch delete - delete last 25 documents
        delete_ids = ids[-25:]
        manager.delete_data(collection_name, ids=delete_ids)

        # Verify batch delete
        expected_final_count = 75
        count = manager.count_items(collection_name)
        assert count == expected_final_count

    def test_persistence_workflow(self, real_manager: VectorDBManager) -> None:
        """Test data persistence across manager instances."""
        collection_name = "persistence_test"

        # First instance - add data
        manager1 = real_manager
        manager1.create_collection(collection_name)

        documents = ["Persistent document 1", "Persistent document 2"]
        ids = ["persist_1", "persist_2"]

        add_params = manager1.AddDataParams(
            collection_name=collection_name, ids=ids, documents=documents
        )
        manager1.add_data(add_params)

        # Clear singleton to force new instance
        VectorDBManager._instance = None
        VectorDBManager._client = None

        # Second instance - verify data persists
        manager2 = VectorDBManager()

        # Check collection exists
        collections = manager2.list_collections()
        assert collection_name in collections

        # Check data exists
        expected_docs = 2
        count = manager2.count_items(collection_name)
        assert count == expected_docs

        # Retrieve and verify data
        get_params = GetParams(collection_name=collection_name, ids=ids)
        retrieved = manager2.get(get_params)
        assert len(retrieved["ids"]) == expected_docs
        assert retrieved["documents"] == documents

    def test_error_recovery_workflow(self, real_manager: VectorDBManager) -> None:
        """Test recovery from various error conditions."""
        manager = real_manager

        # Test 1: Recover from failed collection creation
        # Try to create collection with invalid name
        with pytest.raises(ValueError, match=".*"):
            manager.create_collection("")  # Empty name should fail

        # Should still be able to create valid collection
        manager.create_collection("valid_collection")
        assert "valid_collection" in manager.list_collections()

        # Test 2: Recover from failed data operations
        collection_name = "error_test"
        manager.create_collection(collection_name)

        # Try to add data with mismatched lengths
        add_params = manager.AddDataParams(
            collection_name=collection_name,
            ids=["id1", "id2"],
            documents=["doc1"],  # Mismatched length
        )
        with pytest.raises(ValueError, match=".*"):
            manager.add_data(add_params)

        # Should still be able to add valid data
        add_params = manager.AddDataParams(
            collection_name=collection_name,
            ids=["id1", "id2"],
            documents=["doc1", "doc2"],
        )
        manager.add_data(add_params)
        expected_items = 2
        assert manager.count_items(collection_name) == expected_items

        # Test 3: Recover from query errors
        # Query non-existent collection
        query_params = QueryParams(collection_name="non_existent", query_texts=["test"])
        from chromadb.errors import InvalidCollectionException

        with pytest.raises(InvalidCollectionException, match=".*"):
            manager.query(query_params)

        # Should still be able to query valid collection
        query_params = QueryParams(
            collection_name=collection_name, query_texts=["test"], n_results=1
        )
        results = manager.query(query_params)
        assert "ids" in results

    def test_filtered_operations_workflow(self, real_manager: VectorDBManager) -> None:
        """Test operations with metadata filters."""
        manager = real_manager
        collection_name = "filtered_ops"

        # Create collection and add diverse data
        manager.create_collection(collection_name)

        documents = []
        ids = []
        metadatas = []

        categories = ["tech", "health", "finance", "education"]
        priorities = ["high", "medium", "low"]

        num_docs = 20
        for i in range(num_docs):
            doc_id = f"doc_{i}"
            category = categories[i % len(categories)]
            priority = priorities[i % len(priorities)]

            documents.append(f"Document about {category} with priority {priority}")
            ids.append(doc_id)
            metadatas.append({"category": category, "priority": priority, "index": i})

        add_params = manager.AddDataParams(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        manager.add_data(add_params)

        # Test filtered get
        get_params = GetParams(
            collection_name=collection_name, where={"category": "tech"}
        )
        tech_docs = manager.get(get_params)
        assert all(meta["category"] == "tech" for meta in tech_docs["metadatas"])

        # Test filtered query
        query_params = QueryParams(
            collection_name=collection_name,
            query_texts=["technology"],
            where={"priority": "high"},
            n_results=5,
        )
        results = manager.query(query_params)
        assert all(meta["priority"] == "high" for meta in results["metadatas"][0])

        # Test filtered delete
        manager.delete_data(collection_name, where={"priority": "low"})

        # Verify low priority docs were deleted
        remaining = manager.get(GetParams(collection_name=collection_name))
        assert all(meta["priority"] != "low" for meta in remaining["metadatas"])
