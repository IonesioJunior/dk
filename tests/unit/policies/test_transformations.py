"""
Unit tests for policy transformation functions.

Tests the transformation between frontend and backend policy formats,
including operator mapping, action mapping, and period conversions.
"""


import pytest

from policies.models import (
    Policy,
    PolicyRule,
    PolicyType,
    RuleOperator,
)


# Transformation functions for testing
def transform_frontend_operator_to_backend(operator: str) -> RuleOperator:
    """Transform frontend operator to backend enum."""
    mapping = {
        "greater_than": RuleOperator.GREATER_THAN,
        "greater_than_or_equal": RuleOperator.GREATER_THAN_EQUAL,
        "less_than": RuleOperator.LESS_THAN,
        "less_than_or_equal": RuleOperator.LESS_THAN_EQUAL,
        "equal": RuleOperator.EQUAL,
        "not_equal": RuleOperator.NOT_EQUAL,
        "gt": RuleOperator.GREATER_THAN,
        "gte": RuleOperator.GREATER_THAN_EQUAL,
        "lt": RuleOperator.LESS_THAN,
        "lte": RuleOperator.LESS_THAN_EQUAL,
        "eq": RuleOperator.EQUAL,
        "ne": RuleOperator.NOT_EQUAL,
    }
    if operator not in mapping:
        raise ValueError(f"Invalid operator: {operator}")
    return mapping[operator]


def transform_backend_operator_to_frontend(operator: RuleOperator) -> str:
    """Transform backend enum to frontend string."""
    mapping = {
        RuleOperator.GREATER_THAN: "greater_than",
        RuleOperator.GREATER_THAN_EQUAL: "greater_than_or_equal",
        RuleOperator.LESS_THAN: "less_than",
        RuleOperator.LESS_THAN_EQUAL: "less_than_or_equal",
        RuleOperator.EQUAL: "equal",
        RuleOperator.NOT_EQUAL: "not_equal",
    }
    return mapping[operator]


def transform_frontend_action_to_backend(action: str) -> str:
    """Transform frontend action to backend."""
    if action == "block":
        return "deny"
    return action


def transform_backend_action_to_frontend(action: str) -> str:
    """Transform backend action to frontend."""
    if action == "deny":
        return "block"
    return action


def transform_frontend_period_to_backend(period: str) -> str:
    """Transform frontend period to backend."""
    mapping = {
        "hourly": "hour",
        "daily": "day",
        "monthly": "month",
        "lifetime": "lifetime",
    }
    return mapping.get(period, period)


def transform_backend_period_to_frontend(period: str) -> str:
    """Transform backend period to frontend."""
    mapping = {
        "hour": "hourly",
        "day": "daily",
        "month": "monthly",
        "lifetime": "lifetime",
    }
    return mapping.get(period, period)


def transform_frontend_policy_to_backend(policy: dict) -> dict:
    """Transform frontend policy to backend format."""
    result = {}

    # Required fields
    result["name"] = policy["name"]

    # Type transformation
    if "type" in policy:
        type_str = policy["type"].replace("-", "_").upper()
        result["policy_type"] = PolicyType[type_str]

    # Optional fields
    if "description" in policy:
        result["description"] = policy["description"]

    if "settings" in policy:
        result["settings"] = policy["settings"]

    # Transform rules
    if "rules" in policy:
        transformed_rules = []
        for rule in policy["rules"]:
            # Only copy known fields
            transformed_rule = {}

            # Copy required fields
            transformed_rule["metric_key"] = rule["metric_key"]
            transformed_rule["threshold"] = rule["threshold"]

            # Transform operator
            operator = transform_frontend_operator_to_backend(rule["operator"])
            transformed_rule["operator"] = (
                operator.value if hasattr(operator, "value") else operator
            )

            # Transform period
            transformed_rule["period"] = transform_frontend_period_to_backend(
                rule.get("period", "hour")
            )

            # Transform action
            transformed_rule["action"] = transform_frontend_action_to_backend(
                rule.get("action", "deny")
            )

            # Optional fields
            if "message" in rule:
                transformed_rule["message"] = rule["message"]

            # Convert threshold to number if it's a string
            if isinstance(transformed_rule["threshold"], str):
                transformed_rule["threshold"] = float(transformed_rule["threshold"])
                # Convert to int if it's a whole number
                if transformed_rule["threshold"].is_integer():
                    transformed_rule["threshold"] = int(transformed_rule["threshold"])

            transformed_rules.append(transformed_rule)

        result["rules"] = transformed_rules
    else:
        result["rules"] = []

    return result


def transform_backend_policy_to_frontend(policy: Policy) -> dict:
    """Transform backend policy to frontend format."""
    policy_dict = policy.to_dict()
    policy_dict["policy_type"] = policy.policy_type.value
    if "rules" in policy_dict:
        policy_dict["rules"] = [
            {
                **rule,
                "operator": transform_backend_operator_to_frontend(
                    RuleOperator(rule["operator"])
                ),
                "period": transform_backend_period_to_frontend(rule.get("period", "")),
                "action": transform_backend_action_to_frontend(
                    rule.get("action", "deny")
                ),
            }
            for rule in policy_dict["rules"]
        ]
    return policy_dict


class TestOperatorTransformations:
    """Test operator transformations between frontend and backend."""

    def test_frontend_to_backend_operators(self):
        """Test all frontend operator mappings to backend."""
        test_cases = [
            ("greater_than", RuleOperator.GREATER_THAN),
            ("greater_than_or_equal", RuleOperator.GREATER_THAN_EQUAL),
            ("less_than", RuleOperator.LESS_THAN),
            ("less_than_or_equal", RuleOperator.LESS_THAN_EQUAL),
            ("equal", RuleOperator.EQUAL),
            ("not_equal", RuleOperator.NOT_EQUAL),
        ]

        for frontend, expected_backend in test_cases:
            result = transform_frontend_operator_to_backend(frontend)
            assert result == expected_backend

    def test_backend_to_frontend_operators(self):
        """Test all backend operator mappings to frontend."""
        test_cases = [
            (RuleOperator.GREATER_THAN, "greater_than"),
            (RuleOperator.GREATER_THAN_EQUAL, "greater_than_or_equal"),
            (RuleOperator.LESS_THAN, "less_than"),
            (RuleOperator.LESS_THAN_EQUAL, "less_than_or_equal"),
            (RuleOperator.EQUAL, "equal"),
            (RuleOperator.NOT_EQUAL, "not_equal"),
        ]

        for backend, expected_frontend in test_cases:
            result = transform_backend_operator_to_frontend(backend)
            assert result == expected_frontend

    def test_invalid_frontend_operator(self):
        """Test handling of invalid frontend operator."""
        with pytest.raises(ValueError, match="Invalid operator"):
            transform_frontend_operator_to_backend("invalid_operator")

    def test_already_backend_operator(self):
        """Test that backend operators pass through unchanged."""
        # If frontend sends backend format, it should work
        result = transform_frontend_operator_to_backend("gt")
        assert result == RuleOperator.GREATER_THAN


class TestActionTransformations:
    """Test action transformations between frontend and backend."""

    def test_frontend_to_backend_actions(self):
        """Test all frontend action mappings to backend."""
        test_cases = [
            ("block", "deny"),
            ("warn", "warn"),
            ("throttle", "throttle"),
        ]

        for frontend, expected_backend in test_cases:
            result = transform_frontend_action_to_backend(frontend)
            assert result == expected_backend

    def test_backend_to_frontend_actions(self):
        """Test all backend action mappings to frontend."""
        test_cases = [
            ("deny", "block"),
            ("warn", "warn"),
            ("throttle", "throttle"),
        ]

        for backend, expected_frontend in test_cases:
            result = transform_backend_action_to_frontend(backend)
            assert result == expected_frontend

    def test_already_backend_action(self):
        """Test that backend actions pass through when appropriate."""
        # Frontend might send "deny" which should map to DENY
        result = transform_frontend_action_to_backend("deny")
        assert result == "deny"


class TestPeriodTransformations:
    """Test period transformations between frontend and backend."""

    def test_frontend_to_backend_periods(self):
        """Test all frontend period mappings to backend."""
        test_cases = [
            ("hourly", "hour"),
            ("daily", "day"),
            ("monthly", "month"),
            ("lifetime", "lifetime"),
        ]

        for frontend, expected_backend in test_cases:
            result = transform_frontend_period_to_backend(frontend)
            assert result == expected_backend

    def test_backend_to_frontend_periods(self):
        """Test all backend period mappings to frontend."""
        test_cases = [
            ("hour", "hourly"),
            ("day", "daily"),
            ("month", "monthly"),
            ("lifetime", "lifetime"),
        ]

        for backend, expected_frontend in test_cases:
            result = transform_backend_period_to_frontend(backend)
            assert result == expected_frontend

    def test_already_backend_period(self):
        """Test that backend periods pass through unchanged."""
        result = transform_frontend_period_to_backend("hour")
        assert result == "hour"


class TestPolicyTransformations:
    """Test complete policy transformations."""

    def test_transform_frontend_policy_to_backend(self):
        """Test transforming a complete frontend policy to backend format."""
        frontend_policy = {
            "name": "Test Policy",
            "type": "rate_limit",
            "description": "Test description",
            "rules": [
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": 100,
                    "period": "hourly",
                    "action": "block",
                    "message": "Too many requests",
                },
                {
                    "metric_key": "total_words_count",
                    "operator": "less_than_or_equal",
                    "threshold": 10000,
                    "period": "daily",
                    "action": "warn",
                    "message": "Approaching limit",
                },
            ],
            "settings": {"custom": "value"},
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)

        assert backend_policy["name"] == "Test Policy"
        assert backend_policy["policy_type"] == PolicyType.RATE_LIMIT
        assert len(backend_policy["rules"]) == 2

        # Check first rule transformation
        rule1 = backend_policy["rules"][0]
        assert rule1["operator"] == "gt"  # The value of RuleOperator.GREATER_THAN
        assert rule1["period"] == "hour"
        assert rule1["action"] == "deny"

        # Check second rule transformation
        rule2 = backend_policy["rules"][1]
        assert rule2["operator"] == "lte"  # The value of RuleOperator.LESS_THAN_EQUAL
        assert rule2["period"] == "day"
        assert rule2["action"] == "warn"

    def test_transform_backend_policy_to_frontend(self):
        """Test transforming a complete backend policy to frontend format."""
        backend_policy = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.COMBINED,
            description="Test description",
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=100,
                    period="hour",
                    action="deny",
                    message="Too many requests",
                ),
                PolicyRule(
                    metric_key="credits_used",
                    operator=RuleOperator.GREATER_THAN_EQUAL,
                    threshold=80,
                    period="lifetime",
                    action="throttle",
                ),
            ],
            settings={"initial_credits": 100},
        )

        frontend_policy = transform_backend_policy_to_frontend(backend_policy)

        assert frontend_policy["policy_id"] == "test_id"
        assert frontend_policy["name"] == "Test Policy"
        assert frontend_policy["policy_type"] == "combined"
        assert len(frontend_policy["rules"]) == 2

        # Check first rule transformation
        rule1 = frontend_policy["rules"][0]
        assert rule1["operator"] == "greater_than"
        assert rule1["period"] == "hourly"
        assert rule1["action"] == "block"

        # Check second rule transformation
        rule2 = frontend_policy["rules"][1]
        assert rule2["operator"] == "greater_than_or_equal"
        assert rule2["period"] == "lifetime"
        assert rule2["action"] == "throttle"

    def test_transform_policy_with_empty_rules(self):
        """Test transforming policies with no rules."""
        frontend_policy = {
            "name": "Empty Policy",
            "type": "rate_limit",
            "rules": [],
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)
        assert backend_policy["rules"] == []

        # Test backend to frontend
        backend_obj = Policy(
            policy_id="test",
            name="Empty Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=[],
        )
        frontend_result = transform_backend_policy_to_frontend(backend_obj)
        assert frontend_result["rules"] == []

    def test_transform_policy_preserves_optional_fields(self):
        """Test that transformation preserves optional fields."""
        frontend_policy = {
            "name": "Test Policy",
            "type": "credit_based",
            "description": "Detailed description",
            "rules": [],
            "settings": {
                "initial_credits": 1000,
                "credit_refresh_period": "monthly",
                "custom_field": "custom_value",
            },
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)

        assert backend_policy["description"] == "Detailed description"
        assert backend_policy["settings"]["initial_credits"] == 1000
        assert backend_policy["settings"]["custom_field"] == "custom_value"

    def test_transform_handles_missing_optional_fields(self):
        """Test transformation with missing optional fields."""
        # Minimal frontend policy
        frontend_policy = {
            "name": "Minimal Policy",
            "type": "rate_limit",
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)

        assert backend_policy["name"] == "Minimal Policy"
        assert backend_policy["policy_type"] == PolicyType.RATE_LIMIT
        assert backend_policy.get("description") is None
        assert backend_policy.get("rules") == []
        assert backend_policy.get("settings") is None


class TestEdgeCaseTransformations:
    """Test edge cases in transformations."""

    def test_transform_with_null_values(self):
        """Test handling of null values in transformations."""
        frontend_policy = {
            "name": "Test Policy",
            "type": "rate_limit",
            "description": None,
            "rules": [
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": 100,
                    "period": "hourly",
                    "action": "block",
                    "message": None,  # Null message
                }
            ],
            "settings": None,
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)

        assert backend_policy["description"] is None
        assert backend_policy["rules"][0]["message"] is None
        assert backend_policy["settings"] is None

    def test_transform_with_extra_fields(self):
        """Test that extra fields are preserved or ignored appropriately."""
        frontend_policy = {
            "name": "Test Policy",
            "type": "rate_limit",
            "extra_field": "should_be_ignored",
            "rules": [
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": 100,
                    "period": "hourly",
                    "action": "block",
                    "extra_rule_field": "ignored",
                }
            ],
        }

        # Should not raise error
        backend_policy = transform_frontend_policy_to_backend(frontend_policy)
        assert "extra_field" not in backend_policy
        assert "extra_rule_field" not in backend_policy["rules"][0]

    def test_case_insensitive_type_transformation(self):
        """Test that policy types are case-insensitive."""
        test_cases = [
            ("RATE_LIMIT", PolicyType.RATE_LIMIT),
            ("Rate_Limit", PolicyType.RATE_LIMIT),
            ("rate_limit", PolicyType.RATE_LIMIT),
            ("token_limit", PolicyType.TOKEN_LIMIT),
            ("TOKEN_LIMIT", PolicyType.TOKEN_LIMIT),
        ]

        for input_type, expected_type in test_cases:
            frontend_policy = {
                "name": "Test",
                "type": input_type,
            }
            backend_policy = transform_frontend_policy_to_backend(frontend_policy)
            assert backend_policy["policy_type"] == expected_type

    def test_transform_preserves_rule_order(self):
        """Test that rule order is preserved during transformation."""
        frontend_policy = {
            "name": "Test Policy",
            "type": "combined",
            "rules": [
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": 10,
                    "period": "hourly",
                    "action": "warn",
                },
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": 50,
                    "period": "hourly",
                    "action": "throttle",
                },
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": 100,
                    "period": "hourly",
                    "action": "block",
                },
            ],
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)

        # Verify order is preserved
        assert backend_policy["rules"][0]["threshold"] == 10
        assert backend_policy["rules"][0]["action"] == "warn"
        assert backend_policy["rules"][1]["threshold"] == 50
        assert backend_policy["rules"][1]["action"] == "throttle"
        assert backend_policy["rules"][2]["threshold"] == 100
        assert backend_policy["rules"][2]["action"] == "deny"

    def test_numeric_string_threshold_conversion(self):
        """Test that string thresholds are converted to numbers."""
        frontend_policy = {
            "name": "Test Policy",
            "type": "rate_limit",
            "rules": [
                {
                    "metric_key": "requests_count",
                    "operator": "greater_than",
                    "threshold": "100",  # String instead of number
                    "period": "hourly",
                    "action": "block",
                }
            ],
        }

        backend_policy = transform_frontend_policy_to_backend(frontend_policy)
        assert backend_policy["rules"][0]["threshold"] == 100
        assert isinstance(backend_policy["rules"][0]["threshold"], (int, float))
