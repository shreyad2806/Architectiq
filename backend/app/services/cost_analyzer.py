"""CostAnalyzer service for estimating AI architecture costs.

Provides deterministic, isolated token and cost calculations for a given
production AI architecture review request.
"""

from __future__ import annotations

from app.schemas import ReviewRequest


# Cost per 1_000_000 tokens. Prices are approximate.
PRICING_TABLE: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input_per_1m": 2.50,
        "output_per_1m": 10.00,
    },
    "gpt-4o-mini": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
    },
    "claude-sonnet": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
    },
    "gemini-2.5-pro": {
        "input_per_1m": 1.25,
        "output_per_1m": 10.00,
    },
    "llama3": {
        "input_per_1m": 0.00,
        "output_per_1m": 0.00,
    },
}

# Cheaper baseline used to estimate potential savings.
SAVINGS_BASELINE_MODEL = "gpt-4o-mini"


def _get_model_pricing(model: str) -> dict[str, float]:
    """Return pricing for a supported model, falling back to gpt-4o."""
    normalized = model.lower().strip()
    return PRICING_TABLE.get(normalized, PRICING_TABLE["gpt-4o"])


class CostAnalyzer:
    """Analyze costs for a production AI architecture review request."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return estimated monthly tokens, cost, and potential savings.

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with ``estimated_monthly_tokens``,
            ``estimated_monthly_cost``, and ``potential_monthly_savings``.
        """
        monthly_requests = request.monthly_requests
        prompt_tokens = request.average_prompt_tokens
        completion_tokens = request.average_completion_tokens

        estimated_monthly_tokens = monthly_requests * (prompt_tokens + completion_tokens)

        total_input_tokens = monthly_requests * prompt_tokens
        total_output_tokens = monthly_requests * completion_tokens

        pricing = _get_model_pricing(request.llm)
        baseline_pricing = _get_model_pricing(SAVINGS_BASELINE_MODEL)

        estimated_monthly_cost = self._calculate_cost(
            total_input_tokens, total_output_tokens, pricing
        )
        baseline_cost = self._calculate_cost(
            total_input_tokens, total_output_tokens, baseline_pricing
        )

        potential_monthly_savings = round(
            max(estimated_monthly_cost - baseline_cost, 0.0), 2
        )

        return {
            "estimated_monthly_tokens": int(estimated_monthly_tokens),
            "estimated_monthly_cost": round(estimated_monthly_cost, 2),
            "potential_monthly_savings": potential_monthly_savings,
        }

    @staticmethod
    def _calculate_cost(
        input_tokens: int, output_tokens: int, pricing: dict[str, float]
    ) -> float:
        """Calculate cost from token counts and per-1M pricing."""
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
        return input_cost + output_cost
