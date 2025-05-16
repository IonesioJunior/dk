"""
Vector Database Manager using ChromaDB

Provides a singleton manager for ChromaDB operations with full CRUD support
for collections and data.
"""

import chromadb
from chromadb.config import Settings
from typing import Optional, Dict, List, Any, Union
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorDBManager:
    """
    Singleton Vector Database Manager using ChromaDB persistent client.
    
    This manager handles all CRUD operations for collections and data within
    ChromaDB, using a persistent connection to store data in ./vectordb.
    """
    
    _instance: Optional['VectorDBManager'] = None
    _client: Optional[chromadb.PersistentClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the VectorDBManager with persistent client."""
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the ChromaDB persistent client."""
        try:
            db_path = "./vectordb"
            Path(db_path).mkdir(exist_ok=True)
            
            self._client = chromadb.PersistentClient(path=db_path)
            logger.info(f"ChromaDB client initialized with path: {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def heartbeat(self) -> int:
        """Check if the database is responsive."""
        return self._client.heartbeat()
    
    def reset(self):
        """Reset the database. WARNING: This is destructive and irreversible."""
        logger.warning("Resetting ChromaDB - all data will be lost!")
        self._client.reset()
    
    # Collection Management Methods
    
    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[Any] = None
    ):
        """
        Create a new collection.
        
        Args:
            name: Collection name (3-63 chars, lowercase letters/digits, dots/dashes/underscores)
            metadata: Optional metadata for the collection
            embedding_function: Optional custom embedding function
            
        Returns:
            The created collection
        """
        try:
            kwargs = {"name": name}
            if metadata:
                kwargs["metadata"] = metadata
            if embedding_function:
                kwargs["embedding_function"] = embedding_function
                
            collection = self._client.create_collection(**kwargs)
            logger.info(f"Collection '{name}' created successfully")
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection '{name}': {e}")
            raise
    
    def get_collection(
        self,
        name: str,
        embedding_function: Optional[Any] = None
    ):
        """
        Get an existing collection.
        
        Args:
            name: Collection name
            embedding_function: Optional embedding function
            
        Returns:
            The requested collection
        """
        try:
            kwargs = {"name": name}
            if embedding_function:
                kwargs["embedding_function"] = embedding_function
                
            return self._client.get_collection(**kwargs)
        except Exception as e:
            logger.error(f"Failed to get collection '{name}': {e}")
            raise
    
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[Any] = None
    ):
        """
        Get a collection if it exists, otherwise create it.
        
        Args:
            name: Collection name
            metadata: Optional metadata for the collection
            embedding_function: Optional custom embedding function
            
        Returns:
            The collection (existing or newly created)
        """
        try:
            kwargs = {"name": name}
            if metadata:
                kwargs["metadata"] = metadata
            if embedding_function:
                kwargs["embedding_function"] = embedding_function
                
            return self._client.get_or_create_collection(**kwargs)
        except Exception as e:
            logger.error(f"Failed to get or create collection '{name}': {e}")
            raise
    
    def delete_collection(self, name: str):
        """
        Delete a collection. WARNING: This is destructive and irreversible.
        
        Args:
            name: Collection name to delete
        """
        try:
            self._client.delete_collection(name=name)
            logger.info(f"Collection '{name}' deleted successfully")
        except Exception as e:
            logger.error(f"Failed to delete collection '{name}': {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """
        List all collections in the database.
        
        Returns:
            List of collection names
        """
        try:
            return self._client.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise
    
    def get_collections_with_details(self) -> List[Dict[str, Any]]:
        """
        Get all collections with their details (name, metadata, count).
        
        Returns:
            List of collection details
        """
        try:
            collection_names = self._client.list_collections()
            collections = []
            
            for name in collection_names:
                try:
                    collection = self.get_collection(name)
                    count = self.count_items(name)
                    collections.append({
                        "name": name,
                        "metadata": collection.metadata,
                        "count": count
                    })
                except Exception as e:
                    logger.warning(f"Failed to get details for collection '{name}': {e}")
                    continue
                    
            return collections
        except Exception as e:
            logger.error(f"Failed to get collections with details: {e}")
            raise
    
    # Data Management Methods
    
    def add_data(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Add data to a collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of unique IDs for the documents
            documents: Optional list of document strings (will be embedded automatically)
            embeddings: Optional pre-computed embeddings
            metadatas: Optional list of metadata dictionaries
        """
        try:
            collection = self.get_collection(collection_name)
            
            kwargs = {"ids": ids}
            if documents:
                kwargs["documents"] = documents
            if embeddings:
                kwargs["embeddings"] = embeddings
            if metadatas:
                kwargs["metadatas"] = metadatas
                
            collection.add(**kwargs)
            logger.info(f"Added {len(ids)} items to collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to add data to collection '{collection_name}': {e}")
            raise
    
    def update_data(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Update existing data in a collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of IDs to update
            documents: Optional updated documents
            embeddings: Optional updated embeddings
            metadatas: Optional updated metadata
        """
        try:
            collection = self.get_collection(collection_name)
            
            kwargs = {"ids": ids}
            if documents:
                kwargs["documents"] = documents
            if embeddings:
                kwargs["embeddings"] = embeddings
            if metadatas:
                kwargs["metadatas"] = metadatas
                
            collection.update(**kwargs)
            logger.info(f"Updated {len(ids)} items in collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to update data in collection '{collection_name}': {e}")
            raise
    
    def upsert_data(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Update existing data or insert if it doesn't exist.
        
        Args:
            collection_name: Name of the collection
            ids: List of IDs to upsert
            documents: Optional documents
            embeddings: Optional embeddings
            metadatas: Optional metadata
        """
        try:
            collection = self.get_collection(collection_name)
            
            kwargs = {"ids": ids}
            if documents:
                kwargs["documents"] = documents
            if embeddings:
                kwargs["embeddings"] = embeddings
            if metadatas:
                kwargs["metadatas"] = metadatas
                
            collection.upsert(**kwargs)
            logger.info(f"Upserted {len(ids)} items in collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to upsert data in collection '{collection_name}': {e}")
            raise
    
    def delete_data(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ):
        """
        Delete data from a collection.
        
        Args:
            collection_name: Name of the collection
            ids: Optional list of IDs to delete
            where: Optional filter for deletion
        """
        try:
            collection = self.get_collection(collection_name)
            
            kwargs = {}
            if ids:
                kwargs["ids"] = ids
            if where:
                kwargs["where"] = where
                
            collection.delete(**kwargs)
            logger.info(f"Deleted items from collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete data from collection '{collection_name}': {e}")
            raise
    
    # Query Methods
    
    def query(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Query a collection for similar items.
        
        Args:
            collection_name: Name of the collection
            query_texts: Optional list of query texts (will be embedded)
            query_embeddings: Optional pre-computed query embeddings
            n_results: Number of results to return (default: 10)
            where: Optional metadata filter
            where_document: Optional document content filter
            include: Optional list of data to include in results
            
        Returns:
            Query results
        """
        try:
            collection = self.get_collection(collection_name)
            
            kwargs = {"n_results": n_results}
            if query_texts:
                kwargs["query_texts"] = query_texts
            if query_embeddings:
                kwargs["query_embeddings"] = query_embeddings
            if where:
                kwargs["where"] = where
            if where_document:
                kwargs["where_document"] = where_document
            if include:
                kwargs["include"] = include
                
            return collection.query(**kwargs)
        except Exception as e:
            logger.error(f"Failed to query collection '{collection_name}': {e}")
            raise
    
    def get(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get items from a collection by ID or filter.
        
        Args:
            collection_name: Name of the collection
            ids: Optional list of IDs to retrieve
            where: Optional metadata filter
            limit: Optional limit on results
            offset: Optional offset for pagination
            include: Optional list of data to include in results
            
        Returns:
            Retrieved items
        """
        try:
            collection = self.get_collection(collection_name)
            
            kwargs = {}
            if ids:
                kwargs["ids"] = ids
            if where:
                kwargs["where"] = where
            if limit:
                kwargs["limit"] = limit
            if offset:
                kwargs["offset"] = offset
            if include:
                kwargs["include"] = include
                
            return collection.get(**kwargs)
        except Exception as e:
            logger.error(f"Failed to get data from collection '{collection_name}': {e}")
            raise
    
    def count_items(self, collection_name: str) -> int:
        """
        Count the number of items in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of items in the collection
        """
        try:
            collection = self.get_collection(collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"Failed to count items in collection '{collection_name}': {e}")
            raise
    
    def peek_collection(self, collection_name: str, limit: int = 10) -> Dict[str, Any]:
        """
        Peek at the first few items in a collection.
        
        Args:
            collection_name: Name of the collection
            limit: Number of items to peek (default: 10)
            
        Returns:
            The first few items in the collection
        """
        try:
            collection = self.get_collection(collection_name)
            return collection.peek(limit=limit)
        except Exception as e:
            logger.error(f"Failed to peek collection '{collection_name}': {e}")
            raise