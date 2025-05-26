from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api_configs.models import APIConfig, APIConfigUpdate
from api_configs.usage_tracker import APIConfigMetrics
from dependencies import get_api_config_service
from policies.repository import PolicyRepository

router = APIRouter(tags=["api_configs"])


class APIConfigCreateRequest(BaseModel):
    users: list[str]
    datasets: list[str]


class APIConfigUpdateRequest(BaseModel):
    users: list[str] = None
    datasets: list[str] = None


class APIConfigResponse(BaseModel):
    config_id: str
    users: list[str]
    datasets: list[str]
    created_at: str
    updated_at: str
    policy_id: Optional[str] = None
    policy_name: Optional[str] = None

    @classmethod
    def from_api_config(
        cls: type["APIConfigResponse"],
        api_config: APIConfig,
        policy_id: Optional[str] = None,
        policy_name: Optional[str] = None,
    ) -> "APIConfigResponse":
        return cls(
            config_id=api_config.config_id,
            users=api_config.users,
            datasets=api_config.datasets,
            created_at=api_config.created_at.isoformat(),
            updated_at=api_config.updated_at.isoformat(),
            policy_id=policy_id,
            policy_name=policy_name,
        )


class APIUsageMetricsResponse(BaseModel):
    api_config_id: str
    total_requests: int
    total_input_word_count: int
    total_output_word_count: int
    user_frequency: dict[str, int]
    last_updated: str

    @classmethod
    def from_metrics(
        cls: type["APIUsageMetricsResponse"], metrics: APIConfigMetrics
    ) -> "APIUsageMetricsResponse":
        return cls(
            api_config_id=metrics.api_config_id,
            total_requests=metrics.total_requests,
            total_input_word_count=metrics.total_input_word_count,
            total_output_word_count=metrics.total_output_word_count,
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
        # New configs don't have policies attached yet
        return APIConfigResponse.from_api_config(api_config, None, None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/usage")
async def get_all_api_configs_usage() -> list[APIUsageMetricsResponse]:
    """Get usage metrics for all API configurations"""
    api_config_service = get_api_config_service()
    metrics_list = api_config_service.get_all_api_usage_metrics()

    return [APIUsageMetricsResponse.from_metrics(metrics) for metrics in metrics_list]


@router.get("")
async def get_all_api_configs() -> list[APIConfigResponse]:
    api_config_service = get_api_config_service()
    api_configs = api_config_service.get_all_api_configs()

    # Get policy information for each API config
    policy_repo = PolicyRepository()
    response_list = []

    for api_config in api_configs:
        policy_id = policy_repo.get_policy_for_api(api_config.config_id)
        policy_name = None

        if policy_id:
            policy = policy_repo.get(policy_id)
            if policy:
                policy_name = policy.name

        response_list.append(
            APIConfigResponse.from_api_config(api_config, policy_id, policy_name)
        )

    return response_list


@router.get("/{api_config_id}")
async def get_api_config(api_config_id: str) -> APIConfigResponse:
    api_config_service = get_api_config_service()
    api_config = api_config_service.get_api_config(api_config_id)
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")

    # Get policy information
    policy_repo = PolicyRepository()
    policy_id = policy_repo.get_policy_for_api(api_config_id)
    policy_name = None

    if policy_id:
        policy = policy_repo.get(policy_id)
        if policy:
            policy_name = policy.name

    return APIConfigResponse.from_api_config(api_config, policy_id, policy_name)


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

        # Get policy information
        policy_repo = PolicyRepository()
        policy_id = policy_repo.get_policy_for_api(api_config_id)
        policy_name = None

        if policy_id:
            policy = policy_repo.get(policy_id)
            if policy:
                policy_name = policy.name

        return APIConfigResponse.from_api_config(api_config, policy_id, policy_name)
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
            "total_input_word_count": 0,
            "total_output_word_count": 0,
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

    # Get metrics to access per-user word counts
    metrics = api_config_service.get_api_usage_metrics(api_config_id)
    if not metrics:
        return {"top_users": []}

    # Get top users and include their word counts
    top_users = api_config_service.get_top_api_users(api_config_id, limit)
    user_list = []
    for user_id, count in top_users:
        user_data = {
            "user_id": user_id,
            "count": count,
            "input_words": metrics.user_input_words.get(user_id, 0),
            "output_words": metrics.user_output_words.get(user_id, 0),
        }
        user_list.append(user_data)

    return {"top_users": user_list}
