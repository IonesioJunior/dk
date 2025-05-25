"""Repository for Policy persistence."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import Policy, PolicyUpdate

logger = logging.getLogger(__name__)


class PolicyRepository:
    """File-based repository for Policy entities."""

    def __init__(self, base_path: str = "./cache/policies") -> None:
        """Initialize the repository with a base path."""
        self.base_path = Path(base_path)
        self._ensure_directory_exists()
        self._index_file = self.base_path / "_index.json"
        self._association_file = self.base_path / "_associations.json"
        self._ensure_index_exists()
        self._ensure_associations_exists()

    def _ensure_directory_exists(self) -> None:
        """Ensure the base directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _ensure_index_exists(self) -> None:
        """Ensure the index file exists."""
        if not self._index_file.exists():
            self._write_index({})

    def _ensure_associations_exists(self) -> None:
        """Ensure the associations file exists."""
        if not self._association_file.exists():
            self._write_associations({"api_to_policy": {}, "policy_to_apis": {}})

    def _read_index(self) -> dict[str, Any]:
        """Read the index file."""
        try:
            with self._index_file.open() as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading index file: {e}")
            return {}

    def _write_index(self, index: dict[str, Any]) -> None:
        """Write the index file."""
        try:
            with self._index_file.open("w") as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing index file: {e}")

    def _read_associations(self) -> dict[str, dict[str, Any]]:
        """Read the associations file."""
        try:
            with self._association_file.open() as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading associations file: {e}")
            return {"api_to_policy": {}, "policy_to_apis": {}}

    def _write_associations(self, associations: dict[str, dict[str, Any]]) -> None:
        """Write the associations file."""
        try:
            with self._association_file.open("w") as f:
                json.dump(associations, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing associations file: {e}")

    def _get_policy_file_path(self, policy_id: str) -> str:
        """Get the file path for a policy."""
        return self.base_path / f"{policy_id}.json"

    def create(self, policy: Policy) -> Policy:
        """Create a new policy."""
        # Save the policy file
        file_path = self._get_policy_file_path(policy.policy_id)
        with file_path.open("w") as f:
            json.dump(policy.to_dict(), f, indent=2)

        # Update the index
        index = self._read_index()
        index[policy.policy_id] = {
            "name": policy.name,
            "type": policy.policy_type.value,
            "is_active": policy.is_active,
            "created_at": policy.created_at.isoformat(),
            "updated_at": policy.updated_at.isoformat(),
        }
        self._write_index(index)

        # Initialize associations for this policy
        associations = self._read_associations()
        if policy.policy_id not in associations["policy_to_apis"]:
            associations["policy_to_apis"][policy.policy_id] = []
        self._write_associations(associations)

        logger.info(f"Created policy: {policy.policy_id}")
        return policy

    def get(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        file_path = self._get_policy_file_path(policy_id)
        if not file_path.exists():
            return None

        try:
            with file_path.open() as f:
                data = json.load(f)
                return Policy.from_dict(data)
        except Exception as e:
            logger.error(f"Error reading policy {policy_id}: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[Policy]:
        """Get a policy by name."""
        index = self._read_index()
        for policy_id, metadata in index.items():
            if metadata.get("name") == name:
                return self.get(policy_id)
        return None

    def update(self, policy_id: str, update: PolicyUpdate) -> Optional[Policy]:
        """Update an existing policy."""
        policy = self.get(policy_id)
        if not policy:
            return None

        # Apply updates
        if update.name is not None:
            policy.name = update.name
        if update.description is not None:
            policy.description = update.description
        if update.policy_type is not None:
            policy.policy_type = update.policy_type
        if update.rules is not None:
            policy.rules = update.rules
        if update.api_configs is not None:
            policy.api_configs = update.api_configs
        if update.is_active is not None:
            policy.is_active = update.is_active
        if update.settings is not None:
            policy.settings = update.settings

        policy.updated_at = datetime.now(timezone.utc)

        # Save the updated policy
        file_path = self._get_policy_file_path(policy_id)
        with file_path.open("w") as f:
            json.dump(policy.to_dict(), f, indent=2)

        # Update the index
        index = self._read_index()
        if policy_id in index:
            index[policy_id]["name"] = policy.name
            index[policy_id]["type"] = policy.policy_type.value
            index[policy_id]["is_active"] = policy.is_active
            index[policy_id]["updated_at"] = policy.updated_at.isoformat()
            self._write_index(index)

        logger.info(f"Updated policy: {policy_id}")
        return policy

    def delete(self, policy_id: str) -> bool:
        """Delete a policy."""
        file_path = self._get_policy_file_path(policy_id)
        if not file_path.exists():
            return False

        try:
            # Remove the file
            file_path.unlink()

            # Update the index
            index = self._read_index()
            if policy_id in index:
                del index[policy_id]
                self._write_index(index)

            # Remove associations
            associations = self._read_associations()
            if policy_id in associations["policy_to_apis"]:
                # Remove API associations
                for api_id in associations["policy_to_apis"][policy_id]:
                    if api_id in associations["api_to_policy"]:
                        del associations["api_to_policy"][api_id]
                del associations["policy_to_apis"][policy_id]
                self._write_associations(associations)

            logger.info(f"Deleted policy: {policy_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting policy {policy_id}: {e}")
            return False

    def list_all(self) -> list[Policy]:
        """List all policies."""
        index = self._read_index()
        policies = []

        for policy_id in index:
            policy = self.get(policy_id)
            if policy:
                policies.append(policy)

        # Sort by updated_at descending
        policies.sort(key=lambda p: p.updated_at, reverse=True)
        return policies

    def list_active(self) -> list[Policy]:
        """List all active policies."""
        return [p for p in self.list_all() if p.is_active]

    def attach_to_api(self, policy_id: str, api_config_id: str) -> bool:
        """Attach a policy to an API configuration."""
        associations = self._read_associations()

        # Check if API already has a policy
        if api_config_id in associations["api_to_policy"]:
            logger.warning(f"API {api_config_id} already has a policy attached")
            return False

        # Create the association
        associations["api_to_policy"][api_config_id] = policy_id

        if policy_id not in associations["policy_to_apis"]:
            associations["policy_to_apis"][policy_id] = []

        if api_config_id not in associations["policy_to_apis"][policy_id]:
            associations["policy_to_apis"][policy_id].append(api_config_id)

        self._write_associations(associations)

        # Update the policy's api_configs list
        policy = self.get(policy_id)
        if policy and api_config_id not in policy.api_configs:
            policy.api_configs.append(api_config_id)
            self.update(policy_id, PolicyUpdate(api_configs=policy.api_configs))

        logger.info(f"Attached policy {policy_id} to API {api_config_id}")
        return True

    def detach_from_api(self, api_config_id: str) -> bool:
        """Detach a policy from an API configuration."""
        associations = self._read_associations()

        if api_config_id not in associations["api_to_policy"]:
            return False

        policy_id = associations["api_to_policy"][api_config_id]

        # Remove the association
        del associations["api_to_policy"][api_config_id]

        if (
            policy_id in associations["policy_to_apis"]
            and api_config_id in associations["policy_to_apis"][policy_id]
        ):
            associations["policy_to_apis"][policy_id].remove(api_config_id)

        self._write_associations(associations)

        # Update the policy's api_configs list
        policy = self.get(policy_id)
        if policy and api_config_id in policy.api_configs:
            policy.api_configs.remove(api_config_id)
            self.update(policy_id, PolicyUpdate(api_configs=policy.api_configs))

        logger.info(f"Detached policy from API {api_config_id}")
        return True

    def get_policy_for_api(self, api_config_id: str) -> Optional[str]:
        """Get the policy ID attached to an API configuration."""
        associations = self._read_associations()
        return associations["api_to_policy"].get(api_config_id)

    def get_apis_for_policy(self, policy_id: str) -> list[str]:
        """Get all API configuration IDs attached to a policy."""
        associations = self._read_associations()
        return associations["policy_to_apis"].get(policy_id, [])
