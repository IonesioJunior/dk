from fastapi import APIRouter

from .endpoints import agent, config, documents, frontend

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

# Include all API endpoints under /api prefix
api_router.include_router(api_endpoints, prefix="/api")
