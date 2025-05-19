from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid


@dataclass
class APIConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    users: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "users": self.users,
            "datasets": self.datasets,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "APIConfig":
        api_config = cls(
            id=data.get("id"),
            users=data.get("users", []),
            datasets=data.get("datasets", []),
        )
        if "created_at" in data:
            api_config.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            api_config.updated_at = datetime.fromisoformat(data["updated_at"])
        return api_config


@dataclass
class APIConfigUpdate:
    users: Optional[List[str]] = None
    datasets: Optional[List[str]] = None
