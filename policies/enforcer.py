"""Policy enforcement engine."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from api_configs.usage_tracker import APIConfigUsageTracker

from .manager import PolicyManager
from .models import PolicyEvaluationResult, PolicyRule, RuleOperator

logger = logging.getLogger(__name__)


@dataclass
class MetricsRequest:
    """Parameters for metrics retrieval."""

    api_config_id: str
    user_id: str
    time_range: tuple[datetime, datetime]
    metric_key: str


class PolicyMetricsAdapter:
    """Adapts raw usage metrics for policy evaluation."""

    def __init__(self, usage_tracker: APIConfigUsageTracker) -> None:
        self.usage_tracker = usage_tracker

    def get_usage_metrics(
        self, api_config_id: str, user_id: Optional[str], time_window_start: datetime
    ) -> dict[str, float]:
        """Get usage metrics for a specific time window."""
        # Get logs for the time window
        logs = self.usage_tracker.get_usage_logs_for_period(
            api_config_id, time_window_start, datetime.now(timezone.utc), user_id
        )

        # Calculate metrics - handle both dict and object formats
        if logs and hasattr(logs[0], "input_word_count"):
            # APIConfigUsageLog objects (already filtered by user_id in the query)
            metrics = {
                "requests_count": len(logs),
                "input_words_count": sum(log.input_word_count for log in logs),
                "output_words_count": sum(log.output_word_count for log in logs),
                "total_words_count": sum(
                    log.input_word_count + log.output_word_count for log in logs
                ),
            }
        else:
            # Dictionary format (for tests) - need to filter by user
            if user_id:
                logs = [log for log in logs if log.get("user_id") == user_id]

            metrics = {
                "requests_count": len(logs),
                "input_words_count": sum(
                    log.get("input_word_count", 0) for log in logs
                ),
                "output_words_count": sum(
                    log.get("output_word_count", 0) for log in logs
                ),
                "total_words_count": sum(
                    log.get("input_word_count", 0) + log.get("output_word_count", 0)
                    for log in logs
                ),
            }

        # Calculate credits: requests + (total_words / 100)
        metrics["credits_used"] = metrics["requests_count"] + (
            metrics["total_words_count"] / 100
        )

        return metrics

    async def get_metrics_for_evaluation(
        self, api_config_id: str, user_id: str, policy_rules: list[PolicyRule]
    ) -> dict[str, float]:
        """Extract relevant metrics based on policy rules."""
        metrics = {}
        current_time = datetime.now(timezone.utc)

        for rule in policy_rules:
            try:
                if rule.period == "hour":
                    # Get hourly metrics
                    start_time = current_time - timedelta(hours=1)
                    metrics[rule.metric_key] = await self._get_period_metrics(
                        MetricsRequest(
                            api_config_id=api_config_id,
                            user_id=user_id,
                            time_range=(start_time, current_time),
                            metric_key=rule.metric_key,
                        )
                    )

                elif rule.period == "day":
                    # Get daily metrics
                    start_time = current_time - timedelta(days=1)
                    metrics[rule.metric_key] = await self._get_period_metrics(
                        MetricsRequest(
                            api_config_id=api_config_id,
                            user_id=user_id,
                            time_range=(start_time, current_time),
                            metric_key=rule.metric_key,
                        )
                    )

                elif rule.period == "month":
                    # Get monthly metrics (30 days)
                    start_time = current_time - timedelta(days=30)
                    metrics[rule.metric_key] = await self._get_period_metrics(
                        MetricsRequest(
                            api_config_id=api_config_id,
                            user_id=user_id,
                            time_range=(start_time, current_time),
                            metric_key=rule.metric_key,
                        )
                    )

                elif rule.period == "lifetime" or not rule.period:
                    # Get all-time metrics
                    metrics[rule.metric_key] = await self._get_lifetime_metrics(
                        api_config_id, user_id, rule.metric_key
                    )

            except Exception as e:
                logger.error(f"Error getting metrics for {rule.metric_key}: {e}")
                metrics[rule.metric_key] = 0

        return metrics

    async def _get_period_metrics(self, request: MetricsRequest) -> float:
        """Get metrics for a specific period."""
        # Get usage logs for the period
        start_time, end_time = request.time_range
        usage_logs = self.usage_tracker.get_usage_logs_for_period(
            request.api_config_id, start_time, end_time, request.user_id
        )

        # Calculate aggregated values
        total_words = sum(
            log.input_word_count + log.output_word_count for log in usage_logs
        )
        input_words = sum(log.input_word_count for log in usage_logs)
        output_words = sum(log.output_word_count for log in usage_logs)
        request_count = len(usage_logs)

        # Define metric calculations
        metric_calculations = {
            "requests_per_hour": request_count,
            "requests_per_day": request_count,
            "requests_count": request_count,
            "total_tokens": total_words,
            "total_words_count": total_words,
            "input_tokens": input_words,
            "input_words_count": input_words,
            "output_tokens": output_words,
            "output_words_count": output_words,
            "credits_used": request_count + (total_words / 100),
        }

        return metric_calculations.get(request.metric_key, 0)

    async def _get_lifetime_metrics(
        self, api_config_id: str, user_id: str, metric_key: str
    ) -> float:
        """Get all-time metrics."""
        # Get aggregated metrics
        metrics = self.usage_tracker.get_metrics(api_config_id)
        if not metrics:
            return 0

        # Get user-specific data
        user_count = metrics.user_frequency.get(user_id, 0)
        if metrics.total_requests == 0:
            return 0

        # Calculate averages
        avg_total_tokens = (
            metrics.total_input_word_count + metrics.total_output_word_count
        ) / metrics.total_requests
        avg_input_tokens = metrics.total_input_word_count / metrics.total_requests
        avg_output_tokens = metrics.total_output_word_count / metrics.total_requests

        # Define metric calculations
        metric_calculations = {
            "total_requests": user_count,
            "requests_count": user_count,
            "credits_used": user_count + (avg_total_tokens * user_count / 100),
            "total_tokens": avg_total_tokens * user_count,
            "total_words_count": avg_total_tokens * user_count,
            "input_tokens": avg_input_tokens * user_count,
            "input_words_count": avg_input_tokens * user_count,
            "output_tokens": avg_output_tokens * user_count,
            "output_words_count": avg_output_tokens * user_count,
        }

        return metric_calculations.get(metric_key, 0)


class PolicyEnforcer:
    """Core policy enforcement engine."""

    # Constants
    _CACHE_MAX_SIZE = 1000
    _THROTTLE_RATIO_THRESHOLD = 0.9

    def __init__(self) -> None:
        """Initialize the enforcer."""
        self.policy_manager = PolicyManager()
        self.usage_tracker = APIConfigUsageTracker()
        self.metrics_adapter = PolicyMetricsAdapter(self.usage_tracker)
        self._evaluation_cache: dict[str, tuple[PolicyEvaluationResult, datetime]] = {}
        self._cache_ttl = 60  # 1 minute cache
        self.api_config_repository = None  # Will be injected or use default

    def _validate_api_config(
        self, api_config_id: str
    ) -> tuple[Any, Optional[PolicyEvaluationResult]]:
        """Validate API configuration and return it with error result if invalid."""
        if self.api_config_repository is None:
            from api_configs.repository import APIConfigRepository

            self.api_config_repository = APIConfigRepository()

        api_config = self.api_config_repository.get_by_id(api_config_id)
        if not api_config:
            return None, PolicyEvaluationResult(
                allowed=False,
                violated_rules=[
                    PolicyRule(
                        metric_key="api_config",
                        operator=RuleOperator.EQUAL,
                        threshold=0,
                        action="deny",
                        message="API configuration not found",
                    )
                ],
            )
        return api_config, None

    def _validate_policy(
        self, policy_id: str
    ) -> tuple[Any, Optional[PolicyEvaluationResult]]:
        """Validate policy and return it with error result if invalid."""
        policy = self.policy_manager.get_policy(policy_id)
        if not policy:
            return None, PolicyEvaluationResult(
                allowed=False,
                violated_rules=[
                    PolicyRule(
                        metric_key="policy",
                        operator=RuleOperator.EQUAL,
                        threshold=0,
                        action="deny",
                        message=f"Policy {policy_id} not found",
                    )
                ],
            )
        return policy, None

    def _handle_rule_action(
        self,
        result: PolicyEvaluationResult,
        rule: PolicyRule,
        metric_value: float,
    ) -> None:
        """Handle a specific rule action."""
        action_handlers = {
            "deny": lambda: self._handle_deny_action(result, rule),
            "warn": lambda: self._handle_warn_action(result, rule),
            "throttle": lambda: self._handle_throttle_action(
                result, rule, metric_value
            ),
            "triage": lambda: self._handle_triage_action(result, rule),
        }

        handler = action_handlers.get(rule.action)
        if handler:
            handler()

    def _handle_deny_action(
        self, result: PolicyEvaluationResult, rule: PolicyRule
    ) -> None:
        """Handle deny action."""
        result.allowed = False
        result.violated_rules.append(rule)

    def _handle_warn_action(
        self, result: PolicyEvaluationResult, rule: PolicyRule
    ) -> None:
        """Handle warn action."""
        result.warnings.append(rule)

    def _handle_throttle_action(
        self, result: PolicyEvaluationResult, rule: PolicyRule, metric_value: float
    ) -> None:
        """Handle throttle action."""
        result.throttle_delay = self._calculate_throttle_delay(rule, metric_value)
        result.warnings.append(rule)

    def _handle_triage_action(
        self, result: PolicyEvaluationResult, rule: PolicyRule
    ) -> None:
        """Handle triage action - mark response for manual review."""
        result.allowed = False  # Block immediate response
        result.metadata["requires_triage"] = True
        result.metadata["triage_rule_id"] = rule.rule_id
        result.metadata["triage_message"] = (
            rule.message or "Response requires manual review"
        )
        # Add to violated rules so we can track which rule triggered triage
        result.violated_rules.append(rule)

    async def _evaluate_policy_rules(
        self,
        api_config_id: str,
        user_id: str,
        policy: Any,
    ) -> PolicyEvaluationResult:
        """Evaluate policy rules and return result."""
        # Get current metrics
        metrics = await self.metrics_adapter.get_metrics_for_evaluation(
            api_config_id, user_id, policy.rules
        )

        # Evaluate each rule
        result = PolicyEvaluationResult(allowed=True)
        for rule in policy.rules:
            metric_value = metrics.get(rule.metric_key, 0)
            if self._evaluate_rule(rule, metric_value):
                self._handle_rule_action(result, rule, metric_value)

        # Calculate remaining quotas
        result.remaining_quota = self._calculate_remaining_quotas(policy.rules, metrics)
        return result

    async def enforce_policy(
        self,
        api_config_id: str,
        user_id: str,
        request_context: Optional[dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        """Main enforcement method called before API usage."""
        # Quick bypass checks
        if request_context and request_context.get("is_local_user"):
            return PolicyEvaluationResult(allowed=True)

        # Validate API config
        api_config, error_result = self._validate_api_config(api_config_id)
        if error_result:
            return error_result

        # Check if policy enforcement is needed
        if not api_config.policy_id:
            return PolicyEvaluationResult(allowed=True)

        policy, error_result = self._validate_policy(api_config.policy_id)
        if error_result:
            return error_result

        if not policy.is_active:
            return PolicyEvaluationResult(allowed=True)

        # Process policy evaluation
        return await self._process_policy_evaluation(
            api_config_id, user_id, policy, request_context
        )

    async def _process_policy_evaluation(
        self,
        api_config_id: str,
        user_id: str,
        policy: Any,
        request_context: Optional[dict[str, Any]],
    ) -> PolicyEvaluationResult:
        """Process policy evaluation with caching."""
        cache_key = f"{api_config_id}:{user_id}:{policy.policy_id}"

        # Check cache
        cached_result = self._get_cached_result(cache_key, request_context)
        if cached_result:
            return cached_result

        # Evaluate policy rules
        result = await self._evaluate_policy_rules(api_config_id, user_id, policy)

        # Cache and cleanup
        self._evaluation_cache[cache_key] = (result, datetime.now(timezone.utc))
        if len(self._evaluation_cache) > self._CACHE_MAX_SIZE:
            self._clean_cache()

        return result

    def _get_cached_result(
        self, cache_key: str, request_context: Optional[dict[str, Any]]
    ) -> Optional[PolicyEvaluationResult]:
        """Get cached result if valid."""
        if cache_key not in self._evaluation_cache:
            return None

        cached_result, cached_time = self._evaluation_cache[cache_key]
        time_diff = (datetime.now(timezone.utc) - cached_time).total_seconds()
        bypass_cache = request_context and request_context.get("bypass_cache", False)
        if time_diff < self._cache_ttl and not bypass_cache:
            return cached_result
        return None

    def _evaluate_rule(self, rule: PolicyRule, metric_value: float) -> bool:
        """Evaluate a single rule against a metric value."""
        operators = {
            RuleOperator.LESS_THAN: lambda a, b: a < b,
            RuleOperator.LESS_THAN_EQUAL: lambda a, b: a <= b,
            RuleOperator.GREATER_THAN: lambda a, b: a > b,
            RuleOperator.GREATER_THAN_EQUAL: lambda a, b: a >= b,
            RuleOperator.EQUAL: lambda a, b: a == b,
            RuleOperator.NOT_EQUAL: lambda a, b: a != b,
        }

        operator_func = operators.get(rule.operator)
        if operator_func:
            return operator_func(metric_value, rule.threshold)
        return True

    def _calculate_throttle_delay(self, rule: PolicyRule, metric_value: float) -> float:
        """Calculate throttle delay based on how close to limit."""
        if rule.threshold > 0:
            ratio = metric_value / rule.threshold
            if ratio > self._THROTTLE_RATIO_THRESHOLD:
                # Exponential backoff as approaching limit
                return min(
                    (ratio - self._THROTTLE_RATIO_THRESHOLD) * 10, 5.0
                )  # Max 5 second delay
        return 0

    def _calculate_remaining_quotas(
        self, rules: list[PolicyRule], metrics: dict[str, float]
    ) -> dict[str, float]:
        """Calculate remaining quotas for each rule."""
        remaining = {}

        for rule in rules:
            if rule.operator in [RuleOperator.LESS_THAN, RuleOperator.LESS_THAN_EQUAL]:
                metric_value = metrics.get(rule.metric_key, 0)
                remaining[rule.metric_key] = max(0, rule.threshold - metric_value)

        return remaining

    def _clean_cache(self) -> None:
        """Clean expired cache entries."""
        current_time = datetime.now(timezone.utc)
        expired_keys = []

        for key, (_, cached_time) in self._evaluation_cache.items():
            if (current_time - cached_time).total_seconds() > self._cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._evaluation_cache[key]

    async def evaluate_policy_for_user(
        self, user_id: str
    ) -> Optional[PolicyEvaluationResult]:
        """Evaluate policy for a user based on their API configuration."""
        # Get the user's API config
        api_config_id = self.policy_manager.api_config_manager.get_policy_for_user(
            user_id
        )
        if not api_config_id:
            return None

        return await self.enforce_policy(api_config_id, user_id)

    def clear_cache_for_user(self, user_id: str) -> None:
        """Clear cache entries for a specific user."""
        keys_to_remove = [k for k in self._evaluation_cache if f":{user_id}:" in k]
        for key in keys_to_remove:
            del self._evaluation_cache[key]

    def clear_cache_for_api(self, api_config_id: str) -> None:
        """Clear cache entries for a specific API configuration."""
        keys_to_remove = [
            k for k in self._evaluation_cache if k.startswith(f"{api_config_id}:")
        ]
        for key in keys_to_remove:
            del self._evaluation_cache[key]
