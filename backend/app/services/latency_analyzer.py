"""LatencyAnalyzer service for estimating AI request latency.

Uses simple additive scoring based on architecture characteristics
from a ReviewRequest.
"""

from __future__ import annotations

from app.schemas import ReviewRequest


# Base latency (ms) per LLM. Falls back to DEFAULT_BASE_LATENCY.
LLM_BASE_LATENCY_MS: dict[str, float] = {
    "gpt-4o": 350.0,
    "gpt-4o-mini": 200.0,
    "gpt-4.1": 300.0,
    "claude-sonnet": 420.0,
    "claude-sonnet-4": 400.0,
    "gemini-2.5-pro": 320.0,
    "llama3": 250.0,
}

DEFAULT_BASE_LATENCY_MS = 350.0

# Vector DB lookup overhead (ms)
VECTOR_DB_LATENCY_MS = 90.0

# Extra overhead when RAG pipeline is active (retrieval + reranking)
RAG_OVERHEAD_MS = 60.0

# Penalty when context window usage is large (> 32k tokens)
LARGE_CONTEXT_THRESHOLD = 32_000
LARGE_CONTEXT_PENALTY_MS = 120.0

# Reduction from semantic / response caching
CACHE_SAVING_MS = 80.0

# Concurrency degradation: per 1000 concurrent users above threshold
CONCURRENCY_THRESHOLD = 1_000
CONCURRENCY_PENALTY_PER_1K_MS = 30.0

# Rating thresholds (ms)
FAST_THRESHOLD_MS = 500.0
MODERATE_THRESHOLD_MS = 1_000.0


class LatencyAnalyzer:
    """Estimate average request latency for a production AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``estimated_latency_ms`` and a ``latency_rating``.

        Calculation (additive scoring):
            base latency (LLM)
            + vector DB lookup       (if vector_db present)
            + RAG overhead           (if rag_enabled)
            + large context penalty  (if context_window > 32k)
            + concurrency penalty    (per 1k users above threshold)
            - cache saving           (if cache_enabled)

        Rating:
            Fast     < 500 ms
            Moderate < 1000 ms
            Slow     >= 1000 ms
        """
        latency = self._base_latency(request.llm)
        latency += self._vector_db_component(request)
        latency += self._rag_component(request)
        latency += self._context_component(request)
        latency += self._concurrency_component(request)
        latency -= self._cache_saving(request)

        estimated = round(max(latency, 0.0), 2)
        return {
            "estimated_latency_ms": estimated,
            "latency_rating": self._rating(estimated),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _base_latency(llm: str) -> float:
        return LLM_BASE_LATENCY_MS.get(llm.lower().strip(), DEFAULT_BASE_LATENCY_MS)

    @staticmethod
    def _vector_db_component(request: ReviewRequest) -> float:
        return VECTOR_DB_LATENCY_MS if request.vector_db else 0.0

    @staticmethod
    def _rag_component(request: ReviewRequest) -> float:
        return RAG_OVERHEAD_MS if request.rag_enabled else 0.0

    @staticmethod
    def _context_component(request: ReviewRequest) -> float:
        if request.context_window and request.context_window > LARGE_CONTEXT_THRESHOLD:
            return LARGE_CONTEXT_PENALTY_MS
        return 0.0

    @staticmethod
    def _concurrency_component(request: ReviewRequest) -> float:
        if not request.concurrent_users:
            return 0.0
        excess_users = max(request.concurrent_users - CONCURRENCY_THRESHOLD, 0)
        return (excess_users / 1_000) * CONCURRENCY_PENALTY_PER_1K_MS

    @staticmethod
    def _cache_saving(request: ReviewRequest) -> float:
        return CACHE_SAVING_MS if request.cache_enabled else 0.0

    @staticmethod
    def _rating(latency_ms: float) -> str:
        if latency_ms < FAST_THRESHOLD_MS:
            return "Fast"
        if latency_ms < MODERATE_THRESHOLD_MS:
            return "Moderate"
        return "Slow"
