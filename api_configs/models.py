import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class APIConfig:
    config_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    users: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)
    policy_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.config_id,  # For backward compatibility
            "config_id": self.config_id,
            "users": self.users,
            "datasets": self.datasets,
            "policy_id": self.policy_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls: type["APIConfig"], data: dict) -> "APIConfig":
        # Handle both 'id' and 'config_id' for backward compatibility
        config_id = data.get("config_id") or data.get("id")
        api_config = cls(
            config_id=config_id,
            users=data.get("users", []),
            datasets=data.get("datasets", []),
            policy_id=data.get("policy_id"),
        )
        if "created_at" in data:
            api_config.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            api_config.updated_at = datetime.fromisoformat(data["updated_at"])
        return api_config


@dataclass
class APIConfigUpdate:
    users: Optional[list[str]] = None
    datasets: Optional[list[str]] = None
    policy_id: Optional[str] = None
