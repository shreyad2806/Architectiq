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
    "gpt-4o-mini": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
        "ttft_ms": 120.0,
        "output_tokens_per_second": 120.0,
    },
    "gpt-4.1": {
        "input_per_1m": 2.00,
        "output_per_1m": 8.00,
        "ttft_ms": 220.0,
        "output_tokens_per_second": 90.0,
    },
    "gpt-4.1-mini": {
        "input_per_1m": 0.40,
        "output_per_1m": 1.60,
        "ttft_ms": 130.0,
        "output_tokens_per_second": 110.0,
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
    "claude-haiku": {
        "input_per_1m": 0.25,
        "output_per_1m": 1.25,
        "ttft_ms": 150.0,
        "output_tokens_per_second": 100.0,
    },
    "gemini-2.5-pro": {
        "input_per_1m": 1.25,
        "output_per_1m": 10.00,
        "ttft_ms": 250.0,
        "output_tokens_per_second": 70.0,
    },
    "gemini-2.5-flash": {
        "input_per_1m": 0.075,
        "output_per_1m": 0.30,
        "ttft_ms": 140.0,
        "output_tokens_per_second": 130.0,
    },
    "llama3": {
        "input_per_1m": 0.00,
        "output_per_1m": 0.00,
        "ttft_ms": 180.0,
        "output_tokens_per_second": 90.0,
    },
    "llama-3.1-70b": {
        "input_per_1m": 0.59,
        "output_per_1m": 0.79,
        "ttft_ms": 220.0,
        "output_tokens_per_second": 75.0,
    },
    "mistral-large": {
        "input_per_1m": 3.00,
        "output_per_1m": 9.00,
        "ttft_ms": 260.0,
        "output_tokens_per_second": 65.0,
    },
}

# Aliases: map variant names to canonical MODEL_PRICING keys
_MODEL_ALIASES: dict[str, str] = {
    "gpt-4":                 "gpt-4o",
    "gpt-4-turbo":           "gpt-4o",
    "gpt-4-turbo-preview":   "gpt-4o",
    "gpt4o":                 "gpt-4o",
    "gpt4":                  "gpt-4o",
    "gpt-4o mini":           "gpt-4o-mini",
    "gpt4omini":             "gpt-4o-mini",
    "claude-3-opus":         "claude-sonnet",
    "claude-3.5-sonnet":     "claude-sonnet",
    "claude-3.5-sonnet-4k":  "claude-sonnet-4",
    "claude-3-haiku":        "claude-haiku",
    "gemini-1.5-pro":        "gemini-2.5-pro",
    "gemini-pro":            "gemini-2.5-pro",
    "gemini-flash":          "gemini-2.5-flash",
    "llama-3":               "llama3",
    "llama3.1":              "llama3",
    "llama-3.1":             "llama-3.1-70b",
}

# Suggested cheaper alternatives used when a specific model is not requested.
SAVINGS_ALTERNATIVES: dict[str, str] = {
    "gpt-4o":         "gpt-4.1",
    "gpt-4.1":        "gpt-4.1-mini",
    "claude-sonnet":  "gemini-2.5-pro",
    "claude-sonnet-4": "gemini-2.5-pro",
    "gemini-2.5-pro": "gemini-2.5-flash",
    "mistral-large":  "gemini-2.5-flash",
    "llama-3.1-70b":  "llama3",
}

# Fallback used when a model cannot be resolved — never silent $0.
_DEFAULT_MODEL = "gpt-4o"

DEFAULT_NETWORK_OVERHEAD_MS = 150.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_model(model: str) -> dict[str, float]:
    """Return pricing and latency constants for a model.

    Normalises the name through the alias table first.  Falls back to
    ``_DEFAULT_MODEL`` (gpt-4o) rather than raising, so unknown model names
    never silently produce $0 — they produce a conservative (high) estimate
    that makes the cost visible and triggers an appropriate finding.
    """
    normalized = model.lower().strip()
    canonical  = _MODEL_ALIASES.get(normalized, normalized)
    return MODEL_PRICING.get(canonical, MODEL_PRICING[_DEFAULT_MODEL])


def _normalize_model_name(model: str) -> str:
    """Return the canonical MODEL_PRICING key for a model name (resolves aliases)."""
    normalized = model.lower().strip()
    return _MODEL_ALIASES.get(normalized, normalized)


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


def estimate_detailed_cost(request: "ReviewRequest") -> dict:  # noqa: F821
    """Return a full 6-line cost breakdown for an architecture request.

    Delegates to ``DetailedCostEstimator`` which is the single source of truth
    for cost arithmetic.  Returns the plain ``dict`` from
    ``CostBreakdown.to_dict()`` plus a ``findings`` list.

    This function is safe to call with any model name — unknown models fall
    back to gpt-4o pricing rather than producing $0.
    """
    from app.services.cost_analyzer import CostAnalyzer  # local import avoids circular
    result = CostAnalyzer().analyze(request)
    bd = result["breakdown"]
    return {
        "monthly_cost":        bd["monthly_cost"],
        "llm_cost":            bd["llm_cost"],
        "embedding_cost":      bd["embedding_cost"],
        "vector_db_cost":      bd["vector_db_cost"],
        "storage_cost":        bd["storage_cost"],
        "infrastructure_cost": bd["infrastructure_cost"],
        "total_before_savings": bd["total_before_savings"],
        "estimated_savings":   bd["estimated_savings"],
        "savings_from_cache":  bd["savings_from_cache"],
        "savings_from_model_switch": bd["savings_from_model_switch"],
        "estimated_monthly_tokens": bd["estimated_monthly_tokens"],
        "findings":            result["findings"],
    }
