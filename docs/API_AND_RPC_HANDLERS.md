# Syft Agent API and RPC Handlers Reference

## Table of Contents
1. [Introduction](#introduction)
2. [HTTP Endpoints](#http-endpoints)
   - [Root Endpoint (`/`)](#root-endpoint)
   - [API Endpoint (`/api`)](#api-endpoint)
3. [RPC Handlers](#rpc-handlers)
   - [Ping Handler (`/ping`)](#ping-handler)
4. [Integration with FastSyftbox](#integration-with-fastsyftbox)
   - [Setting Up RPC Handlers](#setting-up-rpc-handlers)
   - [Adding New RPC Handlers](#adding-new-rpc-handlers)
5. [Example Usage](#example-usage)
   - [Accessing HTTP Endpoints](#accessing-http-endpoints)
   - [Calling RPC Handlers](#calling-rpc-handlers)
6. [Error Handling](#error-handling)
7. [Security Considerations](#security-considerations)

## Introduction

Syft Agent provides two main interfaces for interaction:

1. **HTTP Endpoints**: REST API endpoints accessible via standard HTTP requests
2. **RPC Handlers**: Remote Procedure Call handlers for Syft-specific communication

This document serves as a comprehensive reference for all available endpoints and handlers, their parameters, return types, and usage examples.

## HTTP Endpoints

HTTP endpoints are implemented using FastAPI and can be found in `modules/http/routes.py`.

### Root Endpoint

**URL**: `/`  
**Method**: `GET`  
**Handler**: `read_root()`  
**Response**: HTML page  
**Content Type**: `text/html`

**Description**:  
The root endpoint renders the index template, providing a welcome page for the Syft Agent web interface.

**Implementation**:
```python
@router.get("/", response_class=HTMLResponse)
def read_root(request: Request) -> HTMLResponse:
    """Root endpoint that renders the index template."""
    context = {
        "request": request,
        "current_year": datetime.now(tz=timezone.utc).year,
    }
    return templates.TemplateResponse("index.html", context)
```

**Parameters**:
- `request`: The FastAPI request object (injected automatically)

**Response Example**:
```html
<!DOCTYPE html>
<html>
  <head>
    <title>Syft Agent</title>
    <!-- ... -->
  </head>
  <body>
    <h1>Welcome to Syft Agent</h1>
    <!-- ... -->
    <footer>&copy; 2023 Syft Agent</footer>
  </body>
</html>
```

### API Endpoint

**URL**: `/api`  
**Method**: `GET`  
**Handler**: `read_api()`  
**Response**: JSON object  
**Content Type**: `application/json`

**Description**:  
A simple API endpoint that returns a welcome message in JSON format. This can be used to check if the API is running.

**Implementation**:
```python
@router.get("/api")
def read_api() -> dict:
    """API endpoint that returns a welcome message as JSON."""
    return {"message": "Welcome to fastsyftbox API"}
```

**Parameters**:
- None

**Response Example**:
```json
{
  "message": "Welcome to fastsyftbox API"
}
```

## RPC Handlers

RPC handlers are implemented in `modules/rpc/handlers.py` and are registered with the Syftbox instance in `app.py`.

### Ping Handler

**Endpoint**: `/ping`  
**Handler**: `ping_handler()`  
**Input Type**: `Any`  
**Return Type**: `dict[str, str]`

**Description**:  
A simple handler that responds to ping requests with a "pong" message. This can be used to check if the RPC interface is operational.

**Implementation**:
```python
def ping_handler(_ping: Any) -> dict[str, str]:
    """Handler for the ping RPC endpoint.

    Args:
        _ping: The incoming ping request

    Returns:
        A dictionary with a pong message
    """
    return {"message": "pong"}
```

**Parameters**:
- `_ping`: The incoming ping request (not used in the implementation)

**Response Example**:
```json
{
  "message": "pong"
}
```

## Integration with FastSyftbox

The Syft Agent integrates with FastSyftbox to handle RPC communication. This integration is set up in `app.py`.

### Setting Up RPC Handlers

The main application initializes a Syftbox instance and registers RPC handlers with it:

```python
from fastapi import FastAPI
from fastsyftbox import Syftbox
from modules.rpc.handlers import ping_handler

# Create FastAPI app
app = FastAPI()

# Initialize Syftbox
syftbox = Syftbox(
    app=app,
    name=Path(__file__).resolve().parent.name,
)

# Register RPC endpoints
syftbox.on_request("/ping")(ping_handler)
```

### Adding New RPC Handlers

To add a new RPC handler, follow these steps:

1. Define the handler function in `modules/rpc/handlers.py`:
```python
def my_new_handler(request: dict[str, Any]) -> dict[str, Any]:
    """Handler for a new RPC endpoint.

    Args:
        request: The incoming request data

    Returns:
        A dictionary with the response data
    """
    # Process the request
    result = process_request(request)
    
    # Return the response
    return {"status": "success", "data": result}
```

2. Register the handler in `app.py`:
```python
from modules.rpc.handlers import ping_handler, my_new_handler

# Register RPC endpoints
syftbox.on_request("/ping")(ping_handler)
syftbox.on_request("/my/new/endpoint")(my_new_handler)
```

## Example Usage

### Accessing HTTP Endpoints

**Using curl**:
```bash
# Access the root endpoint
curl -X GET http://localhost:8080/

# Access the API endpoint
curl -X GET http://localhost:8080/api
```

**Using Python requests**:
```python
import requests

# Base URL for the Syft Agent
base_url = "http://localhost:8080"

# Access the API endpoint
response = requests.get(f"{base_url}/api")
data = response.json()
print(data)  # {"message": "Welcome to fastsyftbox API"}
```

### Calling RPC Handlers

**Using Syft-Core Client**:
```python
from syft_core import Client, SyftClientConfig

# Configure client
config = SyftClientConfig(
    email="user@example.com",
    server_url="http://localhost:8080"
)
client = Client(config)

# Call the ping endpoint
response = client.call_rpc("/ping", {})
print(response)  # {"message": "pong"}
```

**Using Direct RPC**:
```python
from syft_rpc import send

# Send a request to the ping endpoint
future = send(
    url="http://localhost:8080/ping",
    method="POST",
    body={}
)

# Wait for the response
response = future.wait()
print(response.body)  # {"message": "pong"}
```

## Error Handling

Both HTTP endpoints and RPC handlers should follow consistent error handling patterns:

1. **HTTP Error Responses**:
   - Use appropriate HTTP status codes (400 for client errors, 500 for server errors)
   - Return structured error messages with `error` and `message` fields

Example:
```python
from fastapi import HTTPException

@router.get("/api/resource/{id}")
def get_resource(id: str):
    try:
        resource = find_resource(id)
        if not resource:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Resource {id} not found"}
            )
        return resource
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "server_error", "message": str(e)}
        )
```

2. **RPC Error Handling**:
   - Return error information in the response body
   - Use consistent error fields (`success`, `error`, `message`)

Example:
```python
def data_handler(request: dict) -> dict:
    try:
        # Process request
        result = process_data(request)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": "invalid_input", "message": str(e)}
    except Exception as e:
        return {"success": False, "error": "server_error", "message": str(e)}
```

## Security Considerations

When implementing new HTTP endpoints or RPC handlers, keep the following security considerations in mind:

1. **Input Validation**:
   - Validate all input parameters
   - Use strong typing where possible
   - Sanitize user input to prevent injection attacks

2. **Authentication and Authorization**:
   - Ensure endpoints enforce appropriate authentication
   - Check user permissions before allowing access
   - Document authentication requirements for each endpoint

3. **Rate Limiting**:
   - Consider implementing rate limiting for public-facing endpoints
   - Prevent abuse through excessive requests

4. **Secure Communication**:
   - Use HTTPS for all production deployments
   - Consider encrypting sensitive data in RPC payloads

Example of secure endpoint implementation:
```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validate token and return user
    # ...

@router.get("/api/protected")
def protected_endpoint(current_user = Depends(get_current_user)):
    # Only accessible with valid authentication
    return {"message": "You have access", "user": current_user.username}
```

---

This reference documentation covers the current API endpoints and RPC handlers in the Syft Agent. As the application evolves, make sure to update this document with new endpoints and handlers to maintain a comprehensive reference for developers.