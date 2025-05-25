"""Tests for policy models."""

import uuid
from datetime import datetime, timezone

from policies.models import (
    Policy,
    PolicyEvaluationResult,
    PolicyRule,
    PolicyRuleBuilder,
    PolicyType,
    RuleOperator,
)
from tests.unit.policies.test_builder_methods import (
    PolicyRuleBuilderMethods,  # noqa: F401
)
from tests.unit.policies.test_models_constants import (
    ACTION_DENY,
    ACTION_THROTTLE,
    ACTION_WARN,
    EXPECTED_RULE_COUNT,
    METRIC_CREDITS_USED,
    METRIC_REQUESTS_PER_HOUR,
    METRIC_TOTAL_TOKENS,
    PERIOD_DAY,
    PERIOD_HOUR,
    PERIOD_LIFETIME,
    THRESHOLD_CREDIT_HIGH,
    THRESHOLD_CREDIT_LOW,
    THRESHOLD_CUSTOM_METRIC,
    THRESHOLD_RATE_LIMIT_HOURLY,
    THRESHOLD_RULE_BUILDER_RATE,
    THRESHOLD_RULE_BUILDER_TOKEN,
    THRESHOLD_TEST_RULE,
    THRESHOLD_TOKEN_DAILY,
)


class TestPolicyRule:
    """Test PolicyRule model."""

    def test_create_policy_rule(self) -> None:
        """Test creating a policy rule."""
        rule = PolicyRule(
            metric_key=METRIC_REQUESTS_PER_HOUR,
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=THRESHOLD_RATE_LIMIT_HOURLY,
            period=PERIOD_HOUR,
            action=ACTION_DENY,
            message="Rate limit exceeded",
        )

        assert rule.rule_id is not None
        assert rule.metric_key == METRIC_REQUESTS_PER_HOUR
        assert rule.operator == RuleOperator.LESS_THAN_EQUAL
        assert rule.threshold == THRESHOLD_RATE_LIMIT_HOURLY
        assert rule.period == PERIOD_HOUR
        assert rule.action == ACTION_DENY
        assert rule.message == "Rate limit exceeded"

    def test_rule_to_dict(self) -> None:
        """Test converting rule to dictionary."""
        rule = PolicyRule(
            metric_key=METRIC_TOTAL_TOKENS,
            operator=RuleOperator.LESS_THAN,
            threshold=THRESHOLD_TOKEN_DAILY,
            period=PERIOD_DAY,
        )

        rule_dict = rule.to_dict()
        assert rule_dict["metric_key"] == METRIC_TOTAL_TOKENS
        assert rule_dict["operator"] == "lt"
        assert rule_dict["threshold"] == THRESHOLD_TOKEN_DAILY
        assert rule_dict["period"] == PERIOD_DAY
        assert rule_dict["action"] == ACTION_DENY

    def test_rule_from_dict(self) -> None:
        """Test creating rule from dictionary."""
        data = {
            "rule_id": str(uuid.uuid4()),
            "metric_key": METRIC_CREDITS_USED,
            "operator": "lte",
            "threshold": THRESHOLD_CREDIT_LOW,
            "period": PERIOD_LIFETIME,
            "action": ACTION_WARN,
            "message": "Credit limit warning",
        }

        rule = PolicyRule.from_dict(data)
        assert rule.rule_id == data["rule_id"]
        assert rule.metric_key == METRIC_CREDITS_USED
        assert rule.operator == RuleOperator.LESS_THAN_EQUAL
        assert rule.threshold == THRESHOLD_CREDIT_LOW
        assert rule.action == ACTION_WARN


class TestPolicy:
    """Test Policy model."""

    def test_create_policy(self) -> None:
        """Test creating a policy."""
        policy = Policy(
            name="Test Policy",
            description="A test policy",
            policy_type=PolicyType.COMBINED,
        )

        assert policy.policy_id is not None
        assert policy.name == "Test Policy"
        assert policy.description == "A test policy"
        assert policy.policy_type == PolicyType.COMBINED
        assert policy.is_active is True
        assert isinstance(policy.created_at, datetime)
        assert isinstance(policy.updated_at, datetime)

    def test_policy_with_rules(self) -> None:
        """Test creating a policy with rules."""
        rules = [
            PolicyRule(
                metric_key=METRIC_REQUESTS_PER_HOUR,
                operator=RuleOperator.LESS_THAN_EQUAL,
                threshold=THRESHOLD_RATE_LIMIT_HOURLY,
            ),
            PolicyRule(
                metric_key=METRIC_TOTAL_TOKENS,
                operator=RuleOperator.LESS_THAN,
                threshold=10000,
            ),
        ]

        policy = Policy(name="Limited Policy", rules=rules)

        assert len(policy.rules) == EXPECTED_RULE_COUNT
        assert policy.rules[0].metric_key == METRIC_REQUESTS_PER_HOUR
        assert policy.rules[1].metric_key == METRIC_TOTAL_TOKENS

    def test_policy_to_dict(self) -> None:
        """Test converting policy to dictionary."""
        policy = Policy(
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            settings={"grace_period": THRESHOLD_TEST_RULE},
        )

        policy_dict = policy.to_dict()
        assert policy_dict["name"] == "Test Policy"
        assert policy_dict["type"] == "rate_limit"
        assert policy_dict["settings"]["grace_period"] == THRESHOLD_TEST_RULE
        assert "created_at" in policy_dict
        assert "updated_at" in policy_dict

    def test_policy_from_dict(self) -> None:
        """Test creating policy from dictionary."""
        data = {
            "policy_id": str(uuid.uuid4()),
            "name": "Restored Policy",
            "description": "A restored policy",
            "type": "token_limit",
            "is_active": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "rules": [
                {
                    "metric_key": METRIC_TOTAL_TOKENS,
                    "operator": "lte",
                    "threshold": 5000,
                    "period": PERIOD_DAY,
                }
            ],
        }

        policy = Policy.from_dict(data)
        assert policy.policy_id == data["policy_id"]
        assert policy.name == "Restored Policy"
        assert policy.policy_type == PolicyType.TOKEN_LIMIT
        assert policy.is_active is False
        assert len(policy.rules) == 1


class TestPolicyEvaluationResult:
    """Test PolicyEvaluationResult model."""

    def test_create_evaluation_result(self) -> None:
        """Test creating an evaluation result."""
        result = PolicyEvaluationResult(allowed=True)

        assert result.allowed is True
        assert len(result.violated_rules) == 0
        assert len(result.warnings) == 0
        assert result.remaining_quota is None

    def test_evaluation_with_violations(self) -> None:
        """Test evaluation result with violations."""
        violated_rule = PolicyRule(
            metric_key=METRIC_REQUESTS_PER_HOUR,
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=THRESHOLD_RATE_LIMIT_HOURLY,
            message="Rate limit exceeded",
        )

        result = PolicyEvaluationResult(
            allowed=False,
            violated_rules=[violated_rule],
            warnings=["Approaching daily limit"],
            remaining_quota={METRIC_REQUESTS_PER_HOUR: 0, METRIC_TOTAL_TOKENS: 500},
        )

        assert result.allowed is False
        assert len(result.violated_rules) == 1
        assert result.violated_rules[0].message == "Rate limit exceeded"
        assert len(result.warnings) == 1
        assert result.remaining_quota[METRIC_REQUESTS_PER_HOUR] == 0


class TestPolicyRuleBuilder:
    """Test PolicyRuleBuilder utility."""

    def test_rate_limit_rule(self) -> None:
        """Test creating a rate limit rule."""
        rule = PolicyRuleBuilder.rate_limit(THRESHOLD_RULE_BUILDER_RATE)

        assert rule.metric_key == METRIC_REQUESTS_PER_HOUR
        assert rule.operator == RuleOperator.LESS_THAN_EQUAL
        assert rule.threshold == THRESHOLD_RULE_BUILDER_RATE
        assert rule.period == PERIOD_HOUR
        assert f"{THRESHOLD_RULE_BUILDER_RATE} requests per hour" in rule.message

    def test_token_limit_rule(self) -> None:
        """Test creating a token limit rule."""
        rule = PolicyRuleBuilder.token_limit(THRESHOLD_RULE_BUILDER_TOKEN)

        assert rule.metric_key == "total_tokens_per_day"
        assert rule.operator == RuleOperator.LESS_THAN_EQUAL
        assert rule.threshold == THRESHOLD_RULE_BUILDER_TOKEN
        assert rule.period == PERIOD_DAY
        assert f"{THRESHOLD_RULE_BUILDER_TOKEN} tokens" in rule.message

    def test_credit_limit_rule(self) -> None:
        """Test creating a credit limit rule."""
        rule = PolicyRuleBuilder.credit_limit(THRESHOLD_CREDIT_HIGH)

        assert rule.metric_key == METRIC_CREDITS_USED
        assert rule.operator == RuleOperator.LESS_THAN_EQUAL
        assert rule.threshold == THRESHOLD_CREDIT_HIGH
        assert rule.period == PERIOD_LIFETIME
        assert f"{THRESHOLD_CREDIT_HIGH} credits" in rule.message

    def test_custom_rule(self) -> None:
        """Test creating a custom rule."""
        rule = PolicyRuleBuilder.custom_rule(
            metric_key="custom_metric",
            operator=RuleOperator.GREATER_THAN,
            threshold=THRESHOLD_CUSTOM_METRIC,
            period=PERIOD_HOUR,
            action=ACTION_THROTTLE,
            message="Custom threshold exceeded",
        )

        assert rule.metric_key == "custom_metric"
        assert rule.operator == RuleOperator.GREATER_THAN
        assert rule.threshold == THRESHOLD_CUSTOM_METRIC
        assert rule.period == PERIOD_HOUR
        assert rule.action == ACTION_THROTTLE
        assert rule.message == "Custom threshold exceeded"
