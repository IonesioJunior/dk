from typing import Any

from fastapi import APIRouter

from service_locator import service_locator

router = APIRouter()


def set_agent(agent: Any) -> None:
    """Set the agent instance for this module."""
    service_locator.register("agent", agent)


def get_agent() -> Any:
    """Get the agent instance for this module."""
    try:
        return service_locator.get("agent")
    except KeyError:
        return None


@router.get("/provider")
async def get_config_provider() -> dict[str, Any]:
    """GET /api/config/provider endpoint"""
    agent = get_agent()
    if agent is None:
        return {"error": "Agent not initialized"}
    return agent.get_config()


@router.patch("/provider")
async def patch_config_provider(data: dict[str, Any]) -> dict[str, Any]:
    """PATCH /api/config/provider endpoint"""
    agent = get_agent()
    if agent is None:
        return {"status": "error", "message": "Agent not initialized"}

    # Update agent configuration
    return agent.update_config(data)


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
