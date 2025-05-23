"""API endpoints for onboarding process."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import ModelConfig, get_settings, reload_settings
from dependencies import get_agent
from startup.initialization import complete_onboarding_and_restart_services

logger = logging.getLogger(__name__)

router = APIRouter()


class OnboardingRequest(BaseModel):
    """Request model for completing onboarding."""

    syftbox_username: str
    llm_config: dict[str, Any]


class OnboardingStatus(BaseModel):
    """Response model for onboarding status."""

    onboarding: bool
    configured: bool
    syftbox_username: str | None = None
    has_llm_config: bool


@router.get("/onboarding/status", response_model=OnboardingStatus)
async def get_onboarding_status() -> OnboardingStatus:
    """Get current onboarding status."""
    settings = get_settings()
    get_agent()

    return OnboardingStatus(
        onboarding=settings.onboarding,
        configured=not settings.onboarding,
        syftbox_username=settings.syftbox_username,
        has_llm_config=settings.llm_config is not None,
    )


@router.post("/onboarding/complete")
async def complete_onboarding(request: OnboardingRequest) -> dict[str, Any]:
    """Complete the onboarding process."""
    try:
        settings = get_settings()

        if not settings.onboarding:
            raise HTTPException(status_code=400, detail="Onboarding already completed")

        # Validate model config
        try:
            ModelConfig(**request.llm_config)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid model configuration: {e!s}"
            ) from e

        # Complete onboarding
        await complete_onboarding_and_restart_services(
            request.syftbox_username, request.llm_config
        )

        # Reload settings to get updated values
        settings = reload_settings()

        return {
            "status": "success",
            "message": "Onboarding completed successfully",
            "onboarding": settings.onboarding,
            "configured": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing onboarding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/onboarding/providers")
async def get_available_providers() -> dict[str, list[str]]:
    """Get available LLM providers and their models."""
    return {
        "openai": [
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ],
        "anthropic": [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
        ],
        "ollama": [
            "llama2",
            "llama2:70b",
            "mistral",
            "gemma3:4b",
        ],
        "openrouter": [
            "openai/gpt-4",
            "anthropic/claude-3-opus",
            "google/gemini-pro",
            "meta-llama/llama-3-70b-instruct",
        ],
    }
