from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from api_configs.models import APIConfig, APIConfigUpdate
from services.api_config_service import APIConfigService
from dependencies import get_api_config_service


router = APIRouter(prefix="/api_configs", tags=["api_configs"])


class APIConfigCreateRequest(BaseModel):
    users: List[str]
    datasets: List[str]


class APIConfigUpdateRequest(BaseModel):
    users: List[str] = None
    datasets: List[str] = None


class APIConfigResponse(BaseModel):
    id: str
    users: List[str]
    datasets: List[str]
    created_at: str
    updated_at: str
    
    @classmethod
    def from_api_config(cls, api_config: APIConfig) -> "APIConfigResponse":
        return cls(
            id=api_config.id,
            users=api_config.users,
            datasets=api_config.datasets,
            created_at=api_config.created_at.isoformat(),
            updated_at=api_config.updated_at.isoformat()
        )


# API config service will be injected from dependencies


@router.post("")
async def create_api_config(request: APIConfigCreateRequest):
    api_config_service = get_api_config_service()
    api_config = api_config_service.create_api_config(request.users, request.datasets)
    return APIConfigResponse.from_api_config(api_config)


@router.get("/{api_config_id}")
async def get_api_config(api_config_id: str):
    api_config_service = get_api_config_service()
    api_config = api_config_service.get_api_config(api_config_id)
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")
    return APIConfigResponse.from_api_config(api_config)


@router.get("")
async def get_all_api_configs():
    api_config_service = get_api_config_service()
    api_configs = api_config_service.get_all_api_configs()
    return [APIConfigResponse.from_api_config(api_config) for api_config in api_configs]


@router.put("/{api_config_id}")
async def update_api_config(api_config_id: str, request: APIConfigUpdateRequest):
    api_config_service = get_api_config_service()
    api_config_update = APIConfigUpdate(users=request.users, datasets=request.datasets)
    api_config = api_config_service.update_api_config(api_config_id, api_config_update)
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")
    return APIConfigResponse.from_api_config(api_config)


@router.delete("/{api_config_id}")
async def delete_api_config(api_config_id: str):
    api_config_service = get_api_config_service()
    if not api_config_service.delete_api_config(api_config_id):
        raise HTTPException(status_code=404, detail="API configuration not found")
    return {"message": "API configuration deleted successfully"}