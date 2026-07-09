"""RecommendationEngine.

Collects findings from every analyzer, attaches impact metadata, and
returns a deduplicated list of recommendations sorted from highest
impact to lowest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import ReviewRequest
from app.services.cost_analyzer import CostAnalyzer
from app.services.latency_analyzer import LatencyAnalyzer
from app.services.observability_analyzer import ObservabilityAnalyzer
from app.services.production_readiness_analyzer import ProductionReadinessAnalyzer
from app.services.rag_analyzer import RagAnalyzer
from app.services.reliability_analyzer import ReliabilityAnalyzer
from app.services.scalability_analyzer import ScalabilityAnalyzer
from app.services.security_analyzer import SecurityAnalyzer


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------
_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@dataclass(frozen=True)
class Recommendation:
    priority: str                           # HIGH | MEDIUM | LOW
    title: str
    description: str
    estimated_monthly_saving: float = 0.0   # USD
    estimated_latency_improvement: float = 0.0  # ms
    estimated_score_improvement: int = 0    # points (0-100 scale)

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "estimated_monthly_saving": self.estimated_monthly_saving,
            "estimated_latency_improvement": self.estimated_latency_improvement,
            "estimated_score_improvement": self.estimated_score_improvement,
        }


# ---------------------------------------------------------------------------
# Static recommendation catalogue
# Each entry is keyed by a feature flag that, when False, triggers the rec.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _CatalogueEntry:
    feature: str
    priority: str
    title: str
    description: str
    estimated_monthly_saving: float = 0.0
    estimated_latency_improvement: float = 0.0
    estimated_score_improvement: int = 0


_CATALOGUE: list[_CatalogueEntry] = [
    # ----- Security -----
    _CatalogueEntry(
        feature="authentication",
        priority="HIGH",
        title="Enable API Authentication",
        description="API endpoints are publicly accessible. Implement OAuth 2.0 / JWT or API key authentication to restrict access.",
        estimated_score_improvement=10,
    ),
    _CatalogueEntry(
        feature="prompt_injection_protection",
        priority="HIGH",
        title="Add Prompt Injection Protection",
        description="Without guardrails, malicious users can hijack LLM behaviour. Sanitise inputs and add a guardrails layer.",
        estimated_score_improvement=8,
    ),
    _CatalogueEntry(
        feature="rate_limiting",
        priority="HIGH",
        title="Enforce Rate Limiting",
        description="No rate limiting leaves the service open to abuse and traffic spikes. Add token-bucket or sliding-window rate limiting.",
        estimated_score_improvement=6,
    ),
    _CatalogueEntry(
        feature="input_validation",
        priority="MEDIUM",
        title="Add Strict Input Validation",
        description="Unvalidated payloads increase injection risk. Enforce schema validation (e.g. Pydantic) and reject malformed requests.",
        estimated_score_improvement=5,
    ),
    # ----- Reliability -----
    _CatalogueEntry(
        feature="retry_strategy",
        priority="HIGH",
        title="Implement Retry and Failover Strategy",
        description="Without retries, transient LLM or network failures surface directly to users. Add exponential backoff with jitter.",
        estimated_score_improvement=8,
    ),
    # ----- Production Readiness -----
    _CatalogueEntry(
        feature="observability",
        priority="MEDIUM",
        title="Enable Observability",
        description="No observability makes it impossible to diagnose incidents. Configure tracing and monitoring.",
        estimated_score_improvement=5,
    ),
    # ----- Observability -----
    _CatalogueEntry(
        feature="logging",
        priority="MEDIUM",
        title="Enable Structured Logging",
        description="Add structured JSON logging to capture request context, errors, and LLM interactions.",
        estimated_score_improvement=4,
    ),
    _CatalogueEntry(
        feature="monitoring",
        priority="MEDIUM",
        title="Integrate a Monitoring Platform",
        description="Without monitoring you will miss degraded performance and outages. Add Prometheus + Grafana or Datadog.",
        estimated_score_improvement=5,
    ),
    _CatalogueEntry(
        feature="tracing",
        priority="MEDIUM",
        title="Add Distributed Tracing",
        description="Distributed tracing is essential for diagnosing latency across services. Instrument with OpenTelemetry.",
        estimated_latency_improvement=30.0,
        estimated_score_improvement=4,
    ),
    _CatalogueEntry(
        feature="metrics",
        priority="LOW",
        title="Export Application Metrics",
        description="Collect and export metrics (token usage, error rates, request counts) to a metrics backend.",
        estimated_score_improvement=3,
    ),
    _CatalogueEntry(
        feature="health_endpoint",
        priority="LOW",
        title="Expose a Health Check Endpoint",
        description="A /health endpoint allows load balancers and orchestrators to verify service readiness.",
        estimated_score_improvement=2,
    ),
    # ----- Cost / Performance -----
    _CatalogueEntry(
        feature="cache_enabled",
        priority="HIGH",
        title="Enable Semantic Caching",
        description="Without caching, every request hits the LLM. Semantic caching can cut costs by 30-60% for repetitive workloads.",
        estimated_monthly_saving=300.0,
        estimated_latency_improvement=80.0,
        estimated_score_improvement=7,
    ),
    # ----- RAG -----
    _CatalogueEntry(
        feature="rag_enabled",
        priority="MEDIUM",
        title="Enable Retrieval-Augmented Generation",
        description="RAG grounds responses in your knowledge base and reduces hallucinations. Enable RAG for knowledge-intensive tasks.",
        estimated_score_improvement=6,
    ),
    # ----- Scalability / Reliability -----
    _CatalogueEntry(
        feature="memory",
        priority="LOW",
        title="Add Session Memory",
        description="Stateless designs cause inconsistent multi-turn behaviour. Add session memory or a conversation store.",
        estimated_score_improvement=3,
    ),
]


# ---------------------------------------------------------------------------
# Dynamic recommendations (computed from analyzer results)
# ---------------------------------------------------------------------------

def _dynamic_recommendations(request: ReviewRequest) -> list[Recommendation]:
    """Generate recommendations that depend on computed values (cost, latency)."""
    recs: list[Recommendation] = []

    cost_result = CostAnalyzer().analyze(request)
    savings = cost_result["potential_monthly_savings"]
    if savings > 0:
        recs.append(Recommendation(
            priority="HIGH" if savings >= 500 else "MEDIUM",
            title="Switch to a More Cost-Efficient LLM",
            description=(
                f"Your current LLM ({request.llm}) costs an estimated "
                f"${cost_result['estimated_monthly_cost']:,.2f}/month. "
                f"Switching to a cheaper alternative could save ~${savings:,.2f}/month."
            ),
            estimated_monthly_saving=round(savings, 2),
            estimated_score_improvement=4,
        ))

    latency_result = LatencyAnalyzer().analyze(request)
    if latency_result["latency_rating"] in ("Moderate", "Slow"):
        improvement = 0.0
        description_parts = []
        if not request.cache_enabled:
            improvement += 80.0
            description_parts.append("enable caching (−80 ms)")
        if request.context_window and request.context_window > 32_000:
            improvement += 40.0
            description_parts.append("reduce context window (−40 ms)")
        if improvement > 0:
            recs.append(Recommendation(
                priority="MEDIUM",
                title="Reduce Request Latency",
                description=(
                    f"Estimated latency is {latency_result['estimated_latency_ms']} ms "
                    f"({latency_result['latency_rating']}). Consider: {'; '.join(description_parts)}."
                ),
                estimated_latency_improvement=round(improvement, 2),
                estimated_score_improvement=3,
            ))

    return recs


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """Collect findings from every analyzer and return sorted recommendations."""

    def generate(self, request: ReviewRequest) -> list[dict]:
        """Return recommendations sorted from highest impact to lowest.

        Sorting key (descending priority):
            1. Priority   HIGH > MEDIUM > LOW
            2. score_improvement (desc)
            3. monthly_saving (desc)

        Args:
            request: The architecture review request.

        Returns:
            List of recommendation dicts, each with ``priority``, ``title``,
            ``description``, ``estimated_monthly_saving``,
            ``estimated_latency_improvement``, and ``estimated_score_improvement``.
        """
        recs: list[Recommendation] = []

        # Static catalogue
        for entry in _CATALOGUE:
            value = getattr(request, entry.feature, False)
            if not value:
                recs.append(Recommendation(
                    priority=entry.priority,
                    title=entry.title,
                    description=entry.description,
                    estimated_monthly_saving=entry.estimated_monthly_saving,
                    estimated_latency_improvement=entry.estimated_latency_improvement,
                    estimated_score_improvement=entry.estimated_score_improvement,
                ))

        # Dynamic (cost / latency)
        recs.extend(_dynamic_recommendations(request))

        # Sort: priority tier first, then by score improvement, then by saving
        recs.sort(key=lambda r: (
            _PRIORITY_ORDER.get(r.priority, 99),
            -r.estimated_score_improvement,
            -r.estimated_monthly_saving,
        ))

        return [r.to_dict() for r in recs]
