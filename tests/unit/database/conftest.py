"""Shared fixtures and utilities for database unit tests."""

import random
import string
from collections.abc import Generator
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from database.vector_db_manager import VectorDBManager


@pytest.fixture(autouse=True)
def _reset_singleton() -> Generator[None, None, None]:
    """Automatically reset VectorDBManager singleton before each test."""
    VectorDBManager._instance = None
    VectorDBManager._client = None
    yield
    # Cleanup after test
    VectorDBManager._instance = None
    VectorDBManager._client = None


@pytest.fixture()
def mock_chromadb_client() -> Generator[MagicMock, None, None]:
    """Fixture providing a mocked ChromaDB client."""
    with patch("database.vector_db_manager.chromadb.PersistentClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        # Default behaviors
        mock_client_instance.list_collections.return_value = []
        mock_client_instance.heartbeat.return_value = 1234567890

        yield mock_client_instance


@pytest.fixture()
def vector_db_manager(mock_chromadb_client: MagicMock) -> VectorDBManager:
    """Fixture providing a VectorDBManager instance with mocked client."""
    # Ensure mock client is available
    _ = mock_chromadb_client
    return VectorDBManager()


@pytest.fixture()
def test_collection(mock_chromadb_client: MagicMock) -> MagicMock:
    """Fixture providing a mock collection."""
    # Ensure mock client is available
    _ = mock_chromadb_client
    mock_collection = MagicMock()
    mock_collection.name = "test_collection"
    mock_collection.metadata = {"test": True}
    mock_collection.count.return_value = 0
    return mock_collection


@pytest.fixture()
def sample_documents() -> list[str]:
    """Fixture providing sample documents for testing."""
    return [
        "This is the first test document about Python programming.",
        "Second document discusses machine learning and AI.",
        "Third document covers vector databases and embeddings.",
        "Fourth document is about testing best practices.",
        "Fifth document contains information about ChromaDB.",
    ]


@pytest.fixture()
def sample_embeddings() -> list[list[float]]:
    """Fixture providing sample embeddings (384-dimensional)."""

    def generate_embedding() -> list[float]:
        return [random.random() for _ in range(384)]

    return [generate_embedding() for _ in range(5)]


@pytest.fixture()
def sample_metadatas() -> list[dict[str, str]]:
    """Fixture providing sample metadata for documents."""
    return [
        {"category": "programming", "language": "python", "difficulty": "beginner"},
        {"category": "ai", "subcategory": "ml", "difficulty": "intermediate"},
        {"category": "database", "type": "vector", "difficulty": "advanced"},
        {"category": "testing", "framework": "pytest", "difficulty": "intermediate"},
        {"category": "database", "name": "chromadb", "difficulty": "beginner"},
    ]


@pytest.fixture()
def sample_ids() -> list[str]:
    """Fixture providing sample document IDs."""
    return [f"doc_{i}" for i in range(1, 6)]


@pytest.fixture()
def _cleanup_database(vector_db_manager: VectorDBManager) -> None:
    """Fixture to clean up database after tests."""
    # Ensure vector_db_manager is available
    _ = vector_db_manager
    # Cleanup logic would go here if needed
    # For unit tests with mocks, this is usually not necessary


# Helper functions for test data generation


def create_test_documents(count: int) -> list[str]:
    """Helper to create test documents."""
    topics = [
        "python",
        "machine learning",
        "databases",
        "testing",
        "APIs",
        "algorithms",
    ]
    documents = []
    for i in range(count):
        topic = random.choice(topics)
        doc = f"Test document {i+1} about {topic}. " + " ".join(
            random.choices(string.ascii_lowercase.split(), k=20)
        )
        documents.append(doc)
    return documents


def create_test_embeddings(count: int, dimensions: int = 384) -> list[list[float]]:
    """Helper to create test embeddings."""
    return [[random.random() for _ in range(dimensions)] for _ in range(count)]


def create_test_metadatas(count: int) -> list[dict[str, Any]]:
    """Helper to create test metadata."""
    categories = ["tech", "science", "business", "health", "education"]
    metadatas = []
    for i in range(count):
        metadata = {
            "id": i + 1,
            "category": random.choice(categories),
            "timestamp": f"2024-01-{random.randint(1, 31):02d}",
            "score": round(random.random() * 100, 2),
            "tags": random.sample(
                ["important", "review", "draft", "final", "archived"], k=2
            ),
        }
        metadatas.append(metadata)
    return metadatas


def assert_collection_state(
    collection_mock: MagicMock, expected_count: int, expected_name: Optional[str] = None
) -> None:
    """Helper to assert collection state."""
    assert collection_mock.count.return_value == expected_count
    if expected_name:
        assert collection_mock.name == expected_name


def create_mock_query_results(n_results: int = 5) -> dict[str, Any]:
    """Helper to create mock query results."""
    ids = [[f"doc_{i}" for i in range(1, n_results + 1)]]
    distances = [[random.random() for _ in range(n_results)]]
    documents = [[f"Document {i} content" for i in range(1, n_results + 1)]]
    metadatas = [[{"index": i} for i in range(1, n_results + 1)]]

    return {
        "ids": ids,
        "distances": distances,
        "documents": documents,
        "metadatas": metadatas,
        "embeddings": None,  # Usually not included in results
    }
