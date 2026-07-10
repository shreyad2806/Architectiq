"""ArchitectureHealthAggregator.

Derives four human-readable Architecture Health scores (0–100) from the
already-executed analyzer results stored in the ReviewReportBuilder raw dict.

No analyzer is re-run here — every value is taken from the results already
computed by ReviewReportBuilder.build().

Public API:
    ArchitectureHealthAggregator().aggregate(request, analyzer_results) -> dict

Returns:
    {
        "cost_efficiency": int,   # 0-100
        "latency":         int,   # 0-100
        "reliability":     int,   # 0-100
        "scalability":     int,   # 0-100
    }
"""

from __future__ import annotations

from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# Cost Efficiency
# ---------------------------------------------------------------------------
# Reference ceiling above which cost_efficiency → 0
_COST_CEILING_USD = 50_000.0

# Bonus points for cost-reducing features (max total bonus = 25)
_COST_CACHE_BONUS         = 15   # semantic/response cache present
_COST_CHEAP_EMBEDDING_BONUS = 5  # small embedding model chosen
_COST_SAVINGS_BONUS_MAX   = 5    # potential savings as a bonus (scaled)

_CHEAP_EMBEDDING_MODELS = {
    "text-embedding-3-small",
    "text-embedding-ada-002",
    "bge-small",
    "e5-small",
    "minilm",
}

_EXPENSIVE_MODELS = {
    "gpt-4o",
    "gpt-4.1",
    "claude-sonnet",
    "claude-sonnet-4",
    "gemini-2.5-pro",
}


def _cost_efficiency(request: ReviewRequest, cost_result: dict) -> int:
    """Compute Cost Efficiency score (0-100).

    Formula:
        base   = 100 × (1 - monthly_cost / ceiling)
        bonus  += 15  if cache_enabled
        bonus  += 5   if cheap embedding model
        bonus  += 0-5 scaled from potential savings %
        score  = clamp(base + bonus, 0, 100)
    """
    monthly_cost = float(cost_result.get("estimated_monthly_cost", 0) or 0)
    savings      = float(cost_result.get("potential_monthly_savings", 0) or 0)

    # Base: invert cost — lower cost → higher score
    base = max(0.0, 1.0 - monthly_cost / _COST_CEILING_USD) * 75  # out of 75

    # Bonus: cache
    bonus = _COST_CACHE_BONUS if request.cache_enabled else 0

    # Bonus: cheap embedding model
    if (request.embedding_model or "").lower().strip() in _CHEAP_EMBEDDING_MODELS:
        bonus += _COST_CHEAP_EMBEDDING_BONUS

    # Bonus: potential savings % (up to 5 pts)
    if monthly_cost > 0:
        savings_pct = savings / monthly_cost
        bonus += round(min(savings_pct, 1.0) * _COST_SAVINGS_BONUS_MAX)

    return min(100, max(0, round(base + bonus)))


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------
# Reference ceiling: above this latency → score 0
_LATENCY_CEILING_MS = 3_000.0

# Bonus points for latency-reducing features (max total bonus = 25)
_LATENCY_CACHE_BONUS   = 15   # semantic cache cuts repeated-query latency
_LATENCY_NO_RAG_BONUS  = 5    # RAG adds overhead; not having it is neutral+
_LATENCY_RETRY_PENALTY = 5    # retry logic slightly increases p99 latency

_FAST_MODELS = {"gpt-4o-mini", "llama3", "gemini-2.5-pro"}


def _latency_score(request: ReviewRequest, latency_result: dict) -> int:
    """Compute Latency score (0-100).

    Formula:
        base   = 100 × (1 - estimated_latency_ms / ceiling)  [out of 75]
        bonus  += 15  if cache_enabled
        bonus  += 5   if not rag_enabled   (no extra retrieval hop)
        penalty -= 5  if retry_strategy    (minor p99 overhead acknowledgement)
        score  = clamp(base + bonus, 0, 100)
    """
    latency_ms = float(latency_result.get("estimated_latency_ms", 500) or 500)

    base  = max(0.0, 1.0 - latency_ms / _LATENCY_CEILING_MS) * 75  # out of 75
    bonus = _LATENCY_CACHE_BONUS if request.cache_enabled else 0

    if not request.rag_enabled:
        bonus += _LATENCY_NO_RAG_BONUS

    # Retry strategy slightly increases observed p99 latency
    if request.retry_strategy:
        bonus -= _LATENCY_RETRY_PENALTY

    return min(100, max(0, round(base + bonus)))


# ---------------------------------------------------------------------------
# Reliability
# ---------------------------------------------------------------------------
# The ReliabilityAnalyzer already produces a 0-100 score via a deduction model.
# We enrich it with additional signals from other analyzer results that affect
# operational reliability.

_RELIABILITY_MONITORING_BONUS  = 5   # monitoring configured
_RELIABILITY_LOGGING_BONUS     = 5   # structured logging enabled
_RELIABILITY_AUTH_BONUS        = 5   # authentication protects against abuse
_RELIABILITY_TRACING_BONUS     = 3   # distributed tracing aids incident response
_RELIABILITY_HEALTH_BONUS      = 2   # health endpoint enables orchestrator restarts
_RELIABILITY_BONUS_CAP         = 15  # total bonus capped so base score dominates


def _reliability_score(request: ReviewRequest, reliability_result: dict) -> int:
    """Compute Reliability score (0-100).

    Uses ReliabilityAnalyzer base score (already 0-100) then adds bonuses for
    observability/ops features that improve mean-time-to-recovery (MTTR).

    Bonus features (capped at +15 total):
        monitoring   +5
        logging      +5
        tracing      +3
        health_endpoint +2
    """
    base  = int(reliability_result.get("reliability_score", 0) or 0)
    bonus = 0

    if request.monitoring:
        bonus += _RELIABILITY_MONITORING_BONUS
    if request.logging:
        bonus += _RELIABILITY_LOGGING_BONUS
    if request.tracing:
        bonus += _RELIABILITY_TRACING_BONUS
    if request.health_endpoint:
        bonus += _RELIABILITY_HEALTH_BONUS

    bonus = min(bonus, _RELIABILITY_BONUS_CAP)
    return min(100, max(0, base + bonus))


# ---------------------------------------------------------------------------
# Scalability
# ---------------------------------------------------------------------------
# ScalabilityAnalyzer already produces a 0-100 score.
# We enrich it with signals that affect horizontal scale capability.

_SCALABILITY_OBSERVABILITY_BONUS = 5   # metrics/monitoring enables auto-scaling decisions
_SCALABILITY_METRICS_BONUS       = 3   # exportable metrics feed autoscalers
_SCALABILITY_ASYNC_BONUS         = 5   # async framework scales better under load
_SCALABILITY_BONUS_CAP           = 10

_ASYNC_FRAMEWORKS = {"fastapi", "express", "nestjs", "go", "gin", "actix", "axum"}


def _scalability_score(request: ReviewRequest, scalability_result: dict) -> int:
    """Compute Scalability score (0-100).

    Uses ScalabilityAnalyzer base score (already 0-100) then adds bonuses for
    observability and async architecture signals.

    Bonus features (capped at +10 total):
        monitoring/metrics   +5 / +3
        async framework      +5
    """
    base  = int(scalability_result.get("scalability_score", 0) or 0)
    bonus = 0

    if request.monitoring or request.observability:
        bonus += _SCALABILITY_OBSERVABILITY_BONUS
    if request.metrics:
        bonus += _SCALABILITY_METRICS_BONUS
    if (request.framework or "").lower().strip() in _ASYNC_FRAMEWORKS:
        bonus += _SCALABILITY_ASYNC_BONUS

    bonus = min(bonus, _SCALABILITY_BONUS_CAP)
    return min(100, max(0, base + bonus))


# ---------------------------------------------------------------------------
# Insight captions — short dynamic text shown below each health bar
# ---------------------------------------------------------------------------

def _cost_insight(score: int, request: ReviewRequest) -> str:
    if not request.cache_enabled and score < 70:
        return "Enabling caching would reduce token spend"
    if score >= 85:
        return "Cost profile is well-optimised"
    if score >= 60:
        return "Moderate savings potential identified"
    return "High inference cost — model routing recommended"


def _latency_insight(score: int, request: ReviewRequest) -> str:
    if request.cache_enabled and score >= 80:
        return "Cache is reducing repeated-query latency"
    if not request.cache_enabled and score < 70:
        return "Semantic cache would cut p95 latency"
    if request.rag_enabled and score < 65:
        return "RAG retrieval adds pipeline overhead"
    if score >= 85:
        return "P95 within acceptable SLA range"
    return "Latency optimisation opportunities exist"


def _reliability_insight(score: int, request: ReviewRequest) -> str:
    if not request.retry_strategy and score < 60:
        return "No retry policy — transient failures surface to users"
    if not request.authentication and score < 70:
        return "Unauthenticated endpoints increase risk"
    if score >= 85:
        return "Resilience controls are well-configured"
    if score >= 65:
        return "Some reliability controls are missing"
    return "Critical reliability gaps require immediate attention"


def _scalability_insight(score: int, request: ReviewRequest) -> str:
    if not request.cache_enabled and score < 70:
        return "Cache is critical at this traffic volume"
    if score >= 85:
        return "Architecture scales to current traffic demands"
    if score >= 65:
        return "Horizontal scaling improvements recommended"
    return "Scalability bottlenecks identified"


# ---------------------------------------------------------------------------
# Public aggregator
# ---------------------------------------------------------------------------

class ArchitectureHealthAggregator:
    """Derive Architecture Health scores from pre-computed analyzer results."""

    def aggregate(
        self,
        request: ReviewRequest,
        cost_result: dict,
        latency_result: dict,
        reliability_result: dict,
        scalability_result: dict,
    ) -> dict:
        """Return Architecture Health dict with four 0-100 scores and captions.

        Args:
            request:            The original architecture review request.
            cost_result:        Output of CostAnalyzer.analyze().
            latency_result:     Output of LatencyAnalyzer.analyze().
            reliability_result: Output of ReliabilityAnalyzer.analyze().
            scalability_result: Output of ScalabilityAnalyzer.analyze().

        Returns:
            Dict with keys: cost_efficiency, latency, reliability, scalability,
            and corresponding _insight keys.
        """
        ce  = _cost_efficiency(request, cost_result)
        lat = _latency_score(request, latency_result)
        rel = _reliability_score(request, reliability_result)
        sca = _scalability_score(request, scalability_result)

        return {
            "cost_efficiency":      ce,
            "latency":              lat,
            "reliability":          rel,
            "scalability":          sca,
            "cost_efficiency_insight":  _cost_insight(ce, request),
            "latency_insight":          _latency_insight(lat, request),
            "reliability_insight":      _reliability_insight(rel, request),
            "scalability_insight":      _scalability_insight(sca, request),
        }
