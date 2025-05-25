"""
Unit tests for PolicyEnforcer class.

Tests policy enforcement logic, caching, metrics calculation,
and various edge cases.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from policies.enforcer import PolicyEnforcer, PolicyMetricsAdapter
from policies.models import (
    Policy,
    PolicyEvaluationResult,
    PolicyRule,
    PolicyType,
    RuleOperator,
)


class TestPolicyEnforcer:
    """Test PolicyEnforcer functionality."""

    @pytest.fixture()
    def mock_policy_manager(self):
        """Create a mock policy manager."""
        return MagicMock()

    @pytest.fixture()
    def mock_usage_tracker(self):
        """Create a mock usage tracker."""
        return MagicMock()

    @pytest.fixture()
    def policy_enforcer(self, mock_policy_manager, mock_usage_tracker):
        """Create a PolicyEnforcer instance with mocks."""
        enforcer = PolicyEnforcer()
        enforcer.policy_manager = mock_policy_manager
        enforcer.usage_tracker = mock_usage_tracker
        return enforcer

    @pytest.mark.anyio()
    async def test_enforce_policy_no_api_config(self, policy_enforcer):
        """Test enforcement when API config doesn't exist."""
        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            result = await policy_enforcer.enforce_policy(
                api_config_id="non_existent",
                user_id="test_user",
                request_context={"path": "/api/test"},
            )

            assert result.allowed is False
            assert len(result.violated_rules) == 1
            assert "not found" in result.violated_rules[0].message.lower()

    @pytest.mark.anyio()
    async def test_enforce_policy_no_policy_id(self, policy_enforcer):
        """Test enforcement when API config has no policy."""
        # Mock API config without policy
        mock_config = MagicMock()
        mock_config.policy_id = None

        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_config
            mock_repo_class.return_value = mock_repo

            result = await policy_enforcer.enforce_policy(
                api_config_id="test_config",
                user_id="test_user",
                request_context={"path": "/api/test"},
            )

            assert result.allowed is True  # No policy means allow
            assert len(result.violated_rules) == 0

    @pytest.mark.anyio()
    async def test_enforce_policy_no_rules(self, policy_enforcer):
        """Test enforcement when policy has no rules."""
        # Mock API config with policy
        mock_config = MagicMock()
        mock_config.policy_id = "test_policy"

        # Mock policy with no rules
        mock_policy = Policy(
            policy_id="test_policy",
            name="Empty Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=[],
        )
        policy_enforcer.policy_manager.get_policy.return_value = mock_policy

        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_config
            mock_repo_class.return_value = mock_repo

            result = await policy_enforcer.enforce_policy(
                api_config_id="test_config",
                user_id="test_user",
                request_context={"path": "/api/test"},
            )

            assert result.allowed is True
            assert len(result.violated_rules) == 0

    @pytest.mark.anyio()
    async def test_enforce_policy_with_cache(self, policy_enforcer):
        """Test that results are cached properly."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.policy_id = "test_policy"

        mock_policy = Policy(
            policy_id="test_policy",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=10,
                    period="hour",
                    action="deny",
                )
            ],
        )
        policy_enforcer.policy_manager.get_policy.return_value = mock_policy

        # Patch APIConfigRepository and metrics
        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_config
            mock_repo_class.return_value = mock_repo

            # Mock metrics
            mock_metrics = {"requests_count": 5}
            with patch.object(
                policy_enforcer.metrics_adapter,
                "get_metrics_for_evaluation",
                return_value=mock_metrics,
            ):
                # First call - should calculate
                result1 = await policy_enforcer.enforce_policy(
                    api_config_id="test_config",
                    user_id="test_user",
                    request_context={"path": "/api/test"},
                )

                # Verify cache was populated
                cache_key = "test_config:test_user:test_policy"
                assert cache_key in policy_enforcer._evaluation_cache

                # Second call - should use cache
                result2 = await policy_enforcer.enforce_policy(
                    api_config_id="test_config",
                    user_id="test_user",
                    request_context={"path": "/api/test"},
                )

                # Results should be the same
                assert result1.allowed == result2.allowed
                assert result1.allowed is True  # 5 < 10, so allowed

    @pytest.mark.anyio()
    async def test_enforce_policy_cache_expiration(self, policy_enforcer):
        """Test that cache entries expire after TTL."""
        # Clear cache first
        policy_enforcer._evaluation_cache.clear()

        # Add a cache entry with expired timestamp
        cache_key = "test_config:test_user:test_policy"
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=65)  # > 60s TTL
        policy_enforcer._evaluation_cache[cache_key] = (
            PolicyEvaluationResult(allowed=True),
            expired_time,
        )

        # Setup mocks for fresh evaluation
        mock_config = MagicMock()
        mock_config.policy_id = "test_policy"

        mock_policy = Policy(
            policy_id="test_policy",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=[],
        )
        policy_enforcer.policy_manager.get_policy.return_value = mock_policy

        # Patch APIConfigRepository
        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_config
            mock_repo_class.return_value = mock_repo

            # Should not use expired cache
            await policy_enforcer.enforce_policy(
                api_config_id="test_config",
                user_id="test_user",
                request_context={"path": "/api/test"},
            )

            # Cache should be updated with new timestamp
            assert policy_enforcer._evaluation_cache[cache_key][1] > expired_time

    @pytest.mark.anyio()
    async def test_evaluate_rule_operators(self, policy_enforcer):
        """Test all operator evaluations."""
        test_cases = [
            (RuleOperator.GREATER_THAN, 10, 5, True),  # 10 > 5
            (RuleOperator.GREATER_THAN, 5, 10, False),  # 5 > 10
            (RuleOperator.GREATER_THAN_EQUAL, 10, 10, True),  # 10 >= 10
            (RuleOperator.GREATER_THAN_EQUAL, 9, 10, False),  # 9 >= 10
            (RuleOperator.LESS_THAN, 5, 10, True),  # 5 < 10
            (RuleOperator.LESS_THAN, 10, 5, False),  # 10 < 5
            (RuleOperator.LESS_THAN_EQUAL, 10, 10, True),  # 10 <= 10
            (RuleOperator.LESS_THAN_EQUAL, 11, 10, False),  # 11 <= 10
            (RuleOperator.EQUAL, 10, 10, True),  # 10 == 10
            (RuleOperator.EQUAL, 10, 11, False),  # 10 == 11
            (RuleOperator.NOT_EQUAL, 10, 11, True),  # 10 != 11
            (RuleOperator.NOT_EQUAL, 10, 10, False),  # 10 != 10
        ]

        for operator, metric_value, threshold, expected_violated in test_cases:
            rule = PolicyRule(
                metric_key="test_metric",
                operator=operator,
                threshold=threshold,
                period="hour",
                action="deny",
            )

            violated = policy_enforcer._evaluate_rule(rule, metric_value)

            assert (
                violated == expected_violated
            ), f"Failed for {operator}: {metric_value} vs {threshold}"

    @pytest.mark.anyio()
    async def test_evaluate_missing_metric(self, policy_enforcer):
        """Test rule evaluation when metric is missing."""
        rule = PolicyRule(
            metric_key="missing_metric",
            operator=RuleOperator.GREATER_THAN,
            threshold=10,
            period="hour",
            action="deny",
        )

        # Missing metric defaults to 0
        violated = policy_enforcer._evaluate_rule(rule, 0)

        # Missing metric should be treated as 0
        assert violated is False  # 0 > 10 is False

    @pytest.mark.anyio()
    async def test_policy_result_aggregation(self, policy_enforcer):
        """Test how multiple rule violations are aggregated."""
        # Setup policy with multiple rules
        mock_config = MagicMock()
        mock_config.policy_id = "test_policy"

        mock_policy = Policy(
            policy_id="test_policy",
            name="Multi-Rule Policy",
            policy_type=PolicyType.COMBINED,
            rules=[
                PolicyRule(
                    metric_key="requests_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=5,
                    period="hour",
                    action="warn",
                    message="High request rate",
                ),
                PolicyRule(
                    metric_key="total_words_count",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=1000,
                    period="day",
                    action="throttle",
                    message="High token usage",
                ),
                PolicyRule(
                    metric_key="credits_used",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=100,
                    period="lifetime",
                    action="deny",
                    message="Credit limit exceeded",
                ),
            ],
        )
        policy_enforcer.policy_manager.get_policy.return_value = mock_policy

        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_config
            mock_repo_class.return_value = mock_repo

            # Mock metrics that violate all rules
            mock_metrics = {
                "requests_count": 10,  # Violates warn rule
                "total_words_count": 2000,  # Violates throttle rule
                "credits_used": 150,  # Violates deny rule
            }

            with patch.object(
                policy_enforcer.metrics_adapter,
                "get_metrics_for_evaluation",
                return_value=mock_metrics,
            ):
                result = await policy_enforcer.enforce_policy(
                    api_config_id="test_config",
                    user_id="test_user",
                    request_context={"path": "/api/test"},
                )

            # Should be denied (deny rule takes precedence)
            assert result.allowed is False
            assert len(result.violated_rules) == 1  # Only deny rule
            assert result.violated_rules[0].action == "deny"

            # Should have warnings for other violations
            assert len(result.warnings) == 2
            assert any(w.action == "warn" for w in result.warnings)
            assert any(w.action == "throttle" for w in result.warnings)

            # Should have throttle delay
            assert result.throttle_delay > 0

    @pytest.mark.anyio()
    async def test_concurrent_enforcement(self, policy_enforcer):
        """Test concurrent policy enforcement requests."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.policy_id = "test_policy"

        mock_policy = Policy(
            policy_id="test_policy",
            name="Test Policy",
            policy_type=PolicyType.RATE_LIMIT,
            rules=[],
        )
        policy_enforcer.policy_manager.get_policy.return_value = mock_policy

        with patch("api_configs.repository.APIConfigRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_config
            mock_repo_class.return_value = mock_repo

            # Make concurrent requests
            tasks = [
                policy_enforcer.enforce_policy(
                    api_config_id="test_config",
                    user_id=f"user_{i}",
                    request_context={"path": "/api/test"},
                )
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r.allowed for r in results)
            assert len(results) == 10


class TestPolicyMetricsAdapter:
    """Test PolicyMetricsAdapter functionality."""

    @pytest.fixture()
    def mock_usage_tracker(self):
        """Create a mock usage tracker."""
        return MagicMock()

    @pytest.fixture()
    def metrics_adapter(self, mock_usage_tracker):
        """Create a PolicyMetricsAdapter instance."""
        return PolicyMetricsAdapter(mock_usage_tracker)

    def test_get_usage_metrics_empty(self, metrics_adapter, mock_usage_tracker):
        """Test metrics calculation with no usage logs."""
        mock_usage_tracker.get_usage_logs_for_period.return_value = []

        metrics = metrics_adapter.get_usage_metrics(
            api_config_id="test_config",
            user_id="test_user",
            time_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        assert metrics["requests_count"] == 0
        assert metrics["input_words_count"] == 0
        assert metrics["output_words_count"] == 0
        assert metrics["total_words_count"] == 0
        assert metrics["credits_used"] == 0

    def test_get_usage_metrics_with_logs(self, metrics_adapter, mock_usage_tracker):
        """Test metrics calculation with usage logs."""
        mock_logs = [
            {
                "user_id": "test_user",
                "input_word_count": 10,
                "output_word_count": 20,
            },
            {
                "user_id": "test_user",
                "input_word_count": 15,
                "output_word_count": 25,
            },
            {
                "user_id": "other_user",  # Different user
                "input_word_count": 100,
                "output_word_count": 200,
            },
        ]
        mock_usage_tracker.get_usage_logs_for_period.return_value = mock_logs

        metrics = metrics_adapter.get_usage_metrics(
            api_config_id="test_config",
            user_id="test_user",
            time_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        # Should only count logs for test_user
        assert metrics["requests_count"] == 2
        assert metrics["input_words_count"] == 25  # 10 + 15
        assert metrics["output_words_count"] == 45  # 20 + 25
        assert metrics["total_words_count"] == 70  # (10+20) + (15+25)
        assert metrics["credits_used"] == 2.7  # 2 requests + 70/100 words

    def test_get_usage_metrics_all_users(self, metrics_adapter, mock_usage_tracker):
        """Test metrics calculation for all users."""
        mock_logs = [
            {
                "user_id": "user1",
                "input_word_count": 10,
                "output_word_count": 10,
            },
            {
                "user_id": "user2",
                "input_word_count": 20,
                "output_word_count": 20,
            },
        ]
        mock_usage_tracker.get_usage_logs_for_period.return_value = mock_logs

        metrics = metrics_adapter.get_usage_metrics(
            api_config_id="test_config",
            user_id=None,  # None means all users
            time_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        # Should count all logs
        assert metrics["requests_count"] == 2
        assert metrics["total_words_count"] == 60  # (10+10) + (20+20)

    def test_credit_calculation_formula(self, metrics_adapter, mock_usage_tracker):
        """Test the credit calculation formula."""
        test_cases = [
            (1, 0, 1.0),  # 1 + 0/100
            (5, 100, 6.0),  # 5 + 100/100
            (10, 250, 12.5),  # 10 + 250/100
            (0, 0, 0.0),  # 0 + 0/100 (no requests means no words)
            (100, 5000, 150.0),  # 100 + 5000/100
        ]

        for requests, total_words, expected_credits in test_cases:
            if requests > 0:
                # Create logs with words distributed across requests
                words_per_request = total_words / requests
                mock_logs = [
                    {
                        "user_id": "test_user",
                        "input_word_count": words_per_request / 2,
                        "output_word_count": words_per_request / 2,
                    }
                    for _ in range(requests)
                ]
            else:
                # Special case for 0 requests - should return empty logs
                mock_logs = []
            mock_usage_tracker.get_usage_logs_for_period.return_value = mock_logs

            metrics = metrics_adapter.get_usage_metrics(
                api_config_id="test_config",
                user_id="test_user",
                time_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            )

            assert (
                abs(metrics["credits_used"] - expected_credits) < 0.01
            ), f"Failed for {requests} requests, {total_words} words"

    def test_missing_word_counts(self, metrics_adapter, mock_usage_tracker):
        """Test handling of logs with missing word count fields."""
        mock_logs = [
            {"user_id": "test_user"},  # Missing all word counts
            {
                "user_id": "test_user",
                "input_word_count": 10,
                # Missing output_word_count
            },
            {
                "user_id": "test_user",
                "input_word_count": 5,
                "output_word_count": 5,
            },
        ]
        mock_usage_tracker.get_usage_logs_for_period.return_value = mock_logs

        metrics = metrics_adapter.get_usage_metrics(
            api_config_id="test_config",
            user_id="test_user",
            time_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        # Should handle missing fields gracefully
        assert metrics["requests_count"] == 3
        assert metrics["input_words_count"] == 15  # 0 + 10 + 5
        assert metrics["output_words_count"] == 5  # 0 + 0 + 5
        assert metrics["total_words_count"] == 20  # 0 + (10+0) + (5+5)


class TestPolicyResultSerialization:
    """Test PolicyEvaluationResult serialization and representation."""

    def test_policy_result_to_dict(self):
        """Test PolicyEvaluationResult conversion to dictionary."""
        rule1 = PolicyRule(
            metric_key="requests_count",
            operator=RuleOperator.GREATER_THAN,
            threshold=10,
            period="hour",
            action="deny",
            message="Too many requests",
        )

        rule2 = PolicyRule(
            metric_key="credits_used",
            operator=RuleOperator.GREATER_THAN,
            threshold=100,
            period="lifetime",
            action="warn",
            message="High credit usage",
        )

        result = PolicyEvaluationResult(
            allowed=False,
            violated_rules=[rule1],
            warnings=[rule2],
            remaining_quota={"requests": 5, "credits": 20},
            throttle_delay=2.5,
        )

        result_dict = result.to_dict()

        assert result_dict["allowed"] is False
        assert len(result_dict["violated_rules"]) == 1
        assert result_dict["violated_rules"][0]["message"] == "Too many requests"
        assert len(result_dict["warnings"]) == 1
        assert result_dict["warnings"][0]["message"] == "High credit usage"
        assert result_dict["remaining_quota"]["requests"] == 5
        assert result_dict["throttle_delay"] == 2.5

    def test_policy_result_headers(self):
        """Test PolicyEvaluationResult header generation."""
        result = PolicyEvaluationResult(
            allowed=True,
            warnings=[
                PolicyRule(
                    metric_key="credits_used",
                    operator=RuleOperator.GREATER_THAN,
                    threshold=80,
                    period="lifetime",
                    action="warn",
                    message="80% credits used",
                )
            ],
            remaining_quota={"credits": 20, "requests": 50},
            throttle_delay=0,
        )

        headers = result.get_policy_headers()

        assert headers["X-Policy-Allowed"] == "true"
        assert "80% credits used" in headers["X-Policy-Warnings"]
        assert headers["X-Policy-Remaining-Credits"] == "20"
        assert headers["X-Policy-Remaining-Requests"] == "50"
        assert "X-Policy-Throttle-Delay" not in headers  # 0 delay not included

    def test_policy_result_headers_with_throttle(self):
        """Test PolicyEvaluationResult header generation with throttle."""
        result = PolicyEvaluationResult(allowed=True, throttle_delay=5.0)

        headers = result.get_policy_headers()

        assert headers["X-Policy-Throttle-Delay"] == "5.0"
