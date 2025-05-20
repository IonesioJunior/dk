import logging
from typing import Optional

from api_configs.manager import APIConfigManager
from api_configs.models import APIConfig, APIConfigUpdate
from api_configs.repository import APIConfigRepository
from api_configs.usage_tracker import APIConfigMetrics, APIConfigUsageTracker
from database import VectorDBManager

logger = logging.getLogger(__name__)


class APIConfigService:
    """Service layer for API configuration management."""

    def __init__(self) -> None:
        self.repository = APIConfigRepository()
        self.db_manager = VectorDBManager()
        self.config_manager = APIConfigManager()
        self.usage_tracker = APIConfigUsageTracker()

    def create_api_config(self, users: list[str], datasets: list[str]) -> APIConfig:
        # Check if any users are already in other policies
        can_add, conflicting_users = self.config_manager.can_add_users_to_policy(users)

        if not can_add:
            raise ValueError(
                "Cannot create policy: The following users are already in "
                "other policies: "
                f"{conflicting_users}"
            )

        api_config = APIConfig(users=users, datasets=datasets)
        created_config = self.repository.create(api_config)

        # Update metadata for all documents in the datasets
        self._update_document_metadata(created_config.config_id, datasets)

        return created_config

    def get_api_config(self, api_config_id: str) -> Optional[APIConfig]:
        return self.repository.get_by_id(api_config_id)

    def get_all_api_configs(self) -> list[APIConfig]:
        return self.repository.get_all()

    def update_api_config(
        self, api_config_id: str, api_config_update: APIConfigUpdate
    ) -> Optional[APIConfig]:
        # Get the existing config to compare datasets
        existing_config = self.repository.get_by_id(api_config_id)
        if not existing_config:
            return None

        # If users are being updated, check for conflicts
        if api_config_update.users is not None:
            can_add, conflicting_users = self.config_manager.can_add_users_to_policy(
                api_config_update.users, exclude_policy_id=api_config_id
            )

            if not can_add:
                raise ValueError(
                    "Cannot update policy: The following users are already in "
                    "other policies: "
                    f"{conflicting_users}"
                )

        # Update the config
        updated_config = self.repository.update(api_config_id, api_config_update)

        if updated_config and api_config_update.datasets is not None:
            # Find newly added datasets
            existing_datasets = set(existing_config.datasets)
            new_datasets = set(api_config_update.datasets)
            added_datasets = new_datasets - existing_datasets
            removed_datasets = existing_datasets - new_datasets

            # Update metadata for newly added datasets
            if added_datasets:
                self._update_document_metadata(api_config_id, list(added_datasets))

            # Remove metadata from removed datasets
            if removed_datasets:
                self._remove_document_metadata(api_config_id, list(removed_datasets))

        return updated_config

    def delete_api_config(self, api_config_id: str) -> bool:
        # Get the config before deletion to clean up metadata
        config = self.repository.get_by_id(api_config_id)
        if config:
            # Remove metadata from all documents in this config
            self._remove_document_metadata(api_config_id, config.datasets)

        return self.repository.delete(api_config_id)

    def check_user_access(self, user: str, dataset: str) -> bool:
        """Check if a user has access to a dataset based on API configurations"""
        # Get the policy for the user
        policy_id = self.config_manager.get_policy_for_user(user)

        if not policy_id:
            return False

        # Check if the dataset is in the user's policy
        datasets = self.config_manager.get_datasets_for_policy(policy_id)
        return dataset in datasets

    def get_user_accessible_datasets(self, user: str) -> list[str]:
        """Get all datasets a user has access to"""
        # Get the policy for the user
        policy_id = self.config_manager.get_policy_for_user(user)

        if not policy_id:
            return []

        # Return all datasets in the user's policy
        return self.config_manager.get_datasets_for_policy(policy_id)

    def get_dataset_authorized_users(self, dataset: str) -> list[str]:
        """Get all users who have access to a dataset"""
        authorized_users = set()
        api_configs = self.get_all_api_configs()

        for api_config in api_configs:
            if dataset in api_config.datasets:
                authorized_users.update(api_config.users)

        return list(authorized_users)

    def track_api_usage(
        self, api_config_id: str, user_id: str, input_prompt: str, output_prompt: str
    ) -> None:
        """
        Track usage of an API configuration.

        Args:
            api_config_id: The ID of the API configuration
            user_id: The ID of the user making the request
            input_prompt: The input prompt text
            output_prompt: The output prompt text
        """
        try:
            self.usage_tracker.track_usage(
                api_config_id=api_config_id,
                user_id=user_id,
                input_prompt=input_prompt,
                output_prompt=output_prompt,
            )
        except Exception as e:
            logger.error(f"Error tracking API usage: {e}")

    def get_api_usage_metrics(self, api_config_id: str) -> Optional[APIConfigMetrics]:
        """
        Get usage metrics for a specific API configuration.

        Args:
            api_config_id: The ID of the API configuration

        Returns:
            The metrics for the API configuration, or None if not found
        """
        return self.usage_tracker.get_metrics(api_config_id)

    def get_all_api_usage_metrics(self) -> list[APIConfigMetrics]:
        """
        Get usage metrics for all API configurations.

        Returns:
            A list of metrics for all API configurations
        """
        return self.usage_tracker.get_all_metrics()

    def get_top_api_users(
        self, api_config_id: str, limit: int = 10
    ) -> list[tuple[str, int]]:
        """
        Get the top users for a specific API configuration.

        Args:
            api_config_id: The ID of the API configuration
            limit: Maximum number of users to return

        Returns:
            A list of (user_id, count) tuples sorted by count descending
        """
        return self.usage_tracker.get_top_users(api_config_id, limit)

    def _update_document_metadata(self, policy_id: str, dataset_ids: list[str]) -> None:
        """Add policy_id to the metadata of all documents in the datasets."""
        try:
            # We need to update documents one by one to preserve existing metadata
            for dataset_id in dataset_ids:
                # Get the current document data including metadata
                get_params = self.db_manager.GetParams(
                    collection_name="documents",
                    ids=[dataset_id],
                    include=["metadatas", "documents", "embeddings"],
                )
                result = self.db_manager.get(get_params)

                if result["ids"]:
                    # Get existing metadata
                    current_metadata = (
                        result["metadatas"][0] if result["metadatas"] else {}
                    )

                    # Add the policy_id to metadata
                    updated_metadata = current_metadata.copy()
                    updated_metadata[policy_id] = True

                    # Update the document with the new metadata
                    params = self.db_manager.UpdateDataParams(
                        collection_name="documents",
                        ids=[dataset_id],
                        metadatas=[updated_metadata],
                    )
                    self.db_manager.update_data(params)

        except Exception as e:
            # Log error but don't fail the API config creation
            logger.error(
                f"Failed to update document metadata for policy {policy_id}: {e}"
            )

    def _remove_document_metadata(self, policy_id: str, dataset_ids: list[str]) -> None:
        """Remove policy_id from the metadata of all documents in the datasets."""
        try:
            for dataset_id in dataset_ids:
                # Get the current document data including metadata
                get_params = self.db_manager.GetParams(
                    collection_name="documents",
                    ids=[dataset_id],
                    include=["metadatas", "documents", "embeddings"],
                )
                result = self.db_manager.get(get_params)

                if result["ids"]:
                    # Get existing metadata
                    current_metadata = (
                        result["metadatas"][0] if result["metadatas"] else {}
                    )

                    # Remove the policy_id from metadata
                    if policy_id in current_metadata:
                        updated_metadata = current_metadata.copy()
                        del updated_metadata[policy_id]

                        # Update the document with the new metadata
                        params = self.db_manager.UpdateDataParams(
                            collection_name="documents",
                            ids=[dataset_id],
                            metadatas=[updated_metadata],
                        )
                        self.db_manager.update_data(params)

        except Exception as e:
            # Log error but don't fail the operation
            logger.error(
                f"Failed to remove document metadata for policy {policy_id}: {e}"
            )
