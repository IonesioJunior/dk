# Syft-RPC: Comprehensive Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Architecture Overview](#architecture-overview)
4. [Core Components](#core-components)
5. [Usage Guide](#usage-guide)
6. [Integration with Syft Agent](#integration-with-syft-agent)
7. [Advanced Features](#advanced-features)
8. [API Reference](#api-reference)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

## Introduction

Syft-RPC is a Remote Procedure Call (RPC) implementation for the OpenMined Syft ecosystem, enabling secure and efficient communication between distributed components. It provides a framework for executing operations on remote systems while maintaining the privacy and security guarantees that are central to the Syft platform.

### Key Features

- **Asynchronous Communication**: Non-blocking operations using futures
- **Secure Messaging**: End-to-end message security
- **Multiple Transport Options**: Support for HTTP and filesystem-based transport
- **Bulk Operations**: Efficient handling of multiple concurrent requests
- **Request Tracking**: Persistent tracking of request state
- **Extensible Architecture**: Easy integration with different Syft components

## Installation

To install Syft-RPC, you can use pip:

```bash
pip install syft[rpc]
```

For development environments, you can install directly from the repository:

```bash
git clone https://github.com/OpenMined/syft-extras.git
cd syft-extras/packages/syft-rpc
pip install -e .
```

### Dependencies

- pydantic (>= 2.9.2)
- syft-core (== 0.1.0)
- typing-extensions (>= 4.12.2)

## Architecture Overview

Syft-RPC follows a client-server architecture with the following components:

1. **Protocol Layer**: Defines the message structure and serialization
2. **Transport Layer**: Handles message delivery (HTTP, filesystem)
3. **Future Management**: Tracks request state and handles responses
4. **Database Layer**: Persists futures and their states

![Syft-RPC Architecture](https://openmined.org/syft-rpc-architecture.svg)

The flow of a typical RPC operation:

1. Client creates a request
2. Transport layer delivers the request to the server
3. Server processes the request and generates a response
4. Transport layer returns the response to the client
5. Future object resolves with the response

## Core Components

### SyftMessage, SyftRequest, and SyftResponse

The foundation of Syft-RPC is the message system, which consists of three main types:

1. **SyftMessage**: Base class for all messages
2. **SyftRequest**: Extension of SyftMessage for client requests
3. **SyftResponse**: Extension of SyftMessage for server responses

Example message structure:

```python
# Request
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "request",
    "method": "GET",
    "url": "http://example.com/endpoint",
    "headers": {"content-type": "application/json"},
    "body": {"key": "value"},
    "timestamp": "2023-04-01T12:34:56.789Z"
}

# Response
{
    "id": "550e8400-e29b-41d4-a716-446655440000",  # Same ID as request
    "type": "response",
    "status_code": 200,
    "headers": {"content-type": "application/json"},
    "body": {"result": "success"},
    "timestamp": "2023-04-01T12:35:01.234Z"
}
```

### Futures: SyftFuture and SyftBulkFuture

Futures represent pending operations and allow for asynchronous processing:

1. **SyftFuture**: Represents a single pending request
2. **SyftBulkFuture**: Represents multiple pending requests

### Database Handling: RPC_DB

The `rpc_db.py` module provides persistent storage for futures:

- Uses SQLite for storage
- Automatically cleans up expired futures
- Provides CRUD operations for future management

## Usage Guide

### Basic Request-Response

```python
from syft_rpc import send, SyftRequest

# Send a simple request
future = send(
    url="http://example.com/api/resource",
    method="GET",
    headers={"Authorization": "Bearer token123"}
)

# Wait for response (blocking)
response = future.wait()

# Access response data
if response.status_code == 200:
    result = response.body
    print(f"Success: {result}")
else:
    print(f"Error: {response.status_code}")

# Send request with a body
future = send(
    url="http://example.com/api/resource",
    method="POST",
    body={"name": "test", "value": 42}
)
```

### Asynchronous Operations

```python
from syft_rpc import send

# Send multiple requests without blocking
future1 = send(url="http://example.com/api/resource1")
future2 = send(url="http://example.com/api/resource2")

# Do other work...

# Check if responses are ready
if future1.is_done():
    response1 = future1.result()
    
# Process when both are ready
response1 = future1.wait()
response2 = future2.wait()
```

### Broadcasting to Multiple Endpoints

```python
from syft_rpc import broadcast

# Send to multiple endpoints
endpoints = [
    "http://server1.example.com/api",
    "http://server2.example.com/api",
    "http://server3.example.com/api"
]

bulk_future = broadcast(
    urls=endpoints,
    method="POST",
    body={"action": "synchronize", "timestamp": 1680355351}
)

# Wait for all responses
responses = bulk_future.wait()

# Process each response
for endpoint, response in zip(endpoints, responses):
    print(f"Endpoint: {endpoint}, Status: {response.status_code}")
```

### Creating Responses on the Server Side

```python
from syft_rpc import reply_to

def handle_request(request):
    # Process the request
    user_id = request.body.get("user_id")
    data = retrieve_user_data(user_id)
    
    # Create a response
    return reply_to(
        request, 
        status_code=200,
        body={"user": user_id, "data": data}
    )
```

## Integration with Syft Agent

Syft-RPC integrates seamlessly with the Syft Agent framework, which provides a higher-level interface for privacy-preserving machine learning and data operations.

### Setting Up Syft Agent with RPC

```python
from fastapi import FastAPI
from fastsyftbox import Syftbox

# Create FastAPI app
app = FastAPI()

# Initialize Syftbox with RPC support
syftbox = Syftbox(
    app=app,
    name="my-syft-agent",
)

# Register RPC endpoint handlers
@syftbox.on_request("/ping")
def ping_handler(_ping: Any) -> dict[str, str]:
    """Handler for the ping RPC endpoint."""
    return {"message": "pong"}

# Register custom data handlers
@syftbox.on_request("/documents/search")
def search_documents_handler(request: dict) -> dict:
    """Handle document search requests."""
    query = request.get("query", "")
    limit = request.get("limit", 10)
    
    # Use document search functionality
    results = search_documents(query, limit=limit)
    
    # Format and return results
    return {
        "query": query,
        "count": len(results),
        "results": [doc.to_dict() for doc, score in results]
    }
```

### Accessing RPC Endpoints from Clients

```python
from syft_core import Client, SyftClientConfig

# Configure client
config = SyftClientConfig(
    email="user@example.com",
    server_url="https://syftbox.example.com"
)
client = Client(config)

# Call RPC endpoints
response = client.call_rpc("/ping", {})
print(response)  # {"message": "pong"}

# Call document search endpoint
results = client.call_rpc("/documents/search", {
    "query": "machine learning",
    "limit": 5
})
```

## Advanced Features

### Custom Serialization

Syft-RPC supports custom serialization for complex objects:

```python
from syft_rpc.protocol import register_serializer, register_deserializer

# Register custom serializers
@register_serializer(MyCustomClass)
def serialize_custom(obj):
    return {"__custom__": True, "data": obj.to_dict()}

@register_deserializer(MyCustomClass)
def deserialize_custom(data):
    return MyCustomClass.from_dict(data["data"])
```

### Timeout Configuration

Control request timeouts for better error handling:

```python
from syft_rpc import send
from datetime import timedelta

# Set timeout for the request
future = send(
    url="http://slow-server.example.com/api",
    timeout=timedelta(seconds=30)  # 30-second timeout
)

try:
    response = future.wait()
    print(f"Response received: {response.body}")
except TimeoutError:
    print("Request timed out")
```

### Advanced Filtering with Futures

```python
from syft_rpc import send, bulk_get_futures

# Send multiple requests
futures = [
    send(url=f"http://example.com/api/item/{i}")
    for i in range(1, 100)
]

# Get only completed futures
completed = bulk_get_futures(futures, only_completed=True)

# Get only futures with success responses
successful = bulk_get_futures(
    futures, 
    filter_func=lambda f: f.is_done() and f.result().status_code == 200
)
```

## API Reference

### Core Functions

#### `send()`

Sends a request to a remote endpoint.

**Parameters:**
- `url` (str): The endpoint URL
- `method` (str, optional): HTTP method (GET, POST, etc.). Default: "GET"
- `headers` (dict, optional): Request headers
- `body` (Any, optional): Request body
- `timeout` (timedelta, optional): Request timeout

**Returns:**
- `SyftFuture`: Future object representing the pending request

#### `broadcast()`

Sends a request to multiple endpoints.

**Parameters:**
- `urls` (List[str]): List of endpoint URLs
- `method` (str, optional): HTTP method. Default: "GET"
- `headers` (dict, optional): Request headers
- `body` (Any, optional): Request body
- `timeout` (timedelta, optional): Request timeout

**Returns:**
- `SyftBulkFuture`: Future object representing multiple pending requests

#### `reply_to()`

Creates a response to a specific request.

**Parameters:**
- `request` (SyftRequest): The original request
- `status_code` (int, optional): Response status code. Default: 200
- `headers` (dict, optional): Response headers
- `body` (Any, optional): Response body

**Returns:**
- `SyftResponse`: The response object

### Future Methods

#### `SyftFuture.wait()`

Waits for the request to complete.

**Parameters:**
- `timeout` (timedelta, optional): Maximum time to wait

**Returns:**
- `SyftResponse`: The response object

#### `SyftFuture.is_done()`

Checks if the request has completed.

**Returns:**
- `bool`: True if complete, False otherwise

#### `SyftFuture.result()`

Gets the result if available.

**Returns:**
- `SyftResponse`: The response object
- `None`: If not yet complete

#### `SyftBulkFuture.wait()`

Waits for all requests to complete.

**Parameters:**
- `timeout` (timedelta, optional): Maximum time to wait

**Returns:**
- `List[SyftResponse]`: List of response objects

## Examples

### Document Management with ChromaDB

This example shows how to use Syft-RPC with ChromaDB for document storage and retrieval:

```python
from syft_rpc import send
from datetime import datetime

# Function to store a document
def store_document(server_url, content, metadata=None):
    metadata = metadata or {}
    metadata["created_at"] = datetime.now().isoformat()
    
    # Send document to server
    future = send(
        url=f"{server_url}/documents/store",
        method="POST",
        body={
            "content": content,
            "metadata": metadata
        }
    )
    
    # Wait for response
    response = future.wait()
    if response.status_code == 200:
        return response.body.get("document_id")
    else:
        raise Exception(f"Failed to store document: {response.body}")

# Function to search documents
def search_documents(server_url, query, limit=10):
    future = send(
        url=f"{server_url}/documents/search",
        method="GET",
        body={
            "query": query,
            "limit": limit
        }
    )
    
    response = future.wait()
    if response.status_code == 200:
        return response.body.get("results", [])
    else:
        raise Exception(f"Search failed: {response.body}")

# Usage example
server_url = "http://syft-agent.example.com"
doc_id = store_document(
    server_url,
    "Machine learning is a field of study that gives computers the ability to learn without being explicitly programmed.",
    {"category": "technology", "tags": ["ML", "AI"]}
)

results = search_documents(server_url, "machine learning")
for doc in results:
    print(f"Document: {doc['id']}")
    print(f"Content: {doc['content'][:100]}...")
    print(f"Similarity: {doc['similarity']}")
    print()
```

### Distributed Data Processing

Example of distributing work across multiple nodes:

```python
from syft_rpc import broadcast

def process_data_distributed(data_chunks, worker_urls):
    """Process data chunks across multiple workers."""
    # Split data into chunks for each worker
    tasks = []
    for i, worker_url in enumerate(worker_urls):
        chunk = data_chunks[i % len(data_chunks)]
        tasks.append({
            "url": worker_url,
            "body": {
                "action": "process",
                "data": chunk
            }
        })
    
    # Send all tasks
    bulk_future = broadcast(
        urls=[task["url"] for task in tasks],
        method="POST",
        bodies=[task["body"] for task in tasks]
    )
    
    # Wait for all results
    responses = bulk_future.wait()
    
    # Combine results
    combined_results = []
    for response in responses:
        if response.status_code == 200:
            combined_results.extend(response.body.get("results", []))
    
    return combined_results
```

## Troubleshooting

### Common Issues

1. **Request Timeout**
   - Ensure network connectivity to the endpoint
   - Check if the server is running and responsive
   - Consider increasing the timeout value

2. **Serialization Errors**
   - Ensure all data types in the request body can be serialized
   - Register custom serializers for complex objects
   - Check for circular references in objects

3. **Future Not Resolving**
   - Verify the endpoint URL is correct
   - Check server logs for errors
   - Ensure the response is properly formatted

### Debugging

Enable debug logging to see detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Configure syft_rpc logger
logger = logging.getLogger("syft_rpc")
logger.setLevel(logging.DEBUG)
```

### Support Resources

- [GitHub Repository](https://github.com/OpenMined/syft-extras/tree/main/packages/syft-rpc)
- [OpenMined Documentation](https://docs.openmined.org)
- [OpenMined Community Support](https://slack.openmined.org)

## Conclusion

Syft-RPC provides a robust framework for building distributed applications within the OpenMined ecosystem. By combining secure communication, asynchronous processing, and seamless integration with other Syft components, it enables powerful privacy-preserving applications and workflows.

Whether you're building a simple client-server application or a complex distributed system, Syft-RPC offers the tools and flexibility needed to implement secure and efficient remote procedure calls while maintaining the privacy guarantees that are central to the OpenMined mission.