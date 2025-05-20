"""
APIConfigManager - Singleton manager for API configurations

Provides a centralized manager for API configuration operations with
user-policy mapping.
Ensures each user can only be included in one policy.
"""

import logging
from typing import Optional

from api_configs.repository import APIConfigRepository

logger = logging.getLogger(__name__)


class APIConfigManager:
    """
    Singleton API Configuration Manager.

    This manager handles the business logic for API configurations,
    particularly the constraint that each user can only belong to one policy.
    """

    _instance: Optional["APIConfigManager"] = None
    _repository: Optional[APIConfigRepository] = None

    def __new__(cls) -> "APIConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the APIConfigManager with repository access."""
        if self._repository is None:
            self._initialize_repository()

    def _initialize_repository(self) -> None:
        """Initialize the API configuration repository."""
        try:
            self._repository = APIConfigRepository()
            logger.info("APIConfigRepository initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize APIConfigRepository: {e}")
            raise

    def get_policy_for_user(self, user_id: str) -> Optional[str]:
        """
        Get the policy ID for a given user.

        Since each user can only be in one policy, this method finds
        and returns the first (and only) policy ID that includes the user.

        Args:
            user_id: The ID of the user to check

        Returns:
            The policy ID if the user is found in a policy, None otherwise
        """
        try:
            all_configs = self._repository.get_all()

            for config in all_configs:
                if user_id in config.users:
                    return config.config_id

            return None

        except Exception as e:
            logger.error(f"Error getting policy for user {user_id}: {e}")
            return None

    def is_user_in_any_policy(self, user_id: str) -> bool:
        """
        Check if a user is already included in any policy.

        Args:
            user_id: The ID of the user to check

        Returns:
            True if the user is in any policy, False otherwise
        """
        return self.get_policy_for_user(user_id) is not None

    def get_users_for_policy(self, policy_id: str) -> list[str]:
        """
        Get all users associated with a specific policy.

        Args:
            policy_id: The ID of the policy

        Returns:
            List of user IDs associated with the policy
        """
        try:
            config = self._repository.get_by_id(policy_id)
            if config:
                return config.users
            return []

        except Exception as e:
            logger.error(f"Error getting users for policy {policy_id}: {e}")
            return []

    def get_datasets_for_policy(self, policy_id: str) -> list[str]:
        """
        Get all datasets associated with a specific policy.

        Args:
            policy_id: The ID of the policy

        Returns:
            List of dataset IDs associated with the policy
        """
        try:
            config = self._repository.get_by_id(policy_id)
            if config:
                return config.datasets
            return []

        except Exception as e:
            logger.error(f"Error getting datasets for policy {policy_id}: {e}")
            return []

    def validate_user_not_in_other_policies(
        self, user_id: str, exclude_policy_id: Optional[str] = None
    ) -> bool:
        """
        Validate that a user is not already in another policy.

        Args:
            user_id: The ID of the user to check
            exclude_policy_id: Optional policy ID to exclude from the check
                (useful for updates)

        Returns:
            True if the user is not in any other policy, False otherwise
        """
        existing_policy = self.get_policy_for_user(user_id)

        if existing_policy is None:
            return True

        return bool(exclude_policy_id and existing_policy == exclude_policy_id)

    def can_add_users_to_policy(
        self, users: list[str], policy_id: Optional[str] = None
    ) -> tuple[bool, list[str]]:
        """
        Check if a list of users can be added to a policy.

        Args:
            users: List of user IDs to check
            policy_id: Optional policy ID for update operations

        Returns:
            Tuple of (can_add_all, list_of_conflicting_users)
        """
        conflicting_users = []

        for user in users:
            if not self.validate_user_not_in_other_policies(user, policy_id):
                conflicting_users.append(user)

        return len(conflicting_users) == 0, conflicting_users
