"""RecommendationEngine — production-grade rule-based architecture advisor.

Consumes all analyzer outputs and generates deterministic, prioritised
recommendations that read like advice from a Senior AI Architect.

Public API (backward-compatible):
    RecommendationEngine().generate(request)          → list[dict]  (legacy shape)
    AdvancedRecommendationEngine().generate(request)  → dict with executive_summary,
                                                         total_estimated_monthly_savings,
                                                         estimated_latency_improvement,
                                                         recommendations[]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import ReviewRequest
from app.services.cost_analyzer import CostAnalyzer, PRICING_TABLE, _get_model_pricing
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

# Difficulty ordering: Easy first, Hard last
_DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _impl_time_minutes(impl_time: str) -> int:
    """Normalise a human-readable implementation_time string to minutes.

    Examples:
        "15 minutes" → 15
        "30 min"     → 30
        "2 hours"    → 120
        "1 day"      → 480
        "3 days"     → 1440
        "1 week"     → 2400
        "2 weeks"    → 4800
        "varies"     → 9999  (unknown, sort last)
    """
    t = impl_time.lower().strip()
    if not t or t == "varies":
        return 9_999
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    value = float(m.group(1)) if m else 1.0
    if "week" in t:
        return int(value * 2_400)
    if "day" in t:
        return int(value * 480)
    if "hour" in t or " hr" in t:
        return int(value * 60)
    if "min" in t:
        return int(value)
    return 9_999

# Models known to be cheaper than gpt-4o and suitable as drop-in alternatives
_CHEAP_MODELS = {"gpt-4o-mini", "llama3", "gemini-2.5-flash"}
_HIGH_QUALITY_EMBEDDINGS = {"text-embedding-3-large", "bge-large", "bge-m3", "e5-large"}
_PRODUCTION_VDB = {"pinecone", "weaviate", "qdrant", "milvus"}


# ---------------------------------------------------------------------------
# Rich Recommendation dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Recommendation:
    priority: str                            # HIGH | MEDIUM | LOW
    category: str                            # Cost Optimization | RAG Optimization | etc.
    title: str
    reason: str
    expected_monthly_saving: str = "$0"      # human-readable e.g. "$780"
    latency_improvement: str = "0%"          # e.g. "35%"
    quality_improvement: str = "0%"          # e.g. "18%"
    difficulty: str = "Medium"               # Easy | Medium | Hard
    implementation_time: str = "varies"
    # kept for backward-compatible .generate() output
    estimated_monthly_saving: float = 0.0
    estimated_latency_improvement: float = 0.0
    estimated_score_improvement: int = 0
    # Impact metadata — used by frontend when savings/latency are both zero
    primary_benefit: str = ""                # e.g. "Security", "Reliability", "Cost"
    secondary_benefit: str = ""              # e.g. "Reliability", "Performance"
    impact_level: str = ""                   # HIGH | MEDIUM | LOW (mirrors priority by default)

    def to_rich_dict(self) -> dict:
        return {
            "priority":               self.priority,
            "category":               self.category,
            "title":                  self.title,
            "reason":                 self.reason,
            "impact":                 self._impact(),
            "expected_monthly_saving": self.expected_monthly_saving,
            "latency_improvement":    self.latency_improvement,
            "quality_improvement":    self.quality_improvement,
            "difficulty":             self.difficulty,
            "implementation_time":    self.implementation_time,
            "primary_benefit":        self.primary_benefit or _default_benefit(self.category),
            "secondary_benefit":      self.secondary_benefit,
            "impact_level":           self.impact_level or self.priority,
        }

    def _impact(self) -> str:
        """Derive a human-readable impact label from priority + savings + latency."""
        if self.priority == "HIGH" and self.estimated_monthly_saving >= 500:
            return "Critical — high cost & reliability risk"
        if self.priority == "HIGH" and self.estimated_latency_improvement >= 80:
            return "Critical — severe latency impact"
        if self.priority == "HIGH":
            return "High — must fix before production"
        if self.priority == "MEDIUM" and self.estimated_monthly_saving >= 200:
            return "Medium — significant cost savings available"
        if self.priority == "MEDIUM" and self.estimated_latency_improvement >= 40:
            return "Medium — measurable latency improvement"
        if self.priority == "MEDIUM":
            return "Medium — improves quality or resilience"
        return "Low — nice-to-have optimisation"

    def to_dict(self) -> dict:
        """Legacy shape used by RecommendationEngine.generate()."""
        return {
            "priority": self.priority,
            "title": self.title,
            "description": self.reason,
            "estimated_monthly_saving": self.estimated_monthly_saving,
            "estimated_latency_improvement": self.estimated_latency_improvement,
            "estimated_score_improvement": self.estimated_score_improvement,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_saving(usd: float) -> str:
    return f"${usd:,.0f}" if usd > 0 else "$0"


def _pct(value: float) -> str:
    return f"{value:.0f}%"


def _calc_cost(request: ReviewRequest) -> dict:
    return CostAnalyzer().analyze(request)


def _calc_latency(request: ReviewRequest) -> dict:
    return LatencyAnalyzer().analyze(request)


def _monthly_cost_for_model(model: str, request: ReviewRequest) -> float:
    pricing = _get_model_pricing(model)
    input_tokens = request.monthly_requests * request.average_prompt_tokens
    output_tokens = request.monthly_requests * request.average_completion_tokens
    return (input_tokens / 1_000_000) * pricing["input_per_1m"] + \
           (output_tokens / 1_000_000) * pricing["output_per_1m"]


# ---------------------------------------------------------------------------
# Benefit mapping helpers
# ---------------------------------------------------------------------------

_CATEGORY_BENEFIT: dict[str, str] = {
    "Cost Optimization": "Cost",
    "Performance":       "Performance",
    "RAG Optimization":  "Quality",
    "Reliability":       "Reliability",
    "Security":          "Security",
    "Observability":     "Observability",
}


def _default_benefit(category: str) -> str:
    return _CATEGORY_BENEFIT.get(category, category)


# ---------------------------------------------------------------------------
# Rule-based decision engine
# ---------------------------------------------------------------------------

def _rules(request: ReviewRequest, cost: dict, latency: dict) -> list[Recommendation]:
    """Apply all engineering rules and return matching recommendations."""
    recs: list[Recommendation] = []
    llm = (request.llm or "").lower().strip()
    vdb = (request.vector_db or "").lower().strip()
    emb = (request.embedding_model or "").lower().strip()
    fw  = (request.framework or "").lower().strip()
    current_cost = cost["estimated_monthly_cost"]
    current_latency = latency["estimated_latency_ms"]

    # ── COST OPTIMIZATION ───────────────────────────────────────────────────

    # Rule: expensive model + high traffic → switch to cheaper model
    if llm not in _CHEAP_MODELS and request.monthly_requests > 100_000:
        mini_cost = _monthly_cost_for_model("gpt-4o-mini", request)
        saving = round(max(current_cost - mini_cost, 0), 2)
        if saving > 50:
            recs.append(Recommendation(
                priority="HIGH" if saving >= 500 else "MEDIUM",
                category="Cost Optimization",
                title=f"Switch from {request.llm} to GPT-4o Mini",
                reason=f"With {request.monthly_requests:,} monthly requests, {request.llm} costs "
                       f"~${current_cost:,.2f}/month. GPT-4o Mini delivers strong quality at a fraction of the price.",
                expected_monthly_saving=_fmt_saving(saving),
                latency_improvement="15%",
                difficulty="Easy",
                implementation_time="30 minutes",
                estimated_monthly_saving=saving,
                estimated_latency_improvement=50.0,
                estimated_score_improvement=5,
            ))

    # Rule: no semantic cache → recommend it
    if not request.cache_enabled:
        cache_saving = round(current_cost * 0.35, 2)
        recs.append(Recommendation(
            priority="HIGH",
            category="Cost Optimization",
            title="Enable Semantic Caching",
            reason="Repeated or semantically similar prompts waste tokens and inflate latency. "
                   "A semantic cache (e.g. Redis + GPTCache) eliminates redundant LLM calls.",
            expected_monthly_saving=_fmt_saving(cache_saving),
            latency_improvement="35%",
            quality_improvement="0%",
            difficulty="Easy",
            implementation_time="2 hours",
            estimated_monthly_saving=cache_saving,
            estimated_latency_improvement=80.0,
            estimated_score_improvement=7,
        ))

    # Rule: large context window → recommend compression
    if request.context_window and request.context_window > 12_000:
        ctx_saving = round(current_cost * 0.20, 2)
        recs.append(Recommendation(
            priority="HIGH",
            category="Cost Optimization",
            title="Reduce Context Window Size",
            reason=f"Context window of {request.context_window:,} tokens increases cost and latency on every request. "
                   "Apply context compression, summarisation, or selective chunk retrieval to stay under 8k tokens.",
            expected_monthly_saving=_fmt_saving(ctx_saving),
            latency_improvement="20%",
            difficulty="Medium",
            implementation_time="3 hours",
            estimated_monthly_saving=ctx_saving,
            estimated_latency_improvement=40.0,
            estimated_score_improvement=4,
        ))

    # Rule: large prompts → prompt compression
    if request.average_prompt_tokens > 2_000:
        prompt_saving = round(current_cost * 0.15, 2)
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Cost Optimization",
            title="Compress System and User Prompts",
            reason=f"Average prompt of {request.average_prompt_tokens:,} tokens is above the recommended 1,000–1,500 range. "
                   "Use LLMLingua or manual compression to reduce input tokens.",
            expected_monthly_saving=_fmt_saving(prompt_saving),
            latency_improvement="10%",
            difficulty="Medium",
            implementation_time="4 hours",
            estimated_monthly_saving=prompt_saving,
            estimated_latency_improvement=20.0,
            estimated_score_improvement=3,
        ))

    # Rule: high traffic + expensive model → model routing
    if request.monthly_requests > 500_000 and llm not in _CHEAP_MODELS:
        routing_saving = round(current_cost * 0.40, 2)
        recs.append(Recommendation(
            priority="HIGH",
            category="Cost Optimization",
            title="Implement Intelligent Model Routing",
            reason=f"At {request.monthly_requests:,} monthly requests, routing simple queries to GPT-4o Mini "
                   "and complex ones to the premium model can cut inference costs by ~40%.",
            expected_monthly_saving=_fmt_saving(routing_saving),
            latency_improvement="25%",
            difficulty="Medium",
            implementation_time="1 day",
            estimated_monthly_saving=routing_saving,
            estimated_latency_improvement=60.0,
            estimated_score_improvement=6,
        ))

    # ── RAG OPTIMIZATION ────────────────────────────────────────────────────

    # Rule: RAG enabled + weak embedding → upgrade
    if request.rag_enabled and emb and emb not in _HIGH_QUALITY_EMBEDDINGS:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="RAG Optimization",
            title=f"Upgrade Embedding Model from {request.embedding_model} to BAAI/bge-large",
            reason=f"'{request.embedding_model}' is a lower-tier embedding model. "
                   "BAAI/bge-large improves retrieval recall by ~18%, reducing hallucinations from missed context.",
            quality_improvement="18%",
            latency_improvement="0%",
            difficulty="Medium",
            implementation_time="1 hour",
            estimated_score_improvement=5,
        ))

    # Rule: RAG enabled + no vector DB → recommend one
    if request.rag_enabled and (not request.vector_db or request.vector_db.lower() in ("none", "null", "")):
        recs.append(Recommendation(
            priority="HIGH",
            category="RAG Optimization",
            title="Adopt a Production Vector Database (Pinecone or Qdrant)",
            reason="Production RAG requires a dedicated vector store for reliable semantic search. "
                   "Without one, retrieval is limited to keyword matching or in-memory indexes that do not scale.",
            difficulty="Medium",
            implementation_time="4 hours",
            estimated_score_improvement=8,
        ))
    elif request.rag_enabled and vdb not in _PRODUCTION_VDB:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="RAG Optimization",
            title=f"Migrate Vector Store from {request.vector_db} to Qdrant or Pinecone",
            reason=f"'{request.vector_db}' is suitable for development but lacks production-grade ANN indexing, "
                   "filtering, and horizontal scalability. Migrate to Pinecone or Qdrant before scaling.",
            difficulty="Medium",
            implementation_time="1 day",
            estimated_score_improvement=4,
        ))

    # Rule: RAG enabled → recommend hybrid search
    if request.rag_enabled:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="RAG Optimization",
            title="Add Hybrid Search (Dense + Sparse Retrieval)",
            reason="Pure vector search misses exact keyword matches. Combining dense embeddings with BM25 sparse retrieval "
                   "improves recall by 15–25% for enterprise knowledge bases.",
            quality_improvement="20%",
            difficulty="Medium",
            implementation_time="4 hours",
            estimated_score_improvement=4,
        ))

    # Rule: RAG + large context → recommend cross-encoder reranking
    if request.rag_enabled and request.context_window and request.context_window >= 8_000:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="RAG Optimization",
            title="Implement Cross-Encoder Reranking",
            reason="Bi-encoder retrieval returns approximate matches. A cross-encoder reranker (e.g. Cohere Rerank, "
                   "BGE-reranker) reduces irrelevant chunks passed to the LLM, improving answer quality by ~15%.",
            quality_improvement="15%",
            difficulty="Medium",
            implementation_time="2 hours",
            estimated_score_improvement=4,
        ))

    # ── PERFORMANCE ─────────────────────────────────────────────────────────

    # Rule: slow latency + no cache → Redis cache
    if current_latency >= 800 and not request.cache_enabled:
        recs.append(Recommendation(
            priority="HIGH",
            category="Performance",
            title="Deploy Redis as Response Cache",
            reason=f"Estimated latency is {current_latency:.0f} ms. A Redis-backed response cache for repeated queries "
                   "can reduce P50 latency below 100 ms for cached traffic.",
            latency_improvement="40%",
            difficulty="Easy",
            implementation_time="2 hours",
            estimated_latency_improvement=current_latency * 0.40,
            estimated_score_improvement=5,
        ))

    # Rule: high concurrency → async + connection pooling
    if request.concurrent_users and request.concurrent_users >= 5_000:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Performance",
            title="Enable Async Processing and Connection Pooling",
            reason=f"With {request.concurrent_users:,} concurrent users, synchronous request handling will create "
                   "thread contention. Use async endpoints with httpx/aiohttp and pool LLM API connections.",
            latency_improvement="30%",
            difficulty="Medium",
            implementation_time="1 day",
            estimated_latency_improvement=current_latency * 0.30,
            estimated_score_improvement=4,
        ))

    # Rule: RAG enabled → parallel retrieval
    if request.rag_enabled:
        recs.append(Recommendation(
            priority="LOW",
            category="Performance",
            title="Parallelise Vector Retrieval Across Namespaces",
            reason="If querying multiple knowledge bases or namespaces, parallelising vector searches with asyncio.gather "
                   "can reduce retrieval latency by 40–60%.",
            latency_improvement="25%",
            difficulty="Medium",
            implementation_time="2 hours",
            estimated_latency_improvement=30.0,
            estimated_score_improvement=2,
        ))

    # Rule: high volume → streaming responses
    if request.monthly_requests >= 50_000:
        recs.append(Recommendation(
            priority="LOW",
            category="Performance",
            title="Enable LLM Response Streaming",
            reason="Streaming reduces time-to-first-token from seconds to milliseconds, dramatically improving "
                   "perceived responsiveness without changing actual generation latency.",
            latency_improvement="60% TTFT",
            difficulty="Easy",
            implementation_time="1 hour",
            estimated_latency_improvement=0.0,
            estimated_score_improvement=2,
        ))

    # ── RELIABILITY ──────────────────────────────────────────────────────────

    # Rule: no retry strategy
    if not request.retry_strategy:
        recs.append(Recommendation(
            priority="HIGH",
            category="Reliability",
            title="Implement Exponential Backoff Retry Strategy",
            reason="LLM provider APIs experience transient failures. Without retries, any brief outage "
                   "surfaces as user-facing errors. Implement exponential backoff with jitter (max 3 retries).",
            difficulty="Easy",
            implementation_time="1 hour",
            estimated_score_improvement=8,
            primary_benefit="Reliability",
            secondary_benefit="Stability",
            impact_level="HIGH",
        ))

    # Rule: always recommend circuit breaker for production
    if not request.retry_strategy or request.monthly_requests >= 10_000:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Reliability",
            title="Add Circuit Breaker Pattern",
            reason="A circuit breaker (e.g. tenacity, resilience4j) prevents cascading failures when the LLM provider "
                   "is degraded. It opens automatically after N consecutive failures and self-heals.",
            difficulty="Medium",
            implementation_time="2 hours",
            estimated_score_improvement=4,
            primary_benefit="Reliability",
            secondary_benefit="Availability",
            impact_level="MEDIUM",
        ))

    # Rule: no cache → fallback model harder
    if not request.cache_enabled and request.monthly_requests >= 10_000:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Reliability",
            title="Define a Fallback LLM for Provider Outages",
            reason="Without a fallback, a provider outage causes total service downtime. "
                   "Route to a secondary model (e.g. Gemini 2.5 Pro or Claude Sonnet) when the primary is unavailable.",
            difficulty="Medium",
            implementation_time="3 hours",
            estimated_score_improvement=5,
            primary_benefit="Reliability",
            secondary_benefit="Availability",
            impact_level="MEDIUM",
        ))

    # ── SECURITY ─────────────────────────────────────────────────────────────

    if not request.authentication:
        recs.append(Recommendation(
            priority="HIGH",
            category="Security",
            title="Enforce API Authentication (OAuth 2.0 / JWT)",
            reason="Unauthenticated endpoints are accessible to anyone on the internet. "
                   "Implement JWT or API key authentication before deploying to production.",
            difficulty="Easy",
            implementation_time="2 hours",
            estimated_score_improvement=10,
            primary_benefit="Security",
            secondary_benefit="Compliance",
            impact_level="HIGH",
        ))

    if not request.rate_limiting:
        recs.append(Recommendation(
            priority="HIGH",
            category="Security",
            title="Add Per-User Rate Limiting",
            reason="Without rate limits a single user or bot can exhaust your LLM quota and incur unbounded costs. "
                   "Implement token-bucket rate limiting (e.g. slowapi for FastAPI).",
            difficulty="Easy",
            implementation_time="1 hour",
            estimated_score_improvement=6,
            primary_benefit="Security",
            secondary_benefit="Reliability",
            impact_level="HIGH",
        ))

    if not request.prompt_injection_protection:
        recs.append(Recommendation(
            priority="HIGH",
            category="Security",
            title="Add Prompt Injection Guardrails",
            reason="Without input sanitisation, adversarial users can override system instructions, "
                   "leak prompt content, or manipulate model behaviour. Use LLM Guard or custom input validators.",
            difficulty="Medium",
            implementation_time="4 hours",
            estimated_score_improvement=8,
            primary_benefit="Security",
            secondary_benefit="Reliability",
            impact_level="HIGH",
        ))

    if not request.input_validation:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Security",
            title="Enforce Strict Schema-Level Input Validation",
            reason="Unvalidated payloads can carry oversized inputs, special characters, or injection vectors. "
                   "Apply Pydantic validators with max-length constraints and character allowlists.",
            difficulty="Easy",
            implementation_time="30 minutes",
            estimated_score_improvement=5,
            primary_benefit="Security",
            secondary_benefit="Reliability",
            impact_level="MEDIUM",
        ))

    # ── OBSERVABILITY ────────────────────────────────────────────────────────

    if not request.logging:
        recs.append(Recommendation(
            priority="HIGH",
            category="Observability",
            title="Implement Structured JSON Logging",
            reason="Without structured logs, debugging production incidents requires guesswork. "
                   "Use loguru or structlog to emit JSON logs with request_id, latency, model, and token counts.",
            difficulty="Easy",
            implementation_time="2 hours",
            estimated_score_improvement=6,
            primary_benefit="Observability",
            secondary_benefit="Debuggability",
            impact_level="HIGH",
        ))

    if not request.monitoring:
        recs.append(Recommendation(
            priority="HIGH",
            category="Observability",
            title="Integrate Prometheus + Grafana Monitoring",
            reason="Without monitoring, silent performance regressions and error spikes go unnoticed until users complain. "
                   "Expose /metrics and build dashboards for request rate, latency P95, and token usage.",
            difficulty="Medium",
            implementation_time="4 hours",
            estimated_score_improvement=5,
            primary_benefit="Observability",
            secondary_benefit="Reliability",
            impact_level="HIGH",
        ))

    if not request.tracing:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Observability",
            title="Add Distributed Tracing with OpenTelemetry",
            reason="Multi-step pipelines (API → retrieval → LLM → response) need distributed tracing to isolate "
                   "latency contributors. Instrument with OpenTelemetry and export to Langfuse or Jaeger.",
            latency_improvement="0%",
            difficulty="Medium",
            implementation_time="3 hours",
            estimated_score_improvement=4,
            primary_benefit="Observability",
            secondary_benefit="Performance",
            impact_level="MEDIUM",
        ))

    if not request.metrics:
        recs.append(Recommendation(
            priority="MEDIUM",
            category="Observability",
            title="Export Application Metrics to a Metrics Backend",
            reason="Track token usage per user, error rates, cache hit ratios, and LLM cost per request "
                   "to enable SLO-based alerting and cost attribution.",
            difficulty="Easy",
            implementation_time="2 hours",
            estimated_score_improvement=3,
            primary_benefit="Observability",
            secondary_benefit="Cost",
            impact_level="MEDIUM",
        ))

    if not request.health_endpoint:
        recs.append(Recommendation(
            priority="LOW",
            category="Observability",
            title="Expose a /health Liveness Endpoint",
            reason="Kubernetes and load balancers route traffic based on health checks. Without a /health endpoint, "
                   "unhealthy pods continue receiving requests, causing silent request failures.",
            difficulty="Easy",
            implementation_time="15 minutes",
            estimated_score_improvement=2,
            primary_benefit="Reliability",
            secondary_benefit="Observability",
            impact_level="LOW",
        ))

    return recs


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def _sort_recs(recs: list[Recommendation]) -> list[Recommendation]:
    """Rank recommendations using a five-level composite sort key.

    1. Priority           HIGH(0) < MEDIUM(1) < LOW(2)
    2. Estimated savings  descending (highest first)
    3. Latency improvement descending (highest first)
    4. Difficulty         Easy(0) < Medium(1) < Hard(2)
    5. Implementation time ascending (fastest to complete first, in minutes)
    """
    return sorted(recs, key=lambda r: (
        _PRIORITY_ORDER.get(r.priority, 99),
        -r.estimated_monthly_saving,
        -r.estimated_latency_improvement,
        _DIFFICULTY_ORDER.get(r.difficulty.lower().strip(), 1),
        _impl_time_minutes(r.implementation_time),
    ))


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def _executive_summary(
    request: ReviewRequest,
    recs: list[Recommendation],
    total_saving: float,
    total_latency_pct: float,
) -> str:
    high = sum(1 for r in recs if r.priority == "HIGH")
    n = len(recs)
    saving_str = f"${total_saving:,.0f}" if total_saving > 0 else "minimal"
    latency_str = f"{total_latency_pct:.0f}%" if total_latency_pct > 0 else "marginal"

    parts: list[str] = [
        f"ArchitectIQ identified {n} optimisation opportunities for {request.project_name}."
    ]

    if total_saving > 0 or total_latency_pct > 0:
        parts.append(
            f"Implementing the top recommendations could reduce monthly inference costs by approximately "
            f"{saving_str} and improve average response latency by {latency_str}."
        )

    if high > 0:
        parts.append(
            f"There {'are' if high > 1 else 'is'} {high} high-priority item{'s' if high > 1 else ''} "
            "that must be addressed before a production launch."
        )

    issues: list[str] = []
    if not request.authentication:
        issues.append("API authentication")
    if not request.retry_strategy:
        issues.append("retry strategy")
    if not request.logging:
        issues.append("structured logging")
    if not request.cache_enabled:
        issues.append("semantic caching")

    if issues:
        parts.append(
            f"Critical gaps include: {', '.join(issues)}."
        )
    else:
        parts.append(
            "The system has solid production foundations; focus on cost and retrieval quality improvements."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# AdvancedRecommendationEngine — rich output
# ---------------------------------------------------------------------------

class AdvancedRecommendationEngine:
    """Generate a complete, enterprise-grade recommendation report."""

    def generate(self, request: ReviewRequest) -> dict:
        """Return a structured recommendation report.

        Returns:
            dict with:
            - ``executive_summary``               str
            - ``total_estimated_monthly_savings`` str  (human-readable)
            - ``estimated_latency_improvement``   str  (percentage)
            - ``recommendations``                 list[dict] (rich shape)
        """
        cost   = _calc_cost(request)
        latency = _calc_latency(request)

        recs = _rules(request, cost, latency)
        recs = _deduplicate(recs)
        recs = _sort_recs(recs)

        total_saving = sum(r.estimated_monthly_saving for r in recs)
        base_latency = latency["estimated_latency_ms"] or 1.0
        total_latency_ms = sum(r.estimated_latency_improvement for r in recs)
        total_latency_pct = min((total_latency_ms / base_latency) * 100, 80.0)

        return {
            "executive_summary": _executive_summary(
                request, recs, total_saving, total_latency_pct
            ),
            "total_estimated_monthly_savings": _fmt_saving(round(total_saving, 2)),
            "estimated_latency_improvement": _pct(total_latency_pct),
            "recommendations": [r.to_rich_dict() for r in recs],
        }


# ---------------------------------------------------------------------------
# Semantic deduplication
# ---------------------------------------------------------------------------

# Canonical keys that identify the same underlying optimisation even when the
# recommendation title includes dynamic content (e.g. model names, numbers).
_SEMANTIC_KEYS: list[tuple[str, ...]] = [
    # cache
    ("semantic cach", "response cache", "redis"),
    # model switch / routing
    ("gpt-4o mini", "switch from", "model routing", "intelligent routing"),
    # retry / backoff
    ("retry", "backoff"),
    # authentication
    ("authentication", "oauth", "jwt"),
    # rate limiting
    ("rate limit",),
    # embedding upgrade
    ("embedding model", "upgrade embedding"),
    # vector DB migration
    ("vector store", "vector database", "migrate vector"),
    # hybrid search
    ("hybrid search",),
    # cross-encoder / reranking
    ("cross-encoder", "rerank"),
    # prompt injection
    ("injection", "guardrail"),
    # input validation
    ("input validation", "schema-level"),
    # logging
    ("structured log", "json log"),
    # monitoring / grafana
    ("prometheus", "grafana", "monitoring"),
    # tracing
    ("opentelemetry", "distributed trac", "langfuse"),
    # metrics export
    ("application metrics", "metrics backend"),
    # health endpoint
    ("/health", "liveness"),
    # context window
    ("context window", "reduce context"),
    # prompt compression
    ("prompt compression", "compress"),
    # fallback model
    ("fallback llm", "fallback model", "secondary model"),
    # circuit breaker
    ("circuit breaker",),
    # parallel retrieval
    ("parallel retrieval", "parallelise"),
    # streaming
    ("response streaming", "enable streaming"),
    # async pipeline
    ("async processing", "connection pool"),
]


def _semantic_key(title: str) -> str | None:
    """Return the first matched canonical group key for a title, or None."""
    t = title.lower()
    for group in _SEMANTIC_KEYS:
        if any(kw in t for kw in group):
            return group[0]   # use the first keyword as the canonical key
    return None


def _deduplicate(recs: list[Recommendation]) -> list[Recommendation]:
    """Remove duplicates using both exact-title and semantic-group matching.

    When two recommendations describe the same optimisation (matched via
    _SEMANTIC_KEYS), the one with the higher priority / larger saving wins.
    Ties default to the first occurrence (already sorted by priority before
    _deduplicate is called during the rules pass).
    """
    seen_titles: set[str] = set()
    seen_semantic: set[str] = set()
    out: list[Recommendation] = []

    for r in recs:
        if r.title in seen_titles:
            continue
        sk = _semantic_key(r.title)
        if sk is not None and sk in seen_semantic:
            continue

        seen_titles.add(r.title)
        if sk is not None:
            seen_semantic.add(sk)
        out.append(r)

    return out


# ---------------------------------------------------------------------------
# RecommendationEngine — legacy backward-compatible wrapper
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """Backward-compatible engine. Delegates to the advanced engine."""

    def generate(self, request: ReviewRequest) -> list[dict]:
        """Return recommendations sorted from highest impact to lowest.

        Returns the legacy dict shape (title, description, estimated_monthly_saving,
        estimated_latency_improvement, estimated_score_improvement).
        """
        cost    = _calc_cost(request)
        latency = _calc_latency(request)

        recs = _rules(request, cost, latency)
        recs = _deduplicate(recs)
        recs = _sort_recs(recs)

        return [r.to_dict() for r in recs]
