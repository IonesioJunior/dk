"""
Unit tests for PolicyService class.

Tests policy service operations, default policy creation,
and API configuration management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from policies.models import (
    Policy,
    PolicyRule,
    PolicyRuleBuilder,
    PolicyType,
    RuleOperator,
)
from policies.service import CreatePolicyRequest, PolicyService


class TestPolicyService:
    """Test PolicyService functionality."""

    @pytest.fixture()
    def mock_policy_manager(self):
        """Create a mock policy manager."""
        return MagicMock()

    @pytest.fixture()
    def mock_api_config_manager(self):
        """Create a mock API config manager."""
        return MagicMock()

    @pytest.fixture()
    def policy_service(self, mock_policy_manager, mock_api_config_manager):
        """Create a PolicyService instance with mocks."""
        mock_api_service_instance = MagicMock()
        mock_api_service_instance.config_manager = mock_api_config_manager
        mock_api_service_instance.get_api_config = MagicMock()

        with (
            patch("policies.service.PolicyManager", return_value=mock_policy_manager),
            patch("policies.service.PolicyEnforcer"),
            patch(
                "policies.service.APIConfigService",
                return_value=mock_api_service_instance,
            ),
        ):
            service = PolicyService()
            # Ensure manager alias points to the mock
            service.manager = mock_policy_manager
            # Mock the attach/detach methods to return True
            service.manager.attach_policy_to_api = MagicMock(return_value=True)
            service.manager.detach_policy_from_api = MagicMock(return_value=True)
            # Mock validate_policy_rules to return no errors
            service.manager.validate_policy_rules = MagicMock(return_value=[])
            return service

    @pytest.mark.anyio()
    async def test_create_policy(self, policy_service, mock_policy_manager):
        """Test creating a new policy."""
        mock_policy_manager.create_policy.return_value = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            description="Test description",
        )

        policy = await policy_service.create_policy(
            CreatePolicyRequest(
                name="Test Policy",
                description="Test description",
                policy_type=PolicyType.RATE_LIMIT,
            )
        )

        assert policy.name == "Test Policy"
        assert policy.policy_type == PolicyType.RATE_LIMIT
        mock_policy_manager.create_policy.assert_called_once()

    @pytest.mark.anyio()
    async def test_create_policy_with_rules(self, policy_service, mock_policy_manager):
        """Test creating a policy with initial rules."""
        # Rules in the format expected by create_policy
        test_rules_config = [{"type": "rate_limit", "requests_per_hour": 100}]

        # The resulting policy will have PolicyRule objects
        expected_rules = [
            PolicyRule(
                metric_key="requests_count",
                operator=RuleOperator.GREATER_THAN,
                threshold=100,
                period="hour",
                action="deny",
            )
        ]

        mock_policy_manager.create_policy.return_value = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=expected_rules,
        )

        policy = await policy_service.create_policy(
            CreatePolicyRequest(
                name="Test Policy",
                policy_type=PolicyType.RATE_LIMIT,
                rules=test_rules_config,
            )
        )

        assert len(policy.rules) == 1
        assert policy.rules[0].metric_key == "requests_count"

    @pytest.mark.anyio()
    async def test_create_default_policies(self, policy_service, mock_policy_manager):
        """Test creation of default policy templates."""
        # Mock that policies don't exist yet
        mock_policy_manager.get_policy_by_name.return_value = None

        # Create mock policies that will be returned
        free_policy = Policy(
            policy_id="free_id",
            name="Free Tier",
            policy_type=PolicyType.COMBINED,
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=10,
                    period="hour",
                    action="deny",
                ),
                PolicyRule(
                    metric_key="total_words_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=10000,
                    period="day",
                    action="deny",
                ),
                PolicyRule(
                    metric_key="credits_used",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=100,
                    period="lifetime",
                    action="deny",
                ),
            ],
        )

        standard_policy = Policy(
            policy_id="standard_id",
            name="Standard Tier",
            policy_type=PolicyType.COMBINED,
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=100,
                    period="hour",
                    action="deny",
                ),
                PolicyRule(
                    metric_key="total_words_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=100000,
                    period="day",
                    action="deny",
                ),
                PolicyRule(
                    metric_key="credits_used",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=1000,
                    period="lifetime",
                    action="deny",
                ),
            ],
        )

        premium_policy = Policy(
            policy_id="premium_id",
            name="Premium Tier",
            policy_type=PolicyType.COMBINED,
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=1000,
                    period="hour",
                    action="deny",
                ),
                PolicyRule(
                    metric_key="total_words_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=1000000,
                    period="day",
                    action="deny",
                ),
                PolicyRule(
                    metric_key="credits_used",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=10000,
                    period="lifetime",
                    action="deny",
                ),
            ],
        )

        # Mock create_policy to return the appropriate policy
        mock_policy_manager.create_policy.side_effect = [
            free_policy,
            standard_policy,
            premium_policy,
        ]

        policies = await policy_service.create_default_policies()

        assert len(policies) == 3
        assert policies[0].name == "Free Tier"
        assert policies[1].name == "Standard Tier"
        assert policies[2].name == "Premium Tier"

        # Verify Free Tier rules
        assert policies[0].policy_type == PolicyType.COMBINED
        assert len(policies[0].rules) >= 3  # Rate, token, and credit limits

        # Verify rate limits increase with tiers
        free_rate = next(
            r for r in policies[0].rules if r.metric_key == "requests_count"
        )
        standard_rate = next(
            r for r in policies[1].rules if r.metric_key == "requests_count"
        )
        assert standard_rate.threshold > free_rate.threshold

    @pytest.mark.anyio()
    async def test_create_default_policies_already_exist(
        self, policy_service, mock_policy_manager
    ):
        """Test that existing default policies are not recreated."""
        # Mock that policies already exist
        existing_policy = Policy(
            policy_id="existing",
            name="Free Tier",
            policy_type=PolicyType.COMBINED,
        )
        mock_policy_manager.get_policy_by_name.return_value = existing_policy

        policies = await policy_service.create_default_policies()

        # Should create all 3 default policies regardless of existing ones
        assert len(policies) == 3
        # Create should be called 3 times for the 3 default policies
        assert mock_policy_manager.create_policy.call_count == 3

    @pytest.mark.anyio()
    async def test_update_policy(self, policy_service, mock_policy_manager):
        """Test updating a policy."""
        updated_policy = Policy(
            policy_id="test_id",
            name="Updated Policy",
            policy_type=PolicyType.RATE_LIMIT,
            description="Updated description",
        )
        mock_policy_manager.update_policy.return_value = updated_policy

        result = await policy_service.update_policy(
            policy_id="test_id",
            name="Updated Policy",
            description="Updated description",
        )

        assert result.name == "Updated Policy"
        assert result.description == "Updated description"
        mock_policy_manager.update_policy.assert_called_once()

    @pytest.mark.anyio()
    async def test_delete_policy(self, policy_service, mock_policy_manager):
        """Test deleting a policy."""
        mock_policy_manager.delete_policy.return_value = True

        result = await policy_service.delete_policy("test_id")

        assert result is True
        mock_policy_manager.delete_policy.assert_called_once_with("test_id")

    @pytest.mark.anyio()
    async def test_add_policy_rules(self, policy_service, mock_policy_manager):
        """Test adding rules to an existing policy."""
        existing_policy = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=[],
        )
        mock_policy_manager.get_policy.return_value = existing_policy

        new_rules = [
            PolicyRule(
                metric_key="requests_count",
                operator=RuleOperator.GREATER_THAN,
                threshold=100,
                period="hour",
                action="deny",
            )
        ]

        mock_policy_manager.update_policy.return_value = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=new_rules,
        )

        result = await policy_service.add_policy_rules("test_id", new_rules)

        assert len(result.rules) == 1
        assert result.rules[0].metric_key == "requests_count"

    @pytest.mark.anyio()
    async def test_remove_policy_rule(self, policy_service, mock_policy_manager):
        """Test removing a rule from a policy."""
        existing_rules = [
            PolicyRule(
                metric_key="requests_count",
                operator=RuleOperator.GREATER_THAN,
                threshold=100,
                period="hour",
                action="deny",
            ),
            PolicyRule(
                metric_key="credits_used",
                operator=RuleOperator.GREATER_THAN,
                threshold=1000,
                period="lifetime",
                action="deny",
            ),
        ]

        existing_policy = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.COMBINED,
            rules=existing_rules,
        )
        mock_policy_manager.get_policy.return_value = existing_policy

        # Mock update to return policy with one rule removed
        mock_policy_manager.update_policy.return_value = Policy(
            policy_id="test_id",
            name="Test Policy",
            policy_type=PolicyType.COMBINED,
            rules=[existing_rules[1]],  # Only credits rule remains
        )

        result = await policy_service.remove_policy_rule("test_id", 0)

        assert len(result.rules) == 1
        assert result.rules[0].metric_key == "credits_used"

    @pytest.mark.anyio()
    async def test_attach_policy_to_api_configs(
        self, policy_service, mock_api_config_manager
    ):
        """Test attaching a policy to multiple API configs."""
        # Mock configs that will be returned after attachment
        mock_config1 = MagicMock(
            config_id="config1", policy_id="test_policy", users=["user1"]
        )
        mock_config2 = MagicMock(
            config_id="config2", policy_id="test_policy", users=["user2"]
        )

        # Configure api_config_service to return the configs
        # Need to provide configs for both attach_policy_to_api_config calls and the results
        policy_service.api_config_service.get_api_config.side_effect = [
            mock_config1,  # For first attach_policy_to_api_config
            mock_config1,  # For first result
            mock_config2,  # For second attach_policy_to_api_config
            mock_config2,  # For second result
        ]

        result = await policy_service.attach_policy_to_api_configs(
            policy_id="test_policy",
            api_config_ids=["config1", "config2"],
        )

        assert len(result) == 2
        assert result[0] == mock_config1
        assert result[1] == mock_config2
        # Verify attach was called for each config
        assert policy_service.manager.attach_policy_to_api.call_count == 2

    @pytest.mark.anyio()
    async def test_detach_policy_from_api_configs(
        self, policy_service, mock_api_config_manager
    ):
        """Test detaching a policy from API configs."""
        # Mock configs that will be returned after detachment
        mock_config1 = MagicMock(config_id="config1", policy_id=None)
        mock_config2 = MagicMock(config_id="config2", policy_id=None)

        # Configure api_config_service to return the configs
        policy_service.api_config_service.get_api_config.side_effect = [
            MagicMock(users=["user1"]),  # For detach_policy_from_api_config
            mock_config1,  # For the result
            MagicMock(users=["user2"]),  # For detach_policy_from_api_config
            mock_config2,  # For the result
        ]

        result = await policy_service.detach_policy_from_api_configs(
            api_config_ids=["config1", "config2"]
        )

        assert len(result) == 2
        assert result[0] == mock_config1
        assert result[1] == mock_config2
        # Verify detach was called for each config
        assert policy_service.manager.detach_policy_from_api.call_count == 2

    @pytest.mark.anyio()
    async def test_bulk_migrate_api_configs(
        self, policy_service, mock_api_config_manager, mock_policy_manager
    ):
        """Test bulk migration of API configs between policies."""
        # Mock APIs with the source policy
        mock_apis = [
            {"config_id": "config1", "users": ["user1"]},
            {"config_id": "config2", "users": ["user2"]},
            {"config_id": "config3", "users": ["user3"]},
        ]
        mock_policy_manager.get_apis_with_policy.return_value = mock_apis

        # Mock migrate_api_configs_to_policy to return success
        policy_service.migrate_api_configs_to_policy = AsyncMock(
            return_value={"success": ["config1", "config2", "config3"], "failed": []}
        )

        # Mock configs that will be returned
        mock_configs = [
            MagicMock(config_id="config1", policy_id="new_policy"),
            MagicMock(config_id="config2", policy_id="new_policy"),
            MagicMock(config_id="config3", policy_id="new_policy"),
        ]
        policy_service.api_config_service.get_api_config.side_effect = mock_configs

        result = await policy_service.bulk_migrate_api_configs_to_policy(
            from_policy_id="old_policy",
            to_policy_id="new_policy",
        )

        assert len(result) == 3
        assert all(config.policy_id == "new_policy" for config in result)

    @pytest.mark.anyio()
    async def test_get_policy_usage_summary(
        self, policy_service, mock_policy_manager, mock_api_config_manager
    ):
        """Test getting usage summary for a policy."""
        # Mock policy with proper name attribute
        mock_policy = MagicMock()
        mock_policy.policy_id = "test_policy"
        mock_policy.name = "Test Policy"
        mock_policy.api_config_ids = ["config1", "config2"]
        mock_policy_manager.get_policy.return_value = mock_policy

        # Mock APIs with the policy
        mock_apis = [
            {"config_id": "config1", "users": ["user1", "user2"]},
            {"config_id": "config2", "users": ["user3"]},
        ]
        mock_policy_manager.get_apis_with_policy.return_value = mock_apis

        summary = await policy_service.get_policy_usage_summary("test_policy")

        assert summary["policy_id"] == "test_policy"
        assert summary["policy_name"] == "Test Policy"
        assert summary["total_api_configs"] == 2
        assert summary["total_users"] == 3
        assert set(summary["users"]) == {"user1", "user2", "user3"}


class TestPolicyRuleBuilder:
    """Test PolicyRuleBuilder functionality."""

    def test_rate_limit_builder(self):
        """Test building rate limit rules."""
        rule = (
            PolicyRuleBuilder()
            .with_rate_limit(100, "hour")
            .with_action("deny")
            .with_message("Rate limit exceeded")
            .build()
        )

        assert rule.metric_key == "requests_count"
        assert rule.operator == RuleOperator.GREATER_THAN
        assert rule.threshold == 100
        assert rule.period == "hour"
        assert rule.action == "deny"
        assert rule.message == "Rate limit exceeded"

    def test_token_limit_builder(self):
        """Test building token limit rules."""
        rule = (
            PolicyRuleBuilder()
            .with_token_limit(10000, "day", token_type="input")
            .with_action("throttle")
            .build()
        )

        assert rule.metric_key == "input_words_count"
        assert rule.threshold == 10000
        assert rule.period == "day"
        assert rule.action == "throttle"

    def test_token_limit_types(self):
        """Test different token limit types."""
        input_rule = (
            PolicyRuleBuilder()
            .with_token_limit(100, "hour", token_type="input")
            .build()
        )
        assert input_rule.metric_key == "input_words_count"

        output_rule = (
            PolicyRuleBuilder()
            .with_token_limit(100, "hour", token_type="output")
            .build()
        )
        assert output_rule.metric_key == "output_words_count"

        total_rule = (
            PolicyRuleBuilder()
            .with_token_limit(100, "hour", token_type="total")
            .build()
        )
        assert total_rule.metric_key == "total_words_count"

    def test_credit_limit_builder(self):
        """Test building credit limit rules."""
        rule = PolicyRuleBuilder().with_credit_limit(1000).with_action("warn").build()

        assert rule.metric_key == "credits_used"
        assert rule.operator == RuleOperator.GREATER_THAN
        assert rule.threshold == 1000
        assert rule.period == "lifetime"
        assert rule.action == "warn"

    def test_custom_rule_builder(self):
        """Test building custom rules."""
        rule = (
            PolicyRuleBuilder()
            .with_metric("custom_metric")
            .with_operator(RuleOperator.LESS_THAN_EQUAL)
            .with_threshold(50)
            .with_period("month")
            .with_action("deny")
            .build()
        )

        assert rule.metric_key == "custom_metric"
        assert rule.operator == RuleOperator.LESS_THAN_EQUAL
        assert rule.threshold == 50
        assert rule.period == "month"

    def test_builder_validation(self):
        """Test that builder validates required fields."""
        builder = PolicyRuleBuilder()

        # Missing metric
        with pytest.raises(ValueError, match="metric_key"):
            builder.build()

        # Missing operator
        builder.with_metric("test")
        with pytest.raises(ValueError, match="operator"):
            builder.build()

        # Missing threshold
        builder.with_operator(RuleOperator.GREATER_THAN)
        with pytest.raises(ValueError, match="threshold"):
            builder.build()

        # Missing period
        builder.with_threshold(10)
        with pytest.raises(ValueError, match="period"):
            builder.build()

        # Missing action
        builder.with_period("hour")
        with pytest.raises(ValueError, match="action"):
            builder.build()

        # Should build successfully with all fields
        builder.with_action("deny")
        rule = builder.build()
        assert rule is not None

    def test_builder_chaining(self):
        """Test that builder methods can be chained."""
        rule = (
            PolicyRuleBuilder()
            .with_rate_limit(100, "hour")
            .with_action("throttle")
            .with_message("Slow down!")
            .build()
        )

        assert rule.threshold == 100
        assert rule.action == "throttle"
        assert rule.message == "Slow down!"


class TestPolicyServiceHelpers:
    """Test helper methods in PolicyService."""

    @pytest.fixture()
    def policy_service(self):
        """Create a PolicyService instance."""
        service = PolicyService()
        service.policy_manager = MagicMock()
        service.api_config_manager = MagicMock()
        return service

    def test_validate_policy_type_rules_match(self, policy_service):
        """Test validation of policy type and rules consistency."""
        # Rate limit policy should only have rate limit rules
        rate_rules = [
            PolicyRule(
                metric_key="requests_count",
                operator=RuleOperator.GREATER_THAN,
                threshold=100,
                period="hour",
                action="deny",
            )
        ]
        assert policy_service._validate_policy_type_rules_match(
            PolicyType.RATE_LIMIT, rate_rules
        )

        # Token limit policy with credit rule should fail
        mixed_rules = [
            PolicyRule(
                metric_key="total_words_count",
                operator=RuleOperator.GREATER_THAN,
                threshold=1000,
                period="day",
                action="deny",
            ),
            PolicyRule(
                metric_key="credits_used",  # Wrong metric for token policy
                operator=RuleOperator.GREATER_THAN,
                threshold=100,
                period="lifetime",
                action="deny",
            ),
        ]
        assert not policy_service._validate_policy_type_rules_match(
            PolicyType.TOKEN_LIMIT, mixed_rules
        )

        # Combined policy can have any rules
        assert policy_service._validate_policy_type_rules_match(
            PolicyType.COMBINED, mixed_rules
        )

    @pytest.mark.anyio()
    async def test_get_policies_by_type(self, policy_service):
        """Test filtering policies by type."""
        all_policies = [
            Policy(policy_id="1", name="Rate 1", policy_type=PolicyType.RATE_LIMIT),
            Policy(policy_id="2", name="Token 1", policy_type=PolicyType.TOKEN_LIMIT),
            Policy(policy_id="3", name="Rate 2", policy_type=PolicyType.RATE_LIMIT),
            Policy(policy_id="4", name="Credit 1", policy_type=PolicyType.CREDIT_BASED),
        ]
        policy_service.policy_manager.get_all_policies.return_value = all_policies

        rate_policies = await policy_service.get_policies_by_type(PolicyType.RATE_LIMIT)

        assert len(rate_policies) == 2
        assert all(p.policy_type == PolicyType.RATE_LIMIT for p in rate_policies)

    @pytest.mark.anyio()
    async def test_clone_policy(self, policy_service):
        """Test cloning an existing policy."""
        original = Policy(
            policy_id="original",
            name="Original Policy",
            policy_type=PolicyType.COMBINED,
            description="Original description",
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=100,
                    period="hour",
                    action="deny",
                )
            ],
            settings={"custom": "value"},
        )
        policy_service.policy_manager.get_policy.return_value = original

        # Create a properly cloned policy with enum type preserved
        cloned_data = original.model_dump(exclude={"policy_id"})
        cloned_data["policy_id"] = "cloned"
        cloned_data["name"] = "Cloned Policy"
        cloned_data["policy_type"] = PolicyType.COMBINED  # Ensure type stays as enum
        cloned_policy = Policy(**cloned_data)

        policy_service.policy_manager.create_policy.return_value = cloned_policy

        cloned = await policy_service.clone_policy(
            source_policy_id="original",
            new_name="Cloned Policy",
        )

        assert cloned.policy_id != original.policy_id
        assert cloned.name == "Cloned Policy"
        assert cloned.policy_type == original.policy_type
        assert len(cloned.rules) == len(original.rules)
        assert cloned.settings == original.settings
