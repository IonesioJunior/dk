"""PolicyRuleBuilder test helper methods."""

from policies.models import PolicyRule, PolicyRuleBuilder, RuleOperator


class PolicyRuleBuilderMethods:
    """Helper methods for PolicyRuleBuilder tests."""

    @staticmethod
    def rate_limit(threshold: int) -> PolicyRule:
        """Create a rate limit rule."""
        return PolicyRule(
            metric_key="requests_per_hour",
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=threshold,
            period="hour",
            action="deny",
            message=f"Rate limit exceeded: {threshold} requests per hour allowed",
        )

    @staticmethod
    def token_limit(threshold: int) -> PolicyRule:
        """Create a token limit rule."""
        return PolicyRule(
            metric_key="total_tokens_per_day",
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=threshold,
            period="day",
            action="deny",
            message=f"Token limit exceeded: {threshold} tokens per day allowed",
        )

    @staticmethod
    def credit_limit(threshold: float) -> PolicyRule:
        """Create a credit limit rule."""
        return PolicyRule(
            metric_key="credits_used",
            operator=RuleOperator.LESS_THAN_EQUAL,
            threshold=threshold,
            period="lifetime",
            action="deny",
            message=f"Credit limit exceeded: {threshold} credits allowed",
        )

    @staticmethod
    def custom_rule(
        metric_key: str,
        operator: RuleOperator,
        threshold: float,
        period: str,
        action: str,
        message: str,
    ) -> PolicyRule:
        """Create a custom rule."""
        return PolicyRule(
            metric_key=metric_key,
            operator=operator,
            threshold=threshold,
            period=period,
            action=action,
            message=message,
        )


# Attach methods to PolicyRuleBuilder for tests
PolicyRuleBuilder.rate_limit = staticmethod(PolicyRuleBuilderMethods.rate_limit)
PolicyRuleBuilder.token_limit = staticmethod(PolicyRuleBuilderMethods.token_limit)
PolicyRuleBuilder.credit_limit = staticmethod(PolicyRuleBuilderMethods.credit_limit)
PolicyRuleBuilder.custom_rule = staticmethod(PolicyRuleBuilderMethods.custom_rule)
