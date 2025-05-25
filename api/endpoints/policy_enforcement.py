"""Policy enforcement for API endpoints."""

import json
import logging
from typing import Any, Optional

from fastapi import Cookie, Depends, HTTPException, Request

from dependencies import (
    get_api_config_manager,
    get_api_config_usage_tracker,
    get_policy_enforcer,
    get_websocket_client,
)
from policies.models import PolicyEvaluationResult

logger = logging.getLogger(__name__)

# Cookie name for user identification
USER_ID_COOKIE = "syft_user_id"


async def get_user_id_from_request(
    request: Request,
    user_id_cookie: Optional[str] = Cookie(default=None, alias=USER_ID_COOKIE),
) -> str:
    """Extract user ID from request (cookie, header, or WebSocket client)."""

    # Priority 1: Check cookie
    if user_id_cookie:
        return user_id_cookie

    # Priority 2: Check header
    if "X-User-Id" in request.headers:
        return request.headers["X-User-Id"]

    # Priority 3: Get from WebSocket client
    ws_client = get_websocket_client()
    if ws_client and ws_client.user_id:
        return ws_client.user_id

    # Priority 4: Check if user is in onboarding
    from api.endpoints.config import get_current_config

    config = get_current_config()
    if config and config.user:
        return config.user

    # Default to anonymous
    return "anonymous"


async def enforce_api_policy(
    request: Request, user_id: str = Depends(get_user_id_from_request)
) -> PolicyEvaluationResult:
    """FastAPI dependency for policy enforcement."""

    # Skip policy enforcement for certain endpoints
    if request.url.path in [
        "/api/config",
        "/api/onboarding",
        "/api/policies",  # Allow policy management endpoints
        "/api/active-users",
        "/api/prompt-responses",
        "/api/conversation-history",
        "/api/clear-conversation",
    ]:
        return PolicyEvaluationResult(allowed=True)

    # Get the user's API configuration
    api_config_manager = get_api_config_manager()
    api_config_id = api_config_manager.get_policy_for_user(user_id)

    if not api_config_id:
        # User has no API configuration - check if this is an onboarding flow
        if request.url.path.startswith("/api/onboarding"):
            return PolicyEvaluationResult(allowed=True)

        # For other endpoints, deny access
        raise HTTPException(
            status_code=403,
            detail="User has no API configuration. Please contact an administrator.",
        )

    # Get policy enforcer and evaluate
    policy_enforcer = get_policy_enforcer()

    try:
        result = await policy_enforcer.enforce_policy(
            api_config_id=api_config_id,
            user_id=user_id,
            request_context={
                "path": request.url.path,
                "method": request.method,
                "bypass_cache": request.headers.get(
                    "X-Bypass-Policy-Cache", "false"
                ).lower()
                == "true",
            },
        )

        if not result.allowed:
            # Log policy violation
            violations = [r.message for r in result.violated_rules]
            logger.warning(f"Policy violation for user {user_id}: {violations}")

            # Return detailed error
            error_messages = [
                rule.message for rule in result.violated_rules if rule.message
            ]
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Policy violation",
                    "messages": error_messages,
                    "remaining_quota": result.remaining_quota,
                },
            )

        # Add warnings to request state if any
        if result.warnings:
            request.state.policy_warnings = result.warnings

        # Add remaining quota to request state
        if result.remaining_quota:
            request.state.remaining_quota = result.remaining_quota

        # Store evaluation result in request state for usage tracking
        request.state.policy_result = result
        request.state.api_config_id = api_config_id
        request.state.user_id = user_id

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enforcing policy: {e}")
        # In case of error, allow the request but log it
        return PolicyEvaluationResult(allowed=True)


async def track_api_usage_after_request(
    request: Request, _response_data: Any, prompt: str, completion: Optional[str] = None
) -> None:
    """Track API usage after successful request."""

    # Check if we have the necessary data from policy enforcement
    if not hasattr(request.state, "api_config_id") or not hasattr(
        request.state, "user_id"
    ):
        logger.warning("Missing API config or user ID for usage tracking")
        return

    api_config_id = request.state.api_config_id
    user_id = request.state.user_id

    # Get usage tracker
    usage_tracker = get_api_config_usage_tracker()

    try:
        # Track the usage
        usage_tracker.track_usage(
            api_config_id=api_config_id,
            user_id=user_id,
            input_prompt=prompt,
            output_prompt=completion or "",
        )

        logger.info(f"Tracked API usage for user {user_id} on config {api_config_id}")

    except Exception as e:
        logger.error(f"Error tracking API usage: {e}")


def add_policy_headers(response: Any, request: Request) -> None:
    """Add policy-related headers to response."""

    # Add warnings if any
    if hasattr(request.state, "policy_warnings") and request.state.policy_warnings:
        response.headers["X-Policy-Warnings"] = json.dumps(
            request.state.policy_warnings
        )

    # Add remaining quota if available
    if hasattr(request.state, "remaining_quota") and request.state.remaining_quota:
        response.headers["X-Remaining-Quota"] = json.dumps(
            request.state.remaining_quota
        )
