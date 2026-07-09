"""Cost, token, and latency estimation helpers for AI architectures.

Pricing and performance constants are configurable at the top of the file.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Configurable constants
# ---------------------------------------------------------------------------

# Cost per 1,000,000 tokens. Prices are approximate and should be updated as
# providers change their pricing.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input_per_1m": 2.50,
        "output_per_1m": 10.00,
        "ttft_ms": 200.0,
        "output_tokens_per_second": 80.0,
    },
    "gpt-4.1": {
        "input_per_1m": 2.00,
        "output_per_1m": 8.00,
        "ttft_ms": 220.0,
        "output_tokens_per_second": 90.0,
    },
    "claude-sonnet": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
        "ttft_ms": 300.0,
        "output_tokens_per_second": 60.0,
    },
    "claude-sonnet-4": {
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
        "ttft_ms": 280.0,
        "output_tokens_per_second": 65.0,
    },
    "gemini-2.5-pro": {
        "input_per_1m": 1.25,
        "output_per_1m": 10.00,
        "ttft_ms": 250.0,
        "output_tokens_per_second": 70.0,
    },
}

# Suggested cheaper alternatives used when a specific model is not requested.
SAVINGS_ALTERNATIVES: dict[str, str] = {
    "gpt-4o": "gpt-4.1",
    "gpt-4.1": "gpt-4.1",
    "claude-sonnet": "gemini-2.5-pro",
    "claude-sonnet-4": "gemini-2.5-pro",
    "gemini-2.5-pro": "gemini-2.5-pro",
}

DEFAULT_NETWORK_OVERHEAD_MS = 150.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_model(model: str) -> dict[str, float]:
    """Return pricing and latency constants for a supported model.

    Raises:
        ValueError: If the model is not in the pricing table.
    """
    normalized = model.lower().strip()
    if normalized not in MODEL_PRICING:
        supported = ", ".join(MODEL_PRICING.keys())
        raise ValueError(f"Unsupported model '{model}'. Supported models: {supported}")
    return MODEL_PRICING[normalized]


def _normalize_model_name(model: str) -> str:
    """Return the canonical key for a model name."""
    return model.lower().strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_monthly_tokens(
    requests_per_month: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> dict[str, int]:
    """Estimate total monthly token usage.

    Args:
        requests_per_month: Expected number of requests per month.
        avg_input_tokens: Average input tokens per request.
        avg_output_tokens: Average output tokens per request.

    Returns:
        Dictionary with ``input_tokens``, ``output_tokens``, and ``total_tokens``.
    """
    input_tokens = requests_per_month * avg_input_tokens
    output_tokens = requests_per_month * avg_output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def estimate_monthly_cost(
    model: str,
    requests_per_month: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> float:
    """Estimate monthly cost for a given model and workload.

    Args:
        model: Model key from ``MODEL_PRICING``.
        requests_per_month: Expected number of requests per month.
        avg_input_tokens: Average input tokens per request.
        avg_output_tokens: Average output tokens per request.

    Returns:
        Estimated monthly cost in USD.
    """
    pricing = _get_model(model)
    tokens = estimate_monthly_tokens(requests_per_month, avg_input_tokens, avg_output_tokens)

    input_cost = (tokens["input_tokens"] / 1_000_000) * pricing["input_per_1m"]
    output_cost = (tokens["output_tokens"] / 1_000_000) * pricing["output_per_1m"]
    return round(input_cost + output_cost, 2)


def estimate_latency(
    model: str,
    avg_input_tokens: int,
    avg_output_tokens: int,
    network_overhead_ms: float = DEFAULT_NETWORK_OVERHEAD_MS,
) -> float:
    """Estimate end-to-end latency for a single request.

    Latency is modeled as: network overhead + time-to-first-token + output
    generation time.

    Args:
        model: Model key from ``MODEL_PRICING``.
        avg_input_tokens: Average input tokens per request.
        avg_output_tokens: Average output tokens per request.
        network_overhead_ms: Extra round-trip and queueing time in milliseconds.

    Returns:
        Estimated total latency in milliseconds.
    """
    pricing = _get_model(model)
    ttft_ms = pricing["ttft_ms"]
    output_rate = pricing["output_tokens_per_second"]

    # Simple input-length adjustment: +0.01 ms per input token after the first 1k.
    input_adjustment_ms = max(0, avg_input_tokens - 1000) * 0.01

    output_generation_ms = (avg_output_tokens / output_rate) * 1000
    total_ms = network_overhead_ms + ttft_ms + input_adjustment_ms + output_generation_ms
    return round(total_ms, 2)


def estimate_savings(
    current_model: str,
    requests_per_month: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    recommended_model: str | None = None,
) -> dict[str, float]:
    """Estimate potential savings by switching to a cheaper model.

    Args:
        current_model: Model key currently in use.
        requests_per_month: Expected number of requests per month.
        avg_input_tokens: Average input tokens per request.
        avg_output_tokens: Average output tokens per request.
        recommended_model: Optional model key to switch to. If not provided, a
            cheaper alternative is picked from ``SAVINGS_ALTERNATIVES``.

    Returns:
        Dictionary with ``current_cost``, ``recommended_cost``, ``monthly_savings``,
        and ``savings_percent``.
    """
    current_key = _normalize_model_name(current_model)
    if recommended_model is None:
        recommended_key = SAVINGS_ALTERNATIVES.get(current_key, current_key)
    else:
        recommended_key = _normalize_model_name(recommended_model)

    current_cost = estimate_monthly_cost(
        current_key, requests_per_month, avg_input_tokens, avg_output_tokens
    )
    recommended_cost = estimate_monthly_cost(
        recommended_key, requests_per_month, avg_input_tokens, avg_output_tokens
    )

    monthly_savings = round(current_cost - recommended_cost, 2)
    savings_percent = round((monthly_savings / current_cost) * 100, 2) if current_cost else 0.0

    return {
        "current_cost": current_cost,
        "recommended_cost": recommended_cost,
        "monthly_savings": max(monthly_savings, 0.0),
        "savings_percent": max(savings_percent, 0.0),
    }
