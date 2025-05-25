"""Policy service for high-level orchestration."""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from services.api_config_service import APIConfigService

from .enforcer import PolicyEnforcer
from .manager import PolicyManager
from .models import (
    Policy,
    PolicyRule,
    PolicyRuleBuilder,
    PolicyType,
    PolicyUpdate,
    RuleOperator,
)

logger = logging.getLogger(__name__)


@dataclass
class CreatePolicyRequest:
    """Request parameters for creating a policy."""

    name: str
    description: Optional[str] = None
    policy_type: PolicyType = PolicyType.COMBINED
    rules: Optional[list[dict[str, Any]]] = None
    settings: Optional[dict[str, Any]] = field(default_factory=dict)


class PolicyService:
    """High-level service for policy operations."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.policy_manager = PolicyManager()
        self.manager = self.policy_manager  # Alias for compatibility
        self.enforcer = PolicyEnforcer()
        self.api_config_service = APIConfigService()
        self.api_config_manager = self.api_config_service.config_manager

    async def create_policy(self, request: CreatePolicyRequest) -> Policy:
        """Create a new policy from a CreatePolicyRequest."""
        # Call the original implementation
        return await self._create_policy_impl(request)

    async def _create_policy_impl(self, request: CreatePolicyRequest) -> Policy:
        """Internal implementation of create_policy."""
        # Build rules from configuration
        policy_rules = []
        if request.rules:
            logger.info(f"PolicyService.create_policy received rules: {request.rules}")
            for rule_config in request.rules:
                if rule_config.get("type") == "rate_limit":
                    builder = PolicyRuleBuilder()
                    policy_rules.append(
                        builder.with_rate_limit(
                            rule_config["requests_per_hour"],
                            rule_config.get("period", "hour"),
                        ).build()
                    )
                elif rule_config.get("type") == "token_limit":
                    builder = PolicyRuleBuilder()
                    policy_rules.append(
                        builder.with_token_limit(
                            rule_config["max_tokens_per_day"],
                            rule_config.get("period", "day"),
                        ).build()
                    )
                elif rule_config.get("type") == "credit_limit":
                    builder = PolicyRuleBuilder()
                    policy_rules.append(
                        builder.with_credit_limit(rule_config["max_credits"]).build()
                    )
                elif rule_config.get("type") == "custom":
                    # For custom rules, create a PolicyRule directly
                    params = rule_config["params"]
                    policy_rules.append(
                        PolicyRule(
                            metric_key=params["metric_key"],
                            operator=RuleOperator(params["operator"]),
                            threshold=params["threshold"],
                            period=params.get("period"),
                            action=params.get("action", "deny"),
                            message=params.get("message"),
                        )
                    )
                elif (
                    "metric_key" in rule_config
                    and "operator" in rule_config
                    and "threshold" in rule_config
                ):
                    try:
                        # Convert string operator to enum
                        operator_str = rule_config["operator"]
                        operator = RuleOperator(operator_str)

                        policy_rules.append(
                            PolicyRule(
                                metric_key=rule_config["metric_key"],
                                operator=operator,
                                threshold=rule_config["threshold"],
                                period=rule_config.get("period"),
                                action=rule_config.get("action", "deny"),
                                message=rule_config.get("message"),
                            )
                        )
                    except ValueError as e:
                        logger.error(f"Invalid operator '{operator_str}': {e}")
                        raise ValueError(
                            f"Invalid operator '{operator_str}'. Valid operators are: "
                            f"{list(RuleOperator.__members__.values())}"
                        ) from e

        # Create the policy
        policy = Policy(
            name=request.name,
            description=request.description,
            policy_type=request.policy_type,
            rules=policy_rules,
            settings=request.settings or {},
        )

        # Validate rules
        errors = self.manager.validate_policy_rules(policy)
        if errors:
            raise ValueError(f"Policy validation errors: {', '.join(errors)}")

        return self.manager.create_policy(policy)

    async def create_default_policies(self) -> list[Policy]:
        """Create a set of default policies for common use cases."""
        policies = []

        # Free tier policy
        free_policy = await self.create_policy(
            CreatePolicyRequest(
                name="Free Tier",
                description="Basic access with strict limits",
                policy_type=PolicyType.COMBINED,
                rules=[
                    {"type": "rate_limit", "requests_per_hour": 10},
                    {"type": "token_limit", "max_tokens_per_day": 10000},
                    {"type": "credit_limit", "max_credits": 100},
                ],
                settings={"grace_period": 300},
            )
        )
        policies.append(free_policy)

        # Standard tier policy
        standard_policy = await self.create_policy(
            CreatePolicyRequest(
                name="Standard Tier",
                description="Regular access with moderate limits",
                policy_type=PolicyType.COMBINED,
                rules=[
                    {"type": "rate_limit", "requests_per_hour": 100},
                    {"type": "token_limit", "max_tokens_per_day": 100000},
                    {"type": "credit_limit", "max_credits": 1000},
                ],
                settings={"grace_period": 600, "soft_limit_percentage": 0.8},
            )
        )
        policies.append(standard_policy)

        # Premium tier policy
        premium_policy = await self.create_policy(
            CreatePolicyRequest(
                name="Premium Tier",
                description="Enhanced access with high limits",
                policy_type=PolicyType.COMBINED,
                rules=[
                    {"type": "rate_limit", "requests_per_hour": 1000},
                    {"type": "token_limit", "max_tokens_per_day": 1000000},
                    {"type": "credit_limit", "max_credits": 10000},
                ],
                settings={"grace_period": 1800, "soft_limit_percentage": 0.9},
            )
        )
        policies.append(premium_policy)

        logger.info(f"Created {len(policies)} default policies")
        return policies

    async def attach_policy_to_api_config(
        self, policy_id: str, api_config_id: str
    ) -> bool:
        """Attach a policy to an API configuration with full validation."""
        try:
            # Attach the policy
            result = self.manager.attach_policy_to_api(policy_id, api_config_id)

            if result:
                # Clear enforcement cache for this API
                self.enforcer.clear_cache_for_api(api_config_id)

                # Update API config metadata
                api_config = self.api_config_service.get_api_config(api_config_id)
                if api_config:
                    # Get all users in this API config and clear their caches
                    for user in api_config.users:
                        self.enforcer.clear_cache_for_user(user)

            return result

        except Exception as e:
            logger.error(
                f"Error attaching policy {policy_id} to API {api_config_id}: {e}"
            )
            raise

    async def detach_policy_from_api_config(self, api_config_id: str) -> bool:
        """Detach a policy from an API configuration."""
        try:
            # Get users before detaching
            api_config = self.api_config_service.get_api_config(api_config_id)
            users = api_config.users if api_config else []

            # Detach the policy
            result = self.manager.detach_policy_from_api(api_config_id)

            if result:
                # Clear enforcement cache
                self.enforcer.clear_cache_for_api(api_config_id)
                for user in users:
                    self.enforcer.clear_cache_for_user(user)

            return result

        except Exception as e:
            logger.error(f"Error detaching policy from API {api_config_id}: {e}")
            raise

    async def evaluate_user_policy(
        self, user_id: str, bypass_cache: bool = False
    ) -> Optional[dict[str, Any]]:
        """Evaluate the policy for a user and return detailed information."""

        # Get evaluation result
        context = {"bypass_cache": bypass_cache} if bypass_cache else None

        # Get user's API config
        api_config_id = self.manager.api_config_manager.get_policy_for_user(user_id)
        if not api_config_id:
            return None

        result = await self.enforcer.enforce_policy(api_config_id, user_id, context)

        # Get policy details
        policy = self.manager.get_policy_for_api(api_config_id)

        return {
            "user_id": user_id,
            "api_config_id": api_config_id,
            "policy": (
                {
                    "id": policy.policy_id if policy else None,
                    "name": policy.name if policy else None,
                    "type": policy.policy_type.value if policy else None,
                    "is_active": policy.is_active if policy else None,
                }
                if policy
                else None
            ),
            "evaluation": {
                "allowed": result.allowed,
                "violated_rules": [
                    {
                        "metric": rule.metric_key,
                        "threshold": rule.threshold,
                        "message": rule.message,
                    }
                    for rule in result.violated_rules
                ],
                "warnings": result.warnings,
                "remaining_quota": result.remaining_quota,
                "metadata": result.metadata,
            },
        }

    async def get_policy_summary(self, policy_id: str) -> Optional[dict[str, Any]]:
        """Get a comprehensive summary of a policy."""
        policy = self.manager.get_policy(policy_id)
        if not policy:
            return None

        # Get attached APIs
        attached_apis = self.manager.get_apis_with_policy(policy_id)

        # Count total users under this policy
        total_users = sum(len(api["users"]) for api in attached_apis)

        return {
            "policy": {
                "id": policy.policy_id,
                "name": policy.name,
                "description": policy.description,
                "type": policy.policy_type.value,
                "is_active": policy.is_active,
                "created_at": policy.created_at.isoformat(),
                "updated_at": policy.updated_at.isoformat(),
                "rules_count": len(policy.rules),
                "settings": policy.settings,
            },
            "rules": [
                {
                    "id": rule.rule_id,
                    "metric": rule.metric_key,
                    "operator": rule.operator.value,
                    "threshold": rule.threshold,
                    "period": rule.period,
                    "action": rule.action,
                    "message": rule.message,
                }
                for rule in policy.rules
            ],
            "usage": {
                "attached_apis_count": len(attached_apis),
                "total_users": total_users,
                "attached_apis": attached_apis,
            },
        }

    async def update_policy_rules(
        self, policy_id: str, rules: list[dict[str, Any]]
    ) -> Optional[Policy]:
        """Update the rules of a policy."""
        # Build new rules
        new_rules = []
        for rule_config in rules:
            if rule_config.get("type") == "rate_limit":
                new_rules.append(
                    PolicyRuleBuilder.rate_limit(rule_config["requests_per_hour"])
                )
            elif rule_config.get("type") == "token_limit":
                new_rules.append(
                    PolicyRuleBuilder.token_limit(rule_config["max_tokens_per_day"])
                )
            elif rule_config.get("type") == "credit_limit":
                new_rules.append(
                    PolicyRuleBuilder.credit_limit(rule_config["max_credits"])
                )
            elif rule_config.get("type") == "custom":
                new_rules.append(PolicyRuleBuilder.custom_rule(**rule_config["params"]))
            elif (
                "metric_key" in rule_config
                and "operator" in rule_config
                and "threshold" in rule_config
            ):
                try:
                    # Convert string operator to enum
                    operator_str = rule_config["operator"]
                    operator = RuleOperator(operator_str)

                    new_rules.append(
                        PolicyRuleBuilder.custom_rule(
                            metric_key=rule_config["metric_key"],
                            operator=operator,
                            threshold=rule_config["threshold"],
                            period=rule_config.get("period"),
                            action=rule_config.get("action", "deny"),
                            message=rule_config.get("message"),
                        )
                    )
                except ValueError as e:
                    logger.error(f"Invalid operator '{operator_str}': {e}")
                    raise ValueError(
                        f"Invalid operator '{operator_str}'. Valid operators are: "
                        f"{list(RuleOperator.__members__.values())}"
                    ) from e

        # Update the policy
        update = PolicyUpdate(rules=new_rules)
        updated_policy = self.manager.update_policy(policy_id, update)

        if updated_policy:
            # Clear cache for all affected APIs
            api_ids = self.manager.repository.get_apis_for_policy(policy_id)
            for api_id in api_ids:
                self.enforcer.clear_cache_for_api(api_id)

        return updated_policy

    async def migrate_api_configs_to_policy(
        self, policy_id: str, api_config_ids: list[str]
    ) -> dict[str, Any]:
        """Migrate multiple API configurations to use a specific policy."""
        results = {"success": [], "failed": []}

        for api_config_id in api_config_ids:
            try:
                # First detach any existing policy
                await self.detach_policy_from_api_config(api_config_id)

                # Then attach the new policy
                await self.attach_policy_to_api_config(policy_id, api_config_id)

                results["success"].append(api_config_id)

            except Exception as e:
                logger.error(
                    f"Failed to migrate API {api_config_id} to policy {policy_id}: {e}"
                )
                results["failed"].append(
                    {"api_config_id": api_config_id, "error": str(e)}
                )

        return results

    async def add_policy_rules(self, policy_id: str, rules: list) -> Policy:
        """Add rules to an existing policy."""
        policy = self.policy_manager.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        # Add new rules to existing rules
        policy.rules.extend(rules)

        # Update the policy
        update = PolicyUpdate(rules=policy.rules)
        return self.policy_manager.update_policy(policy_id, update)

    async def remove_policy_rule(self, policy_id: str, rule_index: int) -> Policy:
        """Remove a rule from a policy by index."""
        policy = self.policy_manager.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        if 0 <= rule_index < len(policy.rules):
            policy.rules.pop(rule_index)

            # Update the policy
            update = PolicyUpdate(rules=policy.rules)
            return self.policy_manager.update_policy(policy_id, update)

        raise ValueError(f"Invalid rule index: {rule_index}")

    async def update_policy(self, policy_id: str, **kwargs: Any) -> Optional[Policy]:
        """Update a policy with the given fields."""
        update = PolicyUpdate(**kwargs)
        return self.policy_manager.update_policy(policy_id, update)

    async def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        return self.policy_manager.delete_policy(policy_id)

    async def attach_policy_to_api_configs(
        self, policy_id: str, api_config_ids: list[str]
    ) -> list:
        """Attach a policy to multiple API configs."""
        results = []
        for api_id in api_config_ids:
            try:
                success = await self.attach_policy_to_api_config(policy_id, api_id)
                if success:
                    config = self.api_config_service.get_api_config(api_id)
                    if config:
                        results.append(config)
            except Exception as e:
                logger.error(f"Failed to attach policy to {api_id}: {e}")
        return results

    async def detach_policy_from_api_configs(self, api_config_ids: list[str]) -> list:
        """Detach policies from multiple API configs."""
        results = []
        for api_id in api_config_ids:
            try:
                success = await self.detach_policy_from_api_config(api_id)
                if success:
                    config = self.api_config_service.get_api_config(api_id)
                    if config:
                        results.append(config)
            except Exception as e:
                logger.error(f"Failed to detach policy from {api_id}: {e}")
        return results

    async def bulk_migrate_api_configs_to_policy(
        self, from_policy_id: str, to_policy_id: str
    ) -> list:
        """Migrate all API configs from one policy to another."""
        # Get all APIs with the source policy
        apis = self.policy_manager.get_apis_with_policy(from_policy_id)
        api_ids = [api["config_id"] for api in apis]

        # Migrate them
        result = await self.migrate_api_configs_to_policy(to_policy_id, api_ids)

        # Return the successfully migrated configs
        migrated_configs = []
        for api_id in result["success"]:
            config = self.api_config_service.get_api_config(api_id)
            if config:
                migrated_configs.append(config)

        return migrated_configs

    async def get_policy_usage_summary(self, policy_id: str) -> dict[str, Any]:
        """Get usage summary for a policy."""
        policy = self.policy_manager.get_policy(policy_id)
        if not policy:
            return {}

        apis = self.policy_manager.get_apis_with_policy(policy_id)
        all_users = set()
        for api in apis:
            all_users.update(api.get("users", []))

        return {
            "policy_id": policy_id,
            "policy_name": policy.name,
            "total_api_configs": len(apis),
            "total_users": len(all_users),
            "users": list(all_users),
        }

    def _validate_policy_type_rules_match(
        self, policy_type: PolicyType, rules: list
    ) -> bool:
        """Validate that rules match the policy type."""
        if policy_type == PolicyType.RATE_LIMIT:
            return all(
                r.metric_key in ["requests_count", "requests_per_hour"] for r in rules
            )
        if policy_type == PolicyType.TOKEN_LIMIT:
            return all(
                "words_count" in r.metric_key or "tokens" in r.metric_key for r in rules
            )
        if policy_type == PolicyType.CREDIT_BASED:
            return all(r.metric_key == "credits_used" for r in rules)
        # COMBINED
        return True

    async def get_policies_by_type(self, policy_type: PolicyType) -> list[Policy]:
        """Get all policies of a specific type."""
        all_policies = self.policy_manager.get_all_policies()
        return [p for p in all_policies if p.policy_type == policy_type]

    async def clone_policy(self, source_policy_id: str, new_name: str) -> Policy:
        """Clone an existing policy with a new name."""
        source = self.policy_manager.get_policy(source_policy_id)
        if not source:
            raise ValueError(f"Source policy {source_policy_id} not found")

        # Create new policy with same attributes but new name
        cloned = Policy(
            name=new_name,
            description=source.description,
            policy_type=source.policy_type,
            rules=source.rules.copy(),
            settings=source.settings.copy() if source.settings else {},
        )

        return self.policy_manager.create_policy(cloned)

    async def ensure_default_policies(self) -> list[Policy]:
        """Create default policy templates if they don't exist."""
        policies = []

        # Check if default policies already exist
        existing = self.policy_manager.get_policy_by_name("Free Tier")
        if existing:
            policies.append(existing)
        else:
            # Create Free Tier
            free = await self.create_policy(
                CreatePolicyRequest(
                    name="Free Tier",
                    description="Basic access with strict limits",
                    policy_type=PolicyType.COMBINED,
                    rules=[
                        {"type": "rate_limit", "requests_per_hour": 10},
                        {"type": "token_limit", "max_tokens_per_day": 10000},
                        {"type": "credit_limit", "max_credits": 100},
                    ],
                )
            )
            policies.append(free)

        # Standard Tier
        existing = self.policy_manager.get_policy_by_name("Standard Tier")
        if existing:
            policies.append(existing)
        else:
            standard = await self.create_policy(
                CreatePolicyRequest(
                    name="Standard Tier",
                    description="Regular access with moderate limits",
                    policy_type=PolicyType.COMBINED,
                    rules=[
                        {"type": "rate_limit", "requests_per_hour": 100},
                        {"type": "token_limit", "max_tokens_per_day": 100000},
                        {"type": "credit_limit", "max_credits": 1000},
                    ],
                )
            )
            policies.append(standard)

        # Premium Tier
        existing = self.policy_manager.get_policy_by_name("Premium Tier")
        if existing:
            policies.append(existing)
        else:
            premium = await self.create_policy(
                CreatePolicyRequest(
                    name="Premium Tier",
                    description="Enhanced access with high limits",
                    policy_type=PolicyType.COMBINED,
                    rules=[
                        {"type": "rate_limit", "requests_per_hour": 1000},
                        {"type": "token_limit", "max_tokens_per_day": 1000000},
                        {"type": "credit_limit", "max_credits": 10000},
                    ],
                )
            )
            policies.append(premium)

        return policies
