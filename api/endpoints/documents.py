"""
Document management API endpoints using VectorDBManager
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
import logging
from database import VectorDBManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize VectorDBManager singleton
db_manager = VectorDBManager()


# Pydantic models for request/response validation

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=63, description="Collection name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class CollectionResponse(BaseModel):
    name: str
    metadata: Optional[Dict[str, Any]]
    count: int


class DocumentAdd(BaseModel):
    ids: List[str] = Field(..., description="Unique IDs for documents")
    documents: Optional[List[str]] = Field(None, description="Document texts to embed")
    embeddings: Optional[List[List[float]]] = Field(None, description="Pre-computed embeddings")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="Document metadata")


class DocumentUpdate(BaseModel):
    ids: List[str] = Field(..., description="IDs to update")
    documents: Optional[List[str]] = Field(None, description="Updated documents")
    embeddings: Optional[List[List[float]]] = Field(None, description="Updated embeddings")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="Updated metadata")


class DocumentQuery(BaseModel):
    query_texts: Optional[List[str]] = Field(None, description="Query texts")
    query_embeddings: Optional[List[List[float]]] = Field(None, description="Query embeddings")
    n_results: int = Field(10, ge=1, le=100, description="Number of results")
    where: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")
    where_document: Optional[Dict[str, Any]] = Field(None, description="Document content filter")
    include: Optional[List[str]] = Field(None, description="Data to include in results")


class DocumentGet(BaseModel):
    ids: Optional[List[str]] = Field(None, description="Document IDs to retrieve")
    where: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")
    limit: Optional[int] = Field(None, ge=1, description="Result limit")
    offset: Optional[int] = Field(None, ge=0, description="Result offset")
    include: Optional[List[str]] = Field(None, description="Data to include")


class DocumentDelete(BaseModel):
    ids: Optional[List[str]] = Field(None, description="IDs to delete")
    where: Optional[Dict[str, Any]] = Field(None, description="Filter for deletion")


# Collection endpoints

@router.post("/collections")
async def create_collection(collection: CollectionCreate) -> CollectionResponse:
    """Create a new collection"""
    try:
        result = db_manager.create_collection(
            name=collection.name,
            metadata=collection.metadata
        )
        count = db_manager.count_items(collection.name)
        return CollectionResponse(
            name=result.name,
            metadata=collection.metadata,
            count=count
        )
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/collections/{collection_name}")
async def get_collection(collection_name: str) -> CollectionResponse:
    """Get a collection by name"""
    try:
        collection = db_manager.get_collection(name=collection_name)
        count = db_manager.count_items(collection_name)
        return CollectionResponse(
            name=collection.name,
            metadata=collection.metadata,
            count=count
        )
    except Exception as e:
        logger.error(f"Failed to get collection: {e}")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")


@router.get("/collections")
async def list_collections() -> List[CollectionResponse]:
    """List all collections"""
    try:
        collections = db_manager.get_collections_with_details()
        results = []
        for col in collections:
            results.append(CollectionResponse(
                name=col["name"],
                metadata=col["metadata"],
                count=col["count"]
            ))
        return results
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str) -> Dict[str, str]:
    """Delete a collection"""
    try:
        db_manager.delete_collection(name=collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")


# Document endpoints

@router.post("/collections/{collection_name}/documents")
async def add_documents(collection_name: str, documents: DocumentAdd) -> Dict[str, Any]:
    """Add documents to a collection"""
    try:
        db_manager.add_data(
            collection_name=collection_name,
            ids=documents.ids,
            documents=documents.documents,
            embeddings=documents.embeddings,
            metadatas=documents.metadatas
        )
        return {
            "message": f"Added {len(documents.ids)} documents to collection '{collection_name}'",
            "count": len(documents.ids)
        }
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/collections/{collection_name}/documents")
async def update_documents(collection_name: str, documents: DocumentUpdate) -> Dict[str, Any]:
    """Update documents in a collection"""
    try:
        db_manager.update_data(
            collection_name=collection_name,
            ids=documents.ids,
            documents=documents.documents,
            embeddings=documents.embeddings,
            metadatas=documents.metadatas
        )
        return {
            "message": f"Updated {len(documents.ids)} documents in collection '{collection_name}'",
            "count": len(documents.ids)
        }
    except Exception as e:
        logger.error(f"Failed to update documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/collections/{collection_name}/documents")
async def upsert_documents(collection_name: str, documents: DocumentAdd) -> Dict[str, Any]:
    """Upsert documents in a collection"""
    try:
        db_manager.upsert_data(
            collection_name=collection_name,
            ids=documents.ids,
            documents=documents.documents,
            embeddings=documents.embeddings,
            metadatas=documents.metadatas
        )
        return {
            "message": f"Upserted {len(documents.ids)} documents in collection '{collection_name}'",
            "count": len(documents.ids)
        }
    except Exception as e:
        logger.error(f"Failed to upsert documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/collections/{collection_name}/documents")
async def delete_documents(collection_name: str, deletion: DocumentDelete) -> Dict[str, str]:
    """Delete documents from a collection"""
    try:
        db_manager.delete_data(
            collection_name=collection_name,
            ids=deletion.ids,
            where=deletion.where
        )
        return {"message": f"Deleted documents from collection '{collection_name}'"}
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Query endpoints

@router.post("/collections/{collection_name}/query")
async def query_documents(collection_name: str, query: DocumentQuery) -> Dict[str, Any]:
    """Query documents in a collection"""
    try:
        results = db_manager.query(
            collection_name=collection_name,
            query_texts=query.query_texts,
            query_embeddings=query.query_embeddings,
            n_results=query.n_results,
            where=query.where,
            where_document=query.where_document,
            include=query.include
        )
        return results
    except Exception as e:
        logger.error(f"Failed to query documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/collections/{collection_name}/get")
async def get_documents(collection_name: str, get_request: DocumentGet) -> Dict[str, Any]:
    """Get documents by ID or filter"""
    try:
        results = db_manager.get(
            collection_name=collection_name,
            ids=get_request.ids,
            where=get_request.where,
            limit=get_request.limit,
            offset=get_request.offset,
            include=get_request.include
        )
        return results
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/collections/{collection_name}/count")
async def count_documents(collection_name: str) -> Dict[str, int]:
    """Count documents in a collection"""
    try:
        count = db_manager.count_items(collection_name)
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to count documents: {e}")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")


@router.get("/collections/{collection_name}/peek")
async def peek_collection(collection_name: str, limit: int = 10) -> Dict[str, Any]:
    """Peek at documents in a collection"""
    try:
        results = db_manager.peek_collection(collection_name, limit=limit)
        return results
    except Exception as e:
        logger.error(f"Failed to peek collection: {e}")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")


# Health check endpoint

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check VectorDB health"""
    try:
        heartbeat = db_manager.heartbeat()
        return {
            "status": "healthy",
            "heartbeat": heartbeat
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }