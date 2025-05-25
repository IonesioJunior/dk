"""Manager for Policy business logic."""

import logging
from typing import Any, Optional

from api_configs.manager import APIConfigManager
from api_configs.repository import APIConfigRepository

from .models import Policy, PolicyUpdate
from .repository import PolicyRepository

logger = logging.getLogger(__name__)


class PolicyManager:
    """Manages policy business logic and associations."""

    _instance = None

    def __new__(cls) -> "PolicyManager":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the manager."""
        if not self._initialized:
            self.repository = PolicyRepository()
            self.api_config_repository = APIConfigRepository()
            self.api_config_manager = APIConfigManager()
            self._initialized = True

    def create_policy(self, policy: Policy) -> Policy:
        """Create a new policy with validation."""
        # Validate policy name is unique
        existing = self.repository.get_by_name(policy.name)
        if existing:
            raise ValueError(f"Policy with name '{policy.name}' already exists")

        # Validate rules
        if not policy.rules:
            logger.warning(f"Policy '{policy.name}' created without any rules")

        return self.repository.create(policy)

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self.repository.get(policy_id)

    def update_policy(self, policy_id: str, update: PolicyUpdate) -> Optional[Policy]:
        """Update a policy with validation."""
        policy = self.repository.get(policy_id)
        if not policy:
            return None

        # If name is being updated, check for uniqueness
        if update.name and update.name != policy.name:
            existing = self.repository.get_by_name(update.name)
            if existing:
                raise ValueError(f"Policy with name '{update.name}' already exists")

        return self.repository.update(policy_id, update)

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy if not attached to any APIs."""
        apis = self.repository.get_apis_for_policy(policy_id)
        if apis:
            raise ValueError(
                f"Cannot delete policy {policy_id}: attached to {len(apis)} API(s)"
            )

        return self.repository.delete(policy_id)

    def list_policies(self, active_only: bool = False) -> list[Policy]:
        """List all policies."""
        if active_only:
            return self.repository.list_active()
        return self.repository.list_all()

    def attach_policy_to_api(self, policy_id: str, api_config_id: str) -> bool:
        """Attach a policy to an API configuration."""
        # Validate policy exists and is active
        policy = self.repository.get(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        if not policy.is_active:
            raise ValueError(f"Policy {policy_id} is not active")

        # Validate API config exists
        api_config = self.api_config_repository.get(api_config_id)
        if not api_config:
            raise ValueError(f"API configuration {api_config_id} not found")

        # Check if API already has a policy
        existing_policy_id = self.repository.get_policy_for_api(api_config_id)
        if existing_policy_id:
            raise ValueError(
                f"API {api_config_id} already has policy {existing_policy_id} attached"
            )

        # Attach in policy repository
        result = self.repository.attach_to_api(policy_id, api_config_id)

        # Update API config with policy_id
        if result:
            from api_configs.models import APIConfigUpdate

            update = APIConfigUpdate(policy_id=policy_id)
            self.api_config_repository.update(api_config_id, update)

        return result

    def detach_policy_from_api(self, api_config_id: str) -> bool:
        """Detach a policy from an API configuration."""
        return self.repository.detach_from_api(api_config_id)

    def get_policy_for_api(self, api_config_id: str) -> Optional[Policy]:
        """Get the policy attached to an API configuration."""
        policy_id = self.repository.get_policy_for_api(api_config_id)
        if policy_id:
            return self.repository.get(policy_id)
        return None

    def get_policy_for_user(self, user: str) -> Optional[Policy]:
        """Get the policy for a user through their API configuration."""
        # First get the API config for the user
        api_config_id = self.api_config_manager.get_policy_for_user(user)
        if not api_config_id:
            return None

        # Then get the policy for that API config
        return self.get_policy_for_api(api_config_id)

    def can_user_access_dataset(self, user: str, dataset: str) -> bool:
        """Check if a user can access a dataset based on their policy."""
        # First check API config access
        if not self.api_config_manager.check_user_access(user, dataset):
            return False

        # Then check if their API config has an active policy
        policy = self.get_policy_for_user(user)
        return not (policy and not policy.is_active)

    def get_apis_with_policy(self, policy_id: str) -> list[dict[str, Any]]:
        """Get all API configurations that have this policy attached."""
        api_ids = self.repository.get_apis_for_policy(policy_id)
        apis = []

        for api_id in api_ids:
            api_config = self.api_config_repository.get(api_id)
            if api_config:
                apis.append(
                    {
                        "config_id": api_config.config_id,
                        "users": api_config.users,
                        "datasets": api_config.datasets,
                        "created_at": api_config.created_at.isoformat(),
                        "updated_at": api_config.updated_at.isoformat(),
                    }
                )

        return apis

    def validate_policy_rules(self, policy: Policy) -> list[str]:
        """Validate policy rules for consistency and correctness."""
        errors = []
        logger.info(
            f"PolicyManager.validate_policy_rules called with {len(policy.rules)} rules"
        )

        for rule in policy.rules:
            logger.info(
                f"Validating rule: metric_key={rule.metric_key}, "
                f"operator={rule.operator}, threshold={rule.threshold}"
            )
            # Check metric key is valid
            # These are the actual metrics used by the enforcer
            valid_metrics = [
                # Primary metrics from enforcer.get_usage_metrics()
                "requests_count",
                "input_words_count",
                "output_words_count",
                "total_words_count",
                "credits_used",
                # Legacy/compatibility metrics
                "requests_per_hour",
                "requests_per_day",
                "requests_per_month",
                "total_tokens",
                "total_tokens_per_hour",
                "total_tokens_per_day",
                "input_tokens",
                "output_tokens",
                "avg_response_time",
                "error_rate",
            ]

            if rule.metric_key not in valid_metrics:
                logger.error(f"Metric key '{rule.metric_key}' not in valid_metrics")
                errors.append(f"Unknown metric key: {rule.metric_key}")

            # Check threshold is positive
            if rule.threshold < 0:
                errors.append(
                    f"Negative threshold for rule {rule.rule_id}: {rule.threshold}"
                )

            # Check action is valid
            if rule.action not in ["deny", "warn", "throttle"]:
                errors.append(f"Invalid action for rule {rule.rule_id}: {rule.action}")

            # Check period is valid if specified
            if rule.period and rule.period not in ["hour", "day", "month", "lifetime"]:
                errors.append(f"Invalid period for rule {rule.rule_id}: {rule.period}")

        return errors

    def get_all_policies(self) -> list[Policy]:
        """Get all policies."""
        return self.repository.list_all()

    def get_policy_by_name(self, name: str) -> Optional[Policy]:
        """Get a policy by name."""
        return self.repository.get_by_name(name)

    def get_api_config_by_id(self, api_config_id: str) -> Any:
        """Get API config by ID."""
        return self.api_config_repository.get_by_id(api_config_id)
