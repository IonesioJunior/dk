from typing import Any

from fastapi import APIRouter

router = APIRouter()

# Global variable to store agent reference
_agent = None


def set_agent(agent) -> None:
    """Set the agent instance for this module."""
    global _agent
    _agent = agent


@router.get("/provider")
async def get_config_provider() -> dict[str, Any]:
    """GET /api/config/provider endpoint"""
    if _agent is None:
        return {"error": "Agent not initialized"}
    return _agent.get_config()


@router.patch("/provider")
async def patch_config_provider(data: dict[str, Any]) -> dict[str, Any]:
    """PATCH /api/config/provider endpoint"""
    if _agent is None:
        return {"status": "error", "message": "Agent not initialized"}

    # Update agent configuration
    return _agent.update_config(data)


@router.get("/mcp")
async def get_config_mcp() -> dict[str, Any]:
    """GET /api/config/mcp endpoint"""
    # Implementation placeholder
    return {"mcp": "config_mcp_data"}


@router.patch("/mcp")
async def patch_config_mcp(data: dict[str, Any]) -> dict[str, Any]:
    """PATCH /api/config/mcp endpoint"""
    # Implementation placeholder
    return {"status": "mcp_config_updated", "data": data}
