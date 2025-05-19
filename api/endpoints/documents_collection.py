"""
Document management API endpoints specifically for 'documents' collection
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import VectorDBManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents-collection"])

# Initialize VectorDBManager singleton
db_manager = VectorDBManager()

# Default collection name
DOCUMENTS_COLLECTION = "documents"


def get_file_extension(file_name: str) -> str:
    """Extract the file extension from a filename."""
    _, ext = os.path.splitext(file_name)
    return ext.lower().lstrip(".")


def calculate_word_count(content: str) -> int:
    """Calculate the number of words in the document content."""
    return len(content.split())


def calculate_file_size(content: str) -> int:
    """Calculate the size of the document content in bytes."""
    return len(content.encode("utf-8"))


# Pydantic models for request/response validation
class DocumentCreate(BaseModel):
    file_name: str = Field(..., description="File name for the document")
    content: str = Field(..., description="Document content")
    metadata: Optional[dict[str, Any]] = Field(None, description="Document metadata")
    embedding: Optional[list[float]] = Field(None, description="Pre-computed embedding")


class DocumentBulkCreate(BaseModel):
    documents: list[DocumentCreate] = Field(
        ..., description="List of documents to create"
    )


class DocumentResponse(BaseModel):
    id: str
    content: str
    metadata: Optional[dict[str, Any]]
    embedding: Optional[list[float]] = None


class DocumentUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Updated content")
    metadata: Optional[dict[str, Any]] = Field(None, description="Updated metadata")
    embedding: Optional[list[float]] = Field(None, description="Updated embedding")


class DocumentQuery(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Number of results")
    metadata_filter: Optional[dict[str, Any]] = Field(
        None, description="Metadata filter"
    )
    include_embeddings: bool = Field(
        False, description="Include embeddings in response"
    )


class DocumentFilter(BaseModel):
    ids: Optional[list[str]] = Field(None, description="Document IDs to retrieve")
    metadata_filter: Optional[dict[str, Any]] = Field(
        None, description="Metadata filter"
    )
    limit: Optional[int] = Field(None, ge=1, description="Result limit")
    offset: Optional[int] = Field(None, ge=0, description="Result offset")
    include_embeddings: bool = Field(
        False, description="Include embeddings in response"
    )


class DocumentDeleteFilter(BaseModel):
    ids: Optional[list[str]] = Field(None, description="IDs to delete")
    metadata_filter: Optional[dict[str, Any]] = Field(
        None, description="Filter for deletion"
    )


# Initialize documents collection if it doesn't exist
@router.on_event("startup")
async def startup_event() -> None:
    """Initialize the documents collection on startup"""
    try:
        db_manager.create_collection(name=DOCUMENTS_COLLECTION)
        logger.info(f"Documents collection '{DOCUMENTS_COLLECTION}' initialized")
    except Exception as e:
        if "already exists" in str(e):
            logger.info(f"Documents collection '{DOCUMENTS_COLLECTION}' already exists")
        else:
            logger.error(f"Failed to initialize documents collection: {e}")


# Utility endpoints - MUST BE DEFINED BEFORE DYNAMIC ROUTES
@router.get("/count")
async def count_documents() -> dict[str, int]:
    """Count total documents in collection"""
    try:
        count = db_manager.count_items(DOCUMENTS_COLLECTION)
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to count documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peek")
async def peek_documents(limit: int = 10) -> dict[str, Any]:
    """Peek at the first few documents"""
    try:
        return db_manager.peek_collection(DOCUMENTS_COLLECTION, limit=limit)
    except Exception as e:
        logger.error(f"Failed to peek documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Check documents collection health"""
    try:
        heartbeat = db_manager.heartbeat()
        count = db_manager.count_items(DOCUMENTS_COLLECTION)
        return {
            "status": "healthy",
            "collection": DOCUMENTS_COLLECTION,
            "document_count": count,
            "heartbeat": heartbeat,
        }
    except Exception as e:
        logger.error(f"Documents health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/insights")
async def document_insights() -> dict[str, Any]:
    """Get insights about the documents collection for the dashboard"""
    try:
        # Get total document count
        total_count = db_manager.count_items(DOCUMENTS_COLLECTION)
        
        # Get all documents to analyze metadata
        results = db_manager.get(
            collection_name=DOCUMENTS_COLLECTION,
            include=["metadatas"],
        )
        
        # Initialize counters and aggregates
        total_size = 0
        total_words = 0
        extension_counts = {}
        active_count = 0
        
        # Process metadata from each document
        if results and "metadatas" in results and results["metadatas"]:
            for metadata in results["metadatas"]:
                # Update extension counts
                extension = metadata.get("extension", "unknown")
                extension_counts[extension] = extension_counts.get(extension, 0) + 1
                
                # Update size and word counts
                size = metadata.get("size", 0)
                word_count = metadata.get("word_count", 0)
                total_size += size
                total_words += word_count
                
                # Count active documents
                if metadata.get("active", False):
                    active_count += 1
        
        # Format size for display (KB, MB, etc.)
        size_display = format_file_size(total_size)
        
        # Calculate average word count per document
        avg_words = total_words // total_count if total_count > 0 else 0
        
        # Calculate active document ratio
        active_ratio = round((active_count / total_count) * 100) if total_count > 0 else 0
        
        # Get top 3 file extensions
        top_extensions = sorted(
            [(ext, count) for ext, count in extension_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "total_documents": total_count,
            "total_size": total_size,
            "size_display": size_display,
            "total_words": total_words,
            "avg_words": avg_words,
            "extension_counts": extension_counts,
            "top_extensions": top_extensions,
            "active_count": active_count,
            "active_ratio": active_ratio,
        }
    except Exception as e:
        logger.error(f"Failed to generate document insights: {e}")
        return {
            "total_documents": 0,
            "total_size": 0,
            "size_display": "0 B",
            "total_words": 0,
            "avg_words": 0,
            "extension_counts": {},
            "top_extensions": [],
            "active_count": 0,
            "active_ratio": 0,
            "error": str(e)
        }


def format_file_size(size_in_bytes: int) -> str:
    """Format file size to human-readable format"""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"


# Bulk operations
@router.post("/bulk")
async def create_documents_bulk(bulk_create: DocumentBulkCreate) -> dict[str, Any]:
    """Create multiple documents at once"""
    try:
        ids = []
        contents = []
        metadatas = []
        embeddings = []
        current_time = datetime.utcnow().isoformat()

        for doc in bulk_create.documents:
            # Generate unique ID for each document
            doc_id = f"doc_{uuid.uuid4().hex}"
            ids.append(doc_id)
            contents.append(doc.content)

            # Prepare metadata with active flag and filename
            metadata = doc.metadata.copy() if doc.metadata else {}
            metadata["active"] = True
            metadata["file_name"] = doc.file_name
            metadata["created_at"] = current_time
            
            # Add file metadata
            metadata["extension"] = get_file_extension(doc.file_name)
            metadata["word_count"] = calculate_word_count(doc.content)
            metadata["size"] = calculate_file_size(doc.content)
            
            metadatas.append(metadata)

            if doc.embedding:
                embeddings.append(doc.embedding)

        db_manager.add_data(
            collection_name=DOCUMENTS_COLLECTION,
            ids=ids,
            documents=contents,
            embeddings=embeddings if embeddings else None,
            metadatas=metadatas,
        )

        return {
            "message": f"Created {len(bulk_create.documents)} documents",
            "count": len(bulk_create.documents),
            "ids": ids,
        }
    except Exception as e:
        logger.error(f"Failed to bulk create documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/bulk")
async def delete_documents_bulk(delete_filter: DocumentDeleteFilter) -> dict[str, str]:
    """Delete multiple documents"""
    try:
        db_manager.delete_data(
            collection_name=DOCUMENTS_COLLECTION,
            ids=delete_filter.ids,
            where=delete_filter.metadata_filter,
        )
        return {"message": "Documents deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to bulk delete documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Query operations
@router.post("/search")
async def search_documents(query: DocumentQuery) -> dict[str, Any]:
    """Search for documents"""
    try:
        include = ["documents", "metadatas", "distances"]
        if query.include_embeddings:
            include.append("embeddings")

        results = db_manager.query(
            collection_name=DOCUMENTS_COLLECTION,
            query_texts=[query.query],
            n_results=query.limit,
            where=query.metadata_filter,
            include=include,
        )

        # Format results
        documents = []
        for i in range(len(results["ids"][0])):
            doc = {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": (
                    results["metadatas"][0][i] if results["metadatas"] else None
                ),
                "distance": results["distances"][0][i],
            }
            if query.include_embeddings and results["embeddings"]:
                doc["embedding"] = results["embeddings"][0][i]
            documents.append(doc)

        return {
            "documents": documents,
            "total": len(documents),
        }
    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/list")
async def list_documents(filter: DocumentFilter) -> dict[str, Any]:
    """List documents with filtering"""
    try:
        include = ["documents", "metadatas"]
        if filter.include_embeddings:
            include.append("embeddings")

        results = db_manager.get(
            collection_name=DOCUMENTS_COLLECTION,
            ids=filter.ids,
            where=filter.metadata_filter,
            limit=filter.limit,
            offset=filter.offset,
            include=include,
        )

        # Format results
        documents = []
        for i in range(len(results["ids"])):
            doc = {
                "id": results["ids"][i],
                "content": results["documents"][i],
                "metadata": results["metadatas"][i] if results["metadatas"] else None,
            }
            if filter.include_embeddings and results["embeddings"]:
                doc["embedding"] = results["embeddings"][i]
            documents.append(doc)

        return {
            "documents": documents,
            "total": len(documents),
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Individual document operations - MUST BE DEFINED LAST
@router.post("/")
async def create_document(document: DocumentCreate) -> DocumentResponse:
    """Create a single document"""
    try:
        # Generate a unique document ID
        doc_id = f"doc_{uuid.uuid4().hex}"

        # Prepare metadata with active flag and filename
        metadata = document.metadata.copy() if document.metadata else {}
        metadata["active"] = True
        metadata["file_name"] = document.file_name
        metadata["created_at"] = datetime.utcnow().isoformat()
        
        # Add file metadata
        metadata["extension"] = get_file_extension(document.file_name)
        metadata["word_count"] = calculate_word_count(document.content)
        metadata["size"] = calculate_file_size(document.content)

        db_manager.add_data(
            collection_name=DOCUMENTS_COLLECTION,
            ids=[doc_id],
            documents=[document.content],
            embeddings=[document.embedding] if document.embedding else None,
            metadatas=[metadata],
        )
        return DocumentResponse(
            id=doc_id,
            content=document.content,
            metadata=metadata,
            embedding=document.embedding,
        )
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{document_id}")
async def get_document(document_id: str) -> DocumentResponse:
    """Get a single document by ID"""
    try:
        result = db_manager.get(
            collection_name=DOCUMENTS_COLLECTION,
            ids=[document_id],
            include=["documents", "metadatas", "embeddings"],
        )

        # Debug print the result structure
        logger.info(f"Result type: {type(result)}")
        logger.info(
            f"Result keys: {result.keys() if hasattr(result, 'keys') else 'No keys'}"
        )

        # Check if result has any documents
        if not result.get("ids") or (
            hasattr(result["ids"], "__len__") and len(result["ids"]) == 0
        ):
            raise HTTPException(
                status_code=404, detail=f"Document '{document_id}' not found"
            )

        # Extract ID
        doc_id = result["ids"]
        if hasattr(doc_id, "__getitem__") and hasattr(doc_id, "__len__"):
            doc_id = doc_id[0]

        # Extract document content
        doc_content = result["documents"]
        if hasattr(doc_content, "__getitem__") and hasattr(doc_content, "__len__"):
            doc_content = doc_content[0]

        # Extract metadata
        doc_metadata = None
        if result.get("metadatas") is not None:
            doc_metadata = result["metadatas"]
            if hasattr(doc_metadata, "__getitem__") and hasattr(
                doc_metadata, "__len__"
            ):
                doc_metadata = doc_metadata[0]

        # Extract embedding
        doc_embedding = None
        if result.get("embeddings") is not None:
            doc_embedding = result["embeddings"]
            if hasattr(doc_embedding, "__getitem__") and hasattr(
                doc_embedding, "__len__"
            ):
                doc_embedding = doc_embedding[0]

        return DocumentResponse(
            id=doc_id,
            content=doc_content,
            metadata=doc_metadata,
            embedding=doc_embedding,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{document_id}")
async def update_document(document_id: str, update: DocumentUpdate) -> DocumentResponse:
    """Update a single document"""
    try:
        # Get existing document first
        await get_document(document_id)

        # Prepare update parameters
        kwargs = {
            "collection_name": DOCUMENTS_COLLECTION,
            "ids": [document_id],
        }

        # Only add parameters that are provided in the update
        if update.content is not None:
            kwargs["documents"] = [update.content]
        if update.embedding is not None:
            kwargs["embeddings"] = [update.embedding]
        if update.metadata is not None:
            kwargs["metadatas"] = [update.metadata]

        db_manager.update_data(**kwargs)

        # Return updated document
        return await get_document(document_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict[str, str]:
    """Delete a single document"""
    try:
        db_manager.delete_data(
            collection_name=DOCUMENTS_COLLECTION,
            ids=[document_id],
        )
        return {"message": f"Document '{document_id}' deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=400, detail=str(e))
