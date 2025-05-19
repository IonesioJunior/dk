# Documents API Documentation

This document describes the RESTful API endpoints for managing documents and collections in the Syft Agent's vector database.

## Base URL

All endpoints are accessible under the `/api/documents` prefix.

## Authentication

Currently, no authentication is required. This may change in future versions.

## Endpoints

### Collections

#### Create Collection
- **POST** `/api/documents/collections`
- **Body**:
  ```json
  {
    "name": "collection_name",
    "metadata": {
      "description": "Optional metadata"
    }
  }
  ```
- **Response**: 
  ```json
  {
    "name": "collection_name",
    "metadata": {...},
    "count": 0
  }
  ```

#### Get Collection
- **GET** `/api/documents/collections/{collection_name}`
- **Response**: 
  ```json
  {
    "name": "collection_name",
    "metadata": {...},
    "count": 42
  }
  ```

#### List All Collections
- **GET** `/api/documents/collections`
- **Response**: 
  ```json
  [
    {
      "name": "collection1",
      "metadata": {...},
      "count": 10
    },
    {
      "name": "collection2",
      "metadata": {...},
      "count": 25
    }
  ]
  ```

#### Delete Collection
- **DELETE** `/api/documents/collections/{collection_name}`
- **Response**: 
  ```json
  {
    "message": "Collection 'collection_name' deleted successfully"
  }
  ```

### Documents

#### Add Documents
- **POST** `/api/documents/collections/{collection_name}/documents`
- **Body**:
  ```json
  {
    "ids": ["id1", "id2"],
    "documents": ["Text document 1", "Text document 2"],
    "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],  // Optional
    "metadatas": [{"key": "value"}, {"key": "value"}]  // Optional
  }
  ```
- **Response**: 
  ```json
  {
    "message": "Added 2 documents to collection 'collection_name'",
    "count": 2
  }
  ```

#### Update Documents
- **PUT** `/api/documents/collections/{collection_name}/documents`
- **Body**: Same as Add Documents
- **Response**: 
  ```json
  {
    "message": "Updated 2 documents in collection 'collection_name'",
    "count": 2
  }
  ```

#### Upsert Documents
- **PATCH** `/api/documents/collections/{collection_name}/documents`
- **Body**: Same as Add Documents
- **Response**: 
  ```json
  {
    "message": "Upserted 2 documents in collection 'collection_name'",
    "count": 2
  }
  ```

#### Delete Documents
- **DELETE** `/api/documents/collections/{collection_name}/documents`
- **Body**:
  ```json
  {
    "ids": ["id1", "id2"],  // Optional
    "where": {"key": "value"}  // Optional filter
  }
  ```
- **Response**: 
  ```json
  {
    "message": "Deleted documents from collection 'collection_name'"
  }
  ```

### Querying

#### Query Documents
- **POST** `/api/documents/collections/{collection_name}/query`
- **Body**:
  ```json
  {
    "query_texts": ["search query"],
    "query_embeddings": [[0.1, 0.2, ...]],  // Optional, alternative to query_texts
    "n_results": 10,
    "where": {"metadata_key": "value"},  // Optional metadata filter
    "where_document": {"$contains": "text"},  // Optional full-text filter
    "include": ["documents", "metadatas", "distances"]  // Optional
  }
  ```
- **Response**: 
  ```json
  {
    "ids": [["id1", "id2", ...]],
    "documents": [["doc1", "doc2", ...]],
    "metadatas": [[{...}, {...}, ...]],
    "distances": [[0.1, 0.2, ...]]
  }
  ```

#### Get Documents by ID/Filter
- **POST** `/api/documents/collections/{collection_name}/get`
- **Body**:
  ```json
  {
    "ids": ["id1", "id2"],  // Optional
    "where": {"key": "value"},  // Optional filter
    "limit": 100,  // Optional
    "offset": 0,  // Optional
    "include": ["documents", "metadatas"]  // Optional
  }
  ```

#### Count Documents
- **GET** `/api/documents/collections/{collection_name}/count`
- **Response**: 
  ```json
  {
    "count": 42
  }
  ```

#### Peek Collection
- **GET** `/api/documents/collections/{collection_name}/peek?limit=10`
- **Response**: First few documents in the collection

### Health Check

#### Check Database Health
- **GET** `/api/documents/health`
- **Response**: 
  ```json
  {
    "status": "healthy",
    "heartbeat": 12345
  }
  ```

## Error Responses

All endpoints may return the following error responses:

- **400 Bad Request**: Invalid input data
- **404 Not Found**: Collection or document not found
- **500 Internal Server Error**: Server-side error

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Examples

### Creating a collection and adding documents

```bash
# Create a collection
curl -X POST http://localhost:8000/api/documents/collections \
  -H "Content-Type: application/json" \
  -d '{"name": "articles", "metadata": {"type": "news"}}'

# Add documents
curl -X POST http://localhost:8000/api/documents/collections/articles/documents \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["article1", "article2"],
    "documents": ["First article content", "Second article content"],
    "metadatas": [
      {"category": "tech", "date": "2024-01-01"},
      {"category": "science", "date": "2024-01-02"}
    ]
  }'

# Query documents
curl -X POST http://localhost:8000/api/documents/collections/articles/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_texts": ["technology news"],
    "n_results": 5,
    "where": {"category": "tech"}
  }'
```

## Notes

- Collection names must be 3-63 characters long and follow ChromaDB naming rules
- Documents can be added with either text (which will be auto-embedded) or pre-computed embeddings
- Metadata filtering supports various operators (see ChromaDB documentation)
- The database uses persistent storage in the `./vectordb` directory