"""Unit tests for policy API endpoints operator transformation."""

import pytest

from api.endpoints.policies import (
    OPERATOR_DISPLAY_MAPPING,
    OPERATOR_MAPPING,
    transform_domain_rule_to_frontend,
    transform_frontend_rule_to_domain,
    transform_policy_response,
)


class TestOperatorTransformation:
    """Test operator transformation between frontend and backend formats."""

    def test_frontend_to_domain_operator_mapping(self) -> None:
        """Test that frontend operators are correctly mapped to domain operators."""
        for frontend_op, domain_op in OPERATOR_MAPPING.items():
            rule = {
                "metric_key": "requests_count",
                "operator": frontend_op,
                "threshold": 100,
                "period": "daily",
                "action": "block",
            }

            transformed = transform_frontend_rule_to_domain(rule)

            assert transformed["operator"] == domain_op
            assert transformed["action"] == "deny"  # block -> deny

    def test_domain_to_frontend_operator_mapping(self) -> None:
        """Test that domain operators are correctly mapped to frontend operators."""
        for domain_op, frontend_op in OPERATOR_DISPLAY_MAPPING.items():
            rule = {
                "metric_key": "requests_count",
                "operator": domain_op,
                "threshold": 100,
                "period": "daily",
                "action": "deny",
            }

            transformed = transform_domain_rule_to_frontend(rule)

            assert transformed["operator"] == frontend_op
            assert transformed["action"] == "block"  # deny -> block

    def test_invalid_frontend_operator_raises_error(self) -> None:
        """Test that invalid frontend operators raise ValueError."""
        rule = {
            "metric_key": "requests_count",
            "operator": "invalid_operator",
            "threshold": 100,
        }

        with pytest.raises(ValueError, match="Invalid operator") as exc_info:
            transform_frontend_rule_to_domain(rule)

        assert "Invalid operator" in str(exc_info.value)
        assert "invalid_operator" in str(exc_info.value)

    def test_already_valid_domain_operator_passes_through(self) -> None:
        """Test that already valid domain operators pass through unchanged."""
        rule = {
            "metric_key": "requests_count",
            "operator": "gt",  # Already a valid domain operator
            "threshold": 100,
        }

        transformed = transform_frontend_rule_to_domain(rule)
        assert transformed["operator"] == "gt"

    def test_empty_rule_returns_empty(self) -> None:
        """Test that empty/None rules are handled gracefully."""
        assert transform_frontend_rule_to_domain(None) is None
        assert transform_frontend_rule_to_domain({}) == {}
        assert transform_domain_rule_to_frontend(None) is None
        assert transform_domain_rule_to_frontend({}) == {}

    def test_policy_response_transformation(self) -> None:
        """Test complete policy response transformation."""
        policy_dict = {
            "id": "policy-123",
            "name": "Test Policy",
            "rules": [
                {
                    "metric_key": "requests_count",
                    "operator": "gt",
                    "threshold": 100,
                    "action": "deny",
                },
                {
                    "metric_key": "total_tokens",
                    "operator": "lte",
                    "threshold": 1000,
                    "action": "deny",
                },
            ],
        }

        transformed = transform_policy_response(policy_dict)

        assert transformed["rules"][0]["operator"] == "greater_than"
        assert transformed["rules"][0]["action"] == "block"
        assert transformed["rules"][1]["operator"] == "less_than_or_equal"
        assert transformed["rules"][1]["action"] == "block"


class TestAllOperatorsCovered:
    """Ensure all operators are properly mapped."""

    def test_all_operators_have_mappings(self) -> None:
        """Test that all operators have bidirectional mappings."""
        # Check frontend to domain
        assert "less_than" in OPERATOR_MAPPING
        assert "less_than_or_equal" in OPERATOR_MAPPING
        assert "greater_than" in OPERATOR_MAPPING
        assert "greater_than_or_equal" in OPERATOR_MAPPING
        assert "equal" in OPERATOR_MAPPING
        assert "not_equal" in OPERATOR_MAPPING

        # Check domain to frontend
        assert "lt" in OPERATOR_DISPLAY_MAPPING
        assert "lte" in OPERATOR_DISPLAY_MAPPING
        assert "gt" in OPERATOR_DISPLAY_MAPPING
        assert "gte" in OPERATOR_DISPLAY_MAPPING
        assert "eq" in OPERATOR_DISPLAY_MAPPING
        assert "ne" in OPERATOR_DISPLAY_MAPPING

    def test_mappings_are_consistent(self) -> None:
        """Test that mappings are consistent in both directions."""
        for frontend_op, domain_op in OPERATOR_MAPPING.items():
            assert OPERATOR_DISPLAY_MAPPING[domain_op] == frontend_op

        for domain_op, frontend_op in OPERATOR_DISPLAY_MAPPING.items():
            assert OPERATOR_MAPPING[frontend_op] == domain_op
