"""Policy data models and structures."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class PolicyType(Enum):
    """Types of policies available."""

    RATE_LIMIT = "rate_limit"
    CREDIT_BASED = "credit_based"
    TOKEN_LIMIT = "token_limit"  # nosec B105 - Not a password, just an enum value
    COMBINED = "combined"


class RuleOperator(Enum):
    """Operators for rule evaluation."""

    LESS_THAN = "lt"
    LESS_THAN_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_EQUAL = "gte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


@dataclass
class PolicyRule:
    """Individual rule within a policy."""

    metric_key: str  # e.g., "requests_per_hour", "total_tokens", "credits_used"
    operator: RuleOperator
    threshold: float
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    period: Optional[str] = None  # e.g., "hour", "day", "month", "lifetime"
    action: str = "deny"  # "deny", "warn", "throttle"
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rule_id": self.rule_id,
            "metric_key": self.metric_key,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "period": self.period,
            "action": self.action,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls: type["PolicyRule"], data: dict[str, Any]) -> "PolicyRule":
        """Create from dictionary representation."""
        return cls(
            rule_id=data.get("rule_id", str(uuid.uuid4())),
            metric_key=data["metric_key"],
            operator=RuleOperator(data["operator"]),
            threshold=float(data["threshold"]),
            period=data.get("period"),
            action=data.get("action", "deny"),
            message=data.get("message"),
        )


@dataclass
class Policy:
    """Main Policy entity."""

    name: str
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    policy_type: PolicyType = PolicyType.COMBINED
    rules: list[PolicyRule] = field(default_factory=list)
    legacy_id: Optional[str] = field(default=None, init=False)  # For compatibility

    def __post_init__(self) -> None:
        # Set legacy_id for compatibility
        self.legacy_id = self.policy_id

    # API associations
    api_configs: list[str] = field(default_factory=list)  # List of APIConfig IDs

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    is_active: bool = True

    # Additional settings
    settings: dict[str, Any] = field(default_factory=dict)
    # e.g., {"grace_period": 300, "soft_limit_percentage": 0.8}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "type": self.policy_type.value,
            "rules": [rule.to_dict() for rule in self.rules],
            "api_configs": self.api_configs,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "is_active": self.is_active,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls: type["Policy"], data: dict[str, Any]) -> "Policy":
        """Create from dictionary representation."""
        return cls(
            policy_id=data.get("policy_id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description"),
            policy_type=PolicyType(data.get("type", PolicyType.COMBINED.value)),
            rules=[PolicyRule.from_dict(r) for r in data.get("rules", [])],
            api_configs=data.get("api_configs", []),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(timezone.utc)
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now(timezone.utc)
            ),
            created_by=data.get("created_by"),
            is_active=data.get("is_active", True),
            settings=data.get("settings", {}),
        )

    def model_dump(self, exclude: Optional[set] = None) -> dict[str, Any]:
        """Pydantic-compatible dump method."""
        data = self.to_dict()
        # Convert 'type' back to 'policy_type' for compatibility with constructor
        if "type" in data:
            data["policy_type"] = data.pop("type")
        if exclude:
            for key in exclude:
                data.pop(key, None)
        return data


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation."""

    allowed: bool
    violated_rules: list[PolicyRule] = field(default_factory=list)
    warnings: list[PolicyRule] = field(
        default_factory=list
    )  # Changed to PolicyRule list
    remaining_quota: Optional[dict[str, float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    throttle_delay: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "allowed": self.allowed,
            "violated_rules": [rule.to_dict() for rule in self.violated_rules],
            "warnings": [rule.to_dict() for rule in self.warnings],
            "remaining_quota": self.remaining_quota,
            "metadata": self.metadata,
            "throttle_delay": self.throttle_delay,
        }

    def get_policy_headers(self) -> dict[str, str]:
        """Get HTTP headers for policy response."""
        headers = {"X-Policy-Allowed": "true" if self.allowed else "false"}

        if self.warnings:
            warning_messages = [w.message or "Policy warning" for w in self.warnings]
            headers["X-Policy-Warnings"] = "; ".join(warning_messages)

        if self.remaining_quota:
            for key, value in self.remaining_quota.items():
                header_key = f"X-Policy-Remaining-{key.replace('_', '-').title()}"
                headers[header_key] = str(value)

        if self.throttle_delay > 0:
            headers["X-Policy-Throttle-Delay"] = str(self.throttle_delay)

        return headers


@dataclass
class PolicyUpdate:
    """DTO for policy updates."""

    name: Optional[str] = None
    description: Optional[str] = None
    policy_type: Optional[PolicyType] = None
    rules: Optional[list[PolicyRule]] = None
    api_configs: Optional[list[str]] = None
    is_active: Optional[bool] = None
    settings: Optional[dict[str, Any]] = None


class PolicyRuleBuilder:
    """Fluent API for building policy rules."""

    def __init__(self) -> None:
        self._metric_key = None
        self._operator = None
        self._threshold = None
        self._period = None
        self._action = None
        self._message = None

    def with_rate_limit(self, threshold: int, period: str) -> "PolicyRuleBuilder":
        """Set rate limit parameters."""
        self._metric_key = "requests_count"
        self._operator = RuleOperator.GREATER_THAN
        self._threshold = threshold
        self._period = period
        self._action = "deny"  # Default action
        return self

    def with_token_limit(
        self,
        threshold: int,
        period: str,
        token_type: str = "total",  # nosec B107 - Not a password, just a parameter default
    ) -> "PolicyRuleBuilder":
        """Set token limit parameters."""
        if token_type == "input":  # nosec B105 - Not a password, just a parameter value
            self._metric_key = "input_words_count"
        elif (
            token_type
            == "output"  # nosec B105 - Not a password, just a parameter value
        ):
            self._metric_key = "output_words_count"
        else:
            self._metric_key = "total_words_count"
        self._operator = RuleOperator.GREATER_THAN
        self._threshold = threshold
        self._period = period
        self._action = "deny"  # Default action
        return self

    def with_credit_limit(self, threshold: float) -> "PolicyRuleBuilder":
        """Set credit limit parameters."""
        self._metric_key = "credits_used"
        self._operator = RuleOperator.GREATER_THAN
        self._threshold = threshold
        self._period = "lifetime"
        self._action = "deny"  # Default action
        return self

    def with_metric(self, metric_key: str) -> "PolicyRuleBuilder":
        """Set metric key."""
        self._metric_key = metric_key
        return self

    def with_operator(self, operator: RuleOperator) -> "PolicyRuleBuilder":
        """Set operator."""
        self._operator = operator
        return self

    def with_threshold(self, threshold: float) -> "PolicyRuleBuilder":
        """Set threshold."""
        self._threshold = threshold
        return self

    def with_period(self, period: str) -> "PolicyRuleBuilder":
        """Set period."""
        self._period = period
        return self

    def with_action(self, action: str) -> "PolicyRuleBuilder":
        """Set action."""
        self._action = action
        return self

    def with_message(self, message: str) -> "PolicyRuleBuilder":
        """Set message."""
        self._message = message
        return self

    def build(self) -> PolicyRule:
        """Build the policy rule."""
        if not self._metric_key:
            raise ValueError("metric_key is required")
        if not self._operator:
            raise ValueError("operator is required")
        if self._threshold is None:
            raise ValueError("threshold is required")
        if not self._period:
            raise ValueError("period is required")
        if not self._action:
            raise ValueError("action is required")

        return PolicyRule(
            metric_key=self._metric_key,
            operator=self._operator,
            threshold=self._threshold,
            period=self._period,
            action=self._action,
            message=self._message,
        )

    # Keep static methods for backward compatibility
    @staticmethod
    def rate_limit(requests_per_hour: int) -> PolicyRule:
        """Create a rate limiting rule."""
        return PolicyRule(
            metric_key="requests_count",
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=requests_per_hour,
            period="hour",
            message=f"Rate limit exceeded: {requests_per_hour} requests per hour",
        )

    @staticmethod
    def token_limit(max_tokens_per_day: int) -> PolicyRule:
        """Create a daily token limit rule."""
        return PolicyRule(
            metric_key="total_words_count",
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=max_tokens_per_day,
            period="day",
            message=f"Daily token limit exceeded: {max_tokens_per_day} tokens",
        )

    @staticmethod
    def credit_limit(max_credits: float) -> PolicyRule:
        """Create a credit limit rule."""
        return PolicyRule(
            metric_key="credits_used",
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=max_credits,
            period="lifetime",
            message=f"Credit limit exceeded: {max_credits} credits",
        )

    @staticmethod
    def custom_rule(
        metric_key: str, operator: RuleOperator, threshold: float, **kwargs: Any
    ) -> PolicyRule:
        """Create a custom rule."""
        return PolicyRule(
            metric_key=metric_key, operator=operator, threshold=threshold, **kwargs
        )
