from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api_configs.models import APIConfig, APIConfigUpdate
from api_configs.usage_tracker import APIConfigMetrics
from dependencies import get_api_config_service

router = APIRouter(prefix="/api_configs", tags=["api_configs"])


class APIConfigCreateRequest(BaseModel):
    users: list[str]
    datasets: list[str]


class APIConfigUpdateRequest(BaseModel):
    users: list[str] = None
    datasets: list[str] = None


class APIConfigResponse(BaseModel):
    id: str
    users: list[str]
    datasets: list[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_api_config(cls, api_config: APIConfig) -> "APIConfigResponse":
        return cls(
            id=api_config.id,
            users=api_config.users,
            datasets=api_config.datasets,
            created_at=api_config.created_at.isoformat(),
            updated_at=api_config.updated_at.isoformat(),
        )


class APIUsageMetricsResponse(BaseModel):
    api_config_id: str
    total_requests: int
    total_input_size: int
    total_output_size: int
    user_frequency: dict[str, int]
    last_updated: str

    @classmethod
    def from_metrics(cls, metrics: APIConfigMetrics) -> "APIUsageMetricsResponse":
        return cls(
            api_config_id=metrics.api_config_id,
            total_requests=metrics.total_requests,
            total_input_size=metrics.total_input_size,
            total_output_size=metrics.total_output_size,
            user_frequency=metrics.user_frequency,
            last_updated=metrics.last_updated.isoformat(),
        )


# API config service will be injected from dependencies


@router.post("")
async def create_api_config(request: APIConfigCreateRequest) -> APIConfigResponse:
    api_config_service = get_api_config_service()
    try:
        api_config = api_config_service.create_api_config(
            request.users, request.datasets
        )
        return APIConfigResponse.from_api_config(api_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{api_config_id}")
async def get_api_config(api_config_id: str) -> APIConfigResponse:
    api_config_service = get_api_config_service()
    api_config = api_config_service.get_api_config(api_config_id)
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")
    return APIConfigResponse.from_api_config(api_config)


@router.get("")
async def get_all_api_configs() -> list[APIConfigResponse]:
    api_config_service = get_api_config_service()
    api_configs = api_config_service.get_all_api_configs()
    return [APIConfigResponse.from_api_config(api_config) for api_config in api_configs]


@router.put("/{api_config_id}")
async def update_api_config(
    api_config_id: str, request: APIConfigUpdateRequest
) -> APIConfigResponse:
    api_config_service = get_api_config_service()
    api_config_update = APIConfigUpdate(users=request.users, datasets=request.datasets)
    try:
        api_config = api_config_service.update_api_config(
            api_config_id, api_config_update
        )
        if not api_config:
            raise HTTPException(status_code=404, detail="API configuration not found")
        return APIConfigResponse.from_api_config(api_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{api_config_id}")
async def delete_api_config(api_config_id: str) -> dict[str, str]:
    api_config_service = get_api_config_service()
    if not api_config_service.delete_api_config(api_config_id):
        raise HTTPException(status_code=404, detail="API configuration not found")
    return {"message": "API configuration deleted successfully"}


@router.get("/{api_config_id}/usage")
async def get_api_config_usage(
    api_config_id: str,
) -> APIUsageMetricsResponse | dict[str, Any]:
    """Get usage metrics for a specific API configuration"""
    api_config_service = get_api_config_service()

    # First verify the API config exists
    api_config = api_config_service.get_api_config(api_config_id)
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")

    metrics = api_config_service.get_api_usage_metrics(api_config_id)
    if not metrics:
        # Return empty metrics if none exist yet
        return {
            "api_config_id": api_config_id,
            "total_requests": 0,
            "total_input_size": 0,
            "total_output_size": 0,
            "user_frequency": {},
            "last_updated": None,
        }

    return APIUsageMetricsResponse.from_metrics(metrics)


@router.get("/{api_config_id}/top-users")
async def get_api_config_top_users(
    api_config_id: str, limit: int = 10
) -> dict[str, list[dict[str, Any]]]:
    """Get the top users for a specific API configuration"""
    api_config_service = get_api_config_service()

    # First verify the API config exists
    api_config = api_config_service.get_api_config(api_config_id)
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")

    top_users = api_config_service.get_top_api_users(api_config_id, limit)
    user_list = [{"user_id": user_id, "count": count} for user_id, count in top_users]
    return {"top_users": user_list}


@router.get("/usage")
async def get_all_api_configs_usage() -> list[APIUsageMetricsResponse]:
    """Get usage metrics for all API configurations"""
    api_config_service = get_api_config_service()
    metrics_list = api_config_service.get_all_api_usage_metrics()

    return [APIUsageMetricsResponse.from_metrics(metrics) for metrics in metrics_list]
