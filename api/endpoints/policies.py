"""Policy management API endpoints."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_policy_manager, get_policy_service
from policies.models import (
    PolicyType,
    PolicyUpdate,
    RuleOperator,
)

from .policy_enforcement import get_user_id_from_request

logger = logging.getLogger(__name__)

router = APIRouter()

# Operator mapping between frontend and backend formats
OPERATOR_MAPPING = {
    "less_than": "lt",
    "less_than_or_equal": "lte",
    "greater_than": "gt",
    "greater_than_or_equal": "gte",
    "equal": "eq",
    "not_equal": "ne",
}

# Reverse mapping for converting backend to frontend format
OPERATOR_DISPLAY_MAPPING = {v: k for k, v in OPERATOR_MAPPING.items()}

# Period mapping between frontend and backend formats
PERIOD_MAPPING = {
    "hourly": "hour",
    "daily": "day",
    "monthly": "month",
    "total": "lifetime",
}

# Reverse mapping for converting backend to frontend format
PERIOD_DISPLAY_MAPPING = {v: k for k, v in PERIOD_MAPPING.items()}


def transform_frontend_rule_to_domain(rule: dict[str, Any]) -> dict[str, Any]:
    """Transform a frontend rule format to domain model format."""
    if not rule:
        return rule

    transformed = rule.copy()

    # Get valid domain operators
    valid_domain_operators = [op.value for op in RuleOperator]

    # Convert frontend operator to backend operator
    if "operator" in transformed:
        if transformed["operator"] in OPERATOR_MAPPING:
            # It's a frontend operator, convert it
            transformed["operator"] = OPERATOR_MAPPING[transformed["operator"]]
        elif transformed["operator"] not in valid_domain_operators:
            # It's neither a frontend operator nor a valid domain operator
            valid_ops = list(OPERATOR_MAPPING.keys())
            raise ValueError(
                f"Invalid operator: {transformed['operator']}. "
                f"Valid operators are: {valid_ops}"
            )
        # Otherwise, it's already a valid domain operator, leave it as is

    # Convert frontend action 'block' to backend 'deny'
    if transformed.get("action") == "block":
        transformed["action"] = "deny"

    # Convert frontend period to backend period
    if "period" in transformed and transformed["period"] in PERIOD_MAPPING:
        transformed["period"] = PERIOD_MAPPING[transformed["period"]]

    return transformed


def transform_domain_rule_to_frontend(rule: dict[str, Any]) -> dict[str, Any]:
    """Transform a domain model rule to frontend format."""
    if not rule:
        return rule

    transformed = rule.copy()

    # Convert backend operator to frontend operator
    if (
        "operator" in transformed
        and transformed["operator"] in OPERATOR_DISPLAY_MAPPING
    ):
        transformed["operator"] = OPERATOR_DISPLAY_MAPPING[transformed["operator"]]

    # Convert backend action 'deny' to frontend 'block'
    if transformed.get("action") == "deny":
        transformed["action"] = "block"

    # Convert backend period to frontend period
    if "period" in transformed and transformed["period"] in PERIOD_DISPLAY_MAPPING:
        transformed["period"] = PERIOD_DISPLAY_MAPPING[transformed["period"]]

    return transformed


def transform_policy_response(policy_dict: dict[str, Any]) -> dict[str, Any]:
    """Transform policy response to frontend format."""
    if policy_dict.get("rules"):
        policy_dict["rules"] = [
            transform_domain_rule_to_frontend(rule) for rule in policy_dict["rules"]
        ]
    return policy_dict


class CreatePolicyRequest(BaseModel):
    """Request model for creating a policy."""

    name: str
    description: Optional[str] = None
    policy_type: PolicyType = PolicyType.COMBINED
    rules: Optional[list[dict[str, Any]]] = None
    settings: Optional[dict[str, Any]] = None


class UpdatePolicyRequest(BaseModel):
    """Request model for updating a policy."""

    name: Optional[str] = None
    description: Optional[str] = None
    policy_type: Optional[PolicyType] = None
    rules: Optional[list[dict[str, Any]]] = None
    is_active: Optional[bool] = None
    settings: Optional[dict[str, Any]] = None


class AttachPolicyRequest(BaseModel):
    """Request model for attaching a policy to an API configuration."""

    policy_id: str
    api_config_id: str


class MigratePoliciesRequest(BaseModel):
    """Request model for migrating API configs to a policy."""

    policy_id: str
    api_config_ids: list[str]


@router.post("/policies")
async def create_policy(
    request: CreatePolicyRequest, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """Create a new policy."""
    try:
        policy_service = get_policy_service()

        # Transform rules from frontend format to domain format
        transformed_rules = None
        if request.rules:
            logger.info(f"Original rules: {request.rules}")
            transformed_rules = [
                transform_frontend_rule_to_domain(rule) for rule in request.rules
            ]
            logger.info(f"Transformed rules: {transformed_rules}")

        # Create a new request with transformed rules
        transformed_request = CreatePolicyRequest(
            name=request.name,
            description=request.description,
            policy_type=request.policy_type,
            rules=transformed_rules,
            settings=request.settings,
        )

        # Create the policy
        policy = await policy_service.create_policy(transformed_request)

        logger.info(f"Created policy {policy.policy_id} by user {user_id}")

        # Transform response to frontend format
        policy_response = transform_policy_response(policy.to_dict())

        return {"status": "success", "policy": policy_response}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to create policy") from e


@router.get("/policies")
async def list_policies(
    active_only: bool = False, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """List all policies."""
    try:
        policy_manager = get_policy_manager()

        policies = policy_manager.list_policies(active_only=active_only)

        # Transform each policy to frontend format
        transformed_policies = [
            transform_policy_response(p.to_dict()) for p in policies
        ]

        logger.info(f"Listed {len(policies)} policies for user {user_id}")

        return {
            "status": "success",
            "policies": transformed_policies,
            "count": len(policies),
        }

    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail="Failed to list policies") from e


@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: str, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """Get a specific policy with detailed information."""
    try:
        policy_service = get_policy_service()

        summary = await policy_service.get_policy_summary(policy_id)

        if not summary:
            raise HTTPException(status_code=404, detail="Policy not found")

        # Transform the policy in the summary to frontend format
        if "policy" in summary:
            summary["policy"] = transform_policy_response(summary["policy"])

        logger.info(f"Retrieved policy {policy_id} details for user {user_id}")

        return {"status": "success", **summary}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy {policy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get policy") from e


@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    request: UpdatePolicyRequest,
    user_id: str = Depends(get_user_id_from_request),
) -> dict[str, Any]:
    """Update a policy."""
    try:
        policy_manager = get_policy_manager()

        # Create update object
        update = PolicyUpdate(
            name=request.name,
            description=request.description,
            type=request.policy_type,
            is_active=request.is_active,
            settings=request.settings,
        )

        # If rules are provided, transform and update them
        if request.rules is not None:
            policy_service = get_policy_service()

            # Transform rules from frontend format to domain format
            transformed_rules = [
                transform_frontend_rule_to_domain(rule) for rule in request.rules
            ]

            updated_policy = await policy_service.update_policy_rules(
                policy_id, transformed_rules
            )
        else:
            updated_policy = policy_manager.update_policy(policy_id, update)

        if not updated_policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        logger.info(f"Updated policy {policy_id} by user {user_id}")

        # Transform response to frontend format
        policy_response = transform_policy_response(updated_policy.to_dict())

        return {"status": "success", "policy": policy_response}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy {policy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update policy") from e


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """Delete a policy."""
    try:
        policy_manager = get_policy_manager()

        success = policy_manager.delete_policy(policy_id)

        if not success:
            raise HTTPException(status_code=404, detail="Policy not found")

        logger.info(f"Deleted policy {policy_id} by user {user_id}")

        return {
            "status": "success",
            "message": f"Policy {policy_id} deleted successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy {policy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete policy") from e


@router.post("/policies/attach")
async def attach_policy_to_api(
    request: AttachPolicyRequest, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """Attach a policy to an API configuration."""
    try:
        policy_service = get_policy_service()

        success = await policy_service.attach_policy_to_api_config(
            policy_id=request.policy_id, api_config_id=request.api_config_id
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to attach policy")

        logger.info(
            f"Attached policy {request.policy_id} to API "
            f"{request.api_config_id} by user {user_id}"
        )

        return {
            "status": "success",
            "message": (
                f"Policy {request.policy_id} attached to API "
                f"{request.api_config_id}"
            ),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error attaching policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to attach policy") from e


@router.post("/policies/detach/{api_config_id}")
async def detach_policy_from_api(
    api_config_id: str, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """Detach a policy from an API configuration."""
    try:
        policy_service = get_policy_service()

        success = await policy_service.detach_policy_from_api_config(api_config_id)

        if not success:
            raise HTTPException(
                status_code=404, detail="No policy attached to this API"
            )

        logger.info(f"Detached policy from API {api_config_id} by user {user_id}")

        return {
            "status": "success",
            "message": f"Policy detached from API {api_config_id}",
        }

    except Exception as e:
        logger.error(f"Error detaching policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to detach policy") from e


@router.post("/policies/migrate")
async def migrate_apis_to_policy(
    request: MigratePoliciesRequest, user_id: str = Depends(get_user_id_from_request)
) -> dict[str, Any]:
    """Migrate multiple API configurations to use a specific policy."""
    try:
        policy_service = get_policy_service()

        results = await policy_service.migrate_api_configs_to_policy(
            policy_id=request.policy_id, api_config_ids=request.api_config_ids
        )

        logger.info(
            f"Migrated {len(results['success'])} APIs to policy "
            f"{request.policy_id} by user {user_id}"
        )

        return {"status": "success", **results}

    except Exception as e:
        logger.error(f"Error migrating APIs to policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to migrate APIs") from e


@router.get("/policies/user/{user_id}/evaluation")
async def evaluate_user_policy(
    user_id: str,
    bypass_cache: bool = False,
    _current_user_id: str = Depends(get_user_id_from_request),
) -> dict[str, Any]:
    """Evaluate the policy for a specific user."""
    try:
        policy_service = get_policy_service()

        evaluation = await policy_service.evaluate_user_policy(
            user_id=user_id, bypass_cache=bypass_cache
        )

        if not evaluation:
            raise HTTPException(
                status_code=404, detail="User has no API configuration or policy"
            )

        return {"status": "success", **evaluation}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating policy for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate policy") from e


@router.post("/policies/default")
async def create_default_policies(
    user_id: str = Depends(get_user_id_from_request),
) -> dict[str, Any]:
    """Create default policies (Free, Standard, Premium tiers)."""
    try:
        policy_service = get_policy_service()

        policies = await policy_service.create_default_policies()

        logger.info(f"Created {len(policies)} default policies by user {user_id}")

        # Transform each policy to frontend format
        transformed_policies = [
            transform_policy_response(p.to_dict()) for p in policies
        ]

        return {
            "status": "success",
            "policies": transformed_policies,
            "count": len(policies),
        }

    except Exception as e:
        logger.error(f"Error creating default policies: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create default policies"
        ) from e
