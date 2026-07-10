"""RoadmapGenerator.

Builds a three-phase Optimization Roadmap directly from the rich
recommendations produced by AdvancedRecommendationEngine, using the
architecture request to suppress items the system already satisfies.

Public API:
    RoadmapGenerator().generate(
        recommendations: list[dict],
        request: ReviewRequest,
    ) -> list[dict]

Output shape (each phase):
    {
        "phase":    int,
        "title":    str,
        "timeline": str,
        "tasks":    list[dict]   # full task objects, not just strings
    }

Each task dict:
    {
        "title":                  str,
        "priority":               str,   # HIGH | MEDIUM | LOW
        "category":               str,
        "reason":                 str,
        "expected_monthly_saving": str,
        "latency_improvement":    str,
        "difficulty":             str,
        "implementation_time":    str,
    }

Phase assignment rules
─────────────────────
Phase 1 — Quick Wins (Today)
    Semantic: Authentication, Rate Limiting, Retry, Cache, Logging, Input Validation
    Structural: HIGH priority AND difficulty Easy AND implementation_time < 1 day

Phase 2 — Performance Improvements (This Week)
    Semantic: Hybrid Search, Better Embeddings, Cross-Encoder, Async Pipeline,
              Streaming, Parallel Retrieval, Prompt Compression, Model Routing,
              Context Window, Redis Cache
    Structural: MEDIUM priority OR difficulty Medium OR 1-day tasks

Phase 3 — Production Scaling (This Month)
    Semantic: Observability, Grafana, Langfuse, Queue, Fallback Model,
              Multi-region, Tracing, Monitoring, Metrics, Health Endpoint
    Structural: LOW priority OR difficulty Hard OR multi-week tasks

Priority within each phase: HIGH first, then MEDIUM, then LOW.
No duplicate titles across phases.
Items already solved by the architecture are excluded.
"""

from __future__ import annotations

from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# Phase metadata
# ---------------------------------------------------------------------------

_PHASE_META: dict[int, dict] = {
    1: {"phase": 1, "title": "Quick Wins",           "timeline": "Today"},
    2: {"phase": 2, "title": "Performance Improvements", "timeline": "This Week"},
    3: {"phase": 3, "title": "Production Scaling",   "timeline": "This Month"},
}

_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ---------------------------------------------------------------------------
# Semantic category → phase mapping
# Checked against rec["title"].lower() and rec["category"].lower()
# ---------------------------------------------------------------------------

# Keywords that force a recommendation into Phase 1
_PHASE1_KEYWORDS: frozenset[str] = frozenset({
    "authentication", "auth", "oauth", "jwt",
    "rate limit", "rate-limit", "ratelimit",
    "retry", "backoff",
    "cache", "caching",
    "logging", "logs", "structured log",
    "input validation", "schema-level",
    "guardrail", "injection",
})

# Keywords that force Phase 2
_PHASE2_KEYWORDS: frozenset[str] = frozenset({
    "hybrid search", "hybrid retrieval",
    "embedding", "embed",
    "cross-encoder", "cross encoder", "rerank",
    "async", "connection pool",
    "streaming", "stream",
    "parallel retrieval", "parallelise",
    "prompt compression", "compress",
    "model routing", "intelligent routing",
    "context window", "reduce context",
    "redis",
    "circuit breaker",
    "fallback llm", "fallback model", "secondary model",
})

# Keywords that force Phase 3
_PHASE3_KEYWORDS: frozenset[str] = frozenset({
    "observability", "grafana", "langfuse", "jaeger",
    "prometheus", "monitoring", "dashboard",
    "tracing", "opentelemetry", "otel",
    "metrics", "metric",
    "health endpoint", "/health", "liveness",
    "queue", "message queue",
    "multi-region", "multi region",
    "scaling", "auto-scaling", "horizontal scaling",
})


def _matches(text: str, keywords: frozenset[str]) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)


def _semantic_phase(rec: dict) -> int | None:
    """Return phase 1/2/3 if the title or category matches a keyword set, else None."""
    combined = (rec.get("title") or "") + " " + (rec.get("category") or "")
    if _matches(combined, _PHASE1_KEYWORDS):
        return 1
    if _matches(combined, _PHASE2_KEYWORDS):
        return 2
    if _matches(combined, _PHASE3_KEYWORDS):
        return 3
    return None


# ---------------------------------------------------------------------------
# Structural phase (fallback when no keyword match)
# ---------------------------------------------------------------------------

_FAST_TIME_TOKENS: frozenset[str] = frozenset({
    "minute", "minutes", "min", "hour", "hours", "hr",
})

_MULTI_WEEK_TOKENS: frozenset[str] = frozenset({
    "week", "month", "sprint",
})


def _is_sub_day(impl_time: str) -> bool:
    t = impl_time.lower()
    if t in ("1 day", "one day", "1day"):
        return False
    return any(tok in t for tok in _FAST_TIME_TOKENS)


def _structural_phase(rec: dict) -> int:
    priority   = (rec.get("priority") or "LOW").upper()
    difficulty = (rec.get("difficulty") or "medium").lower().strip()
    impl_time  = (rec.get("implementation_time") or "").lower().strip()

    fast       = _is_sub_day(impl_time)
    multi_week = any(t in impl_time for t in _MULTI_WEEK_TOKENS)

    if priority == "HIGH" and difficulty == "easy" and fast:
        return 1
    if multi_week or difficulty == "hard":
        return 3
    if priority == "LOW":
        return 3
    return 2


def _assign_phase(rec: dict) -> int:
    sem = _semantic_phase(rec)
    return sem if sem is not None else _structural_phase(rec)


# ---------------------------------------------------------------------------
# Solved-by-architecture guard
# ---------------------------------------------------------------------------

def _already_solved(rec: dict, request: ReviewRequest) -> bool:
    """Return True when the architecture already satisfies this recommendation."""
    title_lower = (rec.get("title") or "").lower()
    cat_lower   = (rec.get("category") or "").lower()

    checks: list[tuple[bool, list[str]]] = [
        (bool(request.authentication),            ["authentication", "oauth", "jwt", "api auth"]),
        (bool(request.rate_limiting),              ["rate limit", "rate-limit", "ratelimit"]),
        (bool(request.retry_strategy),             ["retry", "backoff"]),
        (bool(request.cache_enabled),              ["semantic cach", "response cache", "redis", "enable cache", "enable semantic"]),
        (bool(request.logging),                    ["structured log", "json log", "structlog", "loguru"]),
        (bool(request.monitoring),                 ["prometheus", "grafana", "monitoring"]),
        (bool(request.tracing),                    ["tracing", "opentelemetry", "otel", "langfuse", "jaeger"]),
        (bool(request.metrics),                    ["export application metrics", "metrics backend"]),
        (bool(request.health_endpoint),            ["/health", "liveness", "health endpoint"]),
        (bool(request.input_validation),           ["input validation", "schema-level", "strict schema"]),
        (bool(request.prompt_injection_protection), ["injection guardrail", "injection protection", "llm guard"]),
    ]

    combined = title_lower + " " + cat_lower
    for satisfied, keywords in checks:
        if satisfied and any(kw in combined for kw in keywords):
            return True
    return False


# ---------------------------------------------------------------------------
# Task dict builder
# ---------------------------------------------------------------------------

def _to_task(rec: dict) -> dict:
    return {
        "title":                   rec.get("title", ""),
        "priority":                (rec.get("priority") or "LOW").upper(),
        "category":                rec.get("category", ""),
        "reason":                  rec.get("reason", ""),
        "expected_monthly_saving": rec.get("expected_monthly_saving", "$0"),
        "latency_improvement":     rec.get("latency_improvement", "0%"),
        "difficulty":              rec.get("difficulty", "Medium"),
        "implementation_time":     rec.get("implementation_time", "varies"),
    }


# ---------------------------------------------------------------------------
# Public generator
# ---------------------------------------------------------------------------

class RoadmapGenerator:
    """Convert rich recommendations into a phased optimization roadmap."""

    def generate(
        self,
        recommendations: list[dict],
        request: ReviewRequest,
    ) -> list[dict]:
        """Return a list of phase dicts sorted by phase number.

        Args:
            recommendations: Rich recommendation dicts from AdvancedRecommendationEngine.
            request:         The original ReviewRequest used to suppress solved items.

        Returns:
            List of up to 3 phase dicts, each containing:
                phase    int
                title    str
                timeline str
                tasks    list[dict]   — full task objects, HIGH before MEDIUM before LOW
        """
        buckets: dict[int, list[dict]] = {1: [], 2: [], 3: []}
        seen_titles: set[str] = set()

        for rec in recommendations:
            title = (rec.get("title") or "").strip()
            if not title:
                continue
            if title in seen_titles:
                continue
            if _already_solved(rec, request):
                continue

            phase = _assign_phase(rec)
            buckets[phase].append(_to_task(rec))
            seen_titles.add(title)

        result: list[dict] = []
        for phase_num in (1, 2, 3):
            tasks = buckets[phase_num]
            if not tasks:
                continue
            # Within each phase: HIGH first, then MEDIUM, then LOW
            tasks.sort(key=lambda t: _PRIORITY_ORDER.get(t["priority"], 99))
            result.append({
                **_PHASE_META[phase_num],
                "tasks": tasks,
            })

        return result
