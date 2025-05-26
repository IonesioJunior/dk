"""Triage data models for policy-based response review."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class TriageRequest:
    """A request pending triage review."""

    # Core identifiers (required fields first)
    user_id: str
    prompt_id: str
    api_config_id: str
    policy_rule_id: str

    # Request content (required)
    prompt_query: str
    generated_response: str

    # Fields with defaults
    triage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    documents_retrieved: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Additional metadata
    conversation_key: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "triage_id": self.triage_id,
            "user_id": self.user_id,
            "prompt_id": self.prompt_id,
            "api_config_id": self.api_config_id,
            "policy_rule_id": self.policy_rule_id,
            "prompt_query": self.prompt_query,
            "documents_retrieved": self.documents_retrieved,
            "generated_response": self.generated_response,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "rejection_reason": self.rejection_reason,
            "conversation_key": self.conversation_key,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls: type["TriageRequest"], data: dict[str, Any]) -> "TriageRequest":
        """Create from dictionary representation."""
        return cls(
            triage_id=data.get("triage_id", str(uuid.uuid4())),
            user_id=data["user_id"],
            prompt_id=data["prompt_id"],
            api_config_id=data["api_config_id"],
            policy_rule_id=data["policy_rule_id"],
            prompt_query=data["prompt_query"],
            documents_retrieved=data.get("documents_retrieved", []),
            generated_response=data["generated_response"],
            status=data.get("status", "pending"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(timezone.utc)
            ),
            reviewed_at=(
                datetime.fromisoformat(data["reviewed_at"])
                if data.get("reviewed_at")
                else None
            ),
            reviewed_by=data.get("reviewed_by"),
            rejection_reason=data.get("rejection_reason"),
            conversation_key=data.get("conversation_key"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TriageUpdate:
    """DTO for updating triage request status."""

    status: str  # approved, rejected
    reviewed_by: str = "app_owner"  # Since we're on localhost
    rejection_reason: Optional[str] = None
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
