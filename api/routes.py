from fastapi import APIRouter

from .endpoints import (
    agent,
    config,
    documents,
    documents_collection,
    frontend,
    api_configs,
    active_users,
)

# Create the main router
api_router = APIRouter()

# Include the frontend router (no prefix - these are root routes)
api_router.include_router(frontend.router, tags=["frontend"])

# Create a sub-router for API endpoints with /api prefix
api_endpoints = APIRouter()

# Include the config router
api_endpoints.include_router(config.router, prefix="/config", tags=["config"])

# Include the agent router
api_endpoints.include_router(agent.router, tags=["agent"])

# Include the documents router
api_endpoints.include_router(documents.router, tags=["documents"])

api_endpoints.include_router(
    documents_collection.router,
    prefix="/documents-collection",
    tags=["documents-collection"],
)

# Include the API configs router
api_endpoints.include_router(api_configs.router, tags=["api_configs"])

# Include the active users router
api_endpoints.include_router(active_users.router, tags=["active_users"])

# Include all API endpoints under /api prefix
api_router.include_router(api_endpoints, prefix="/api")
