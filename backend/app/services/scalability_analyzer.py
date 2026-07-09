"""ScalabilityAnalyzer service.

Evaluates the scalability of a production AI architecture based on
concurrent users, caching, vector DB, framework, and monthly traffic.
"""

from __future__ import annotations

from app.schemas import ReviewRequest


def _finding(severity: str, title: str, description: str, impact: str) -> dict:
    return {"severity": severity, "title": title, "description": description, "impact": impact}


# ---------------------------------------------------------------------------
# Scoring tables
# ---------------------------------------------------------------------------

# Points awarded for framework scalability tier (out of 25)
FRAMEWORK_SCORES: dict[str, int] = {
    "fastapi": 25,
    "flask": 15,
    "django": 18,
    "express": 22,
    "nestjs": 22,
    "spring": 22,
    "go": 25,
    "gin": 25,
    "actix": 25,
    "axum": 25,
    "rails": 12,
    "laravel": 12,
}
DEFAULT_FRAMEWORK_SCORE = 15

# Points awarded for vector DB scalability tier (out of 25)
VECTOR_DB_SCORES: dict[str, int] = {
    "pinecone": 25,
    "weaviate": 23,
    "qdrant": 23,
    "milvus": 22,
    "chroma": 15,
    "pgvector": 14,
    "faiss": 10,
    "sqlite-vss": 6,
}
DEFAULT_VECTOR_DB_SCORE = 10
NO_VECTOR_DB_SCORE = 5

# Cache bonus (out of 20)
CACHE_BONUS = 20

# Concurrent-users score (out of 20)
# Tiers: score reflects ability to handle that load well-designed
_USER_TIERS: list[tuple[int, int]] = [
    (50_000, 20),
    (10_000, 16),
    (5_000,  12),
    (1_000,   8),
    (0,       4),
]

# Monthly traffic score (out of 10)
_TRAFFIC_TIERS: list[tuple[int, int]] = [
    (10_000_000, 10),
    (1_000_000,   8),
    (100_000,     6),
    (10_000,      4),
    (0,           2),
]

# Expected capacity labels
_CAPACITY_LABELS: list[tuple[int, str]] = [
    (85, "Enterprise  (100k+ concurrent users)"),
    (70, "Large-scale (10k–100k concurrent users)"),
    (50, "Mid-scale   (1k–10k concurrent users)"),
    (0,  "Small-scale (<1k concurrent users)"),
]

# Scalability recommendation thresholds
_SCORE_THRESHOLD_FOR_CACHE_REC = 80
_SCORE_THRESHOLD_FOR_VDB_REC = 70


def _expected_capacity(score: int) -> str:
    for threshold, label in _CAPACITY_LABELS:
        if score >= threshold:
            return label
    return "Small-scale (<1k concurrent users)"


class ScalabilityAnalyzer:
    """Evaluate the scalability of an AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``scalability_score``, ``expected_capacity``, and ``recommendations``.

        Scoring breakdown (max 100):
            Concurrent users capacity   20
            Caching enabled             20
            Vector DB tier              25
            Framework tier              25
            Monthly traffic volume      10

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with ``scalability_score`` (int 0-100),
            ``expected_capacity`` (str), and ``recommendations`` (list[str]).
        """
        recommendations: list[str] = []
        findings: list[dict] = []
        score = 0

        # 1. Concurrent users
        users_score = self._users_component(request.concurrent_users)
        score += users_score
        if request.concurrent_users and request.concurrent_users >= 10_000:
            findings.append(_finding(
                "MEDIUM", "High Concurrent User Load",
                f"{request.concurrent_users:,} concurrent users demands horizontal scaling, connection pooling, and async processing to maintain throughput.",
                "Medium",
            ))

        # 2. Caching
        if request.cache_enabled:
            score += CACHE_BONUS
        else:
            recommendations.append(
                "Enable semantic or response caching to reduce repeated LLM calls "
                "and improve throughput under high concurrency."
            )
            findings.append(_finding(
                "HIGH", "No Caching Under High Traffic",
                "Without caching, every request hits the LLM, creating a linear scaling bottleneck and risk of exceeding provider rate limits.",
                "High",
            ))

        # 3. Vector DB
        vdb_score, vdb_rec = self._vector_db_component(request.vector_db)
        score += vdb_score
        if vdb_rec:
            recommendations.append(vdb_rec)
            if not request.vector_db:
                findings.append(_finding(
                    "MEDIUM", "No Vector Database",
                    "Absence of a vector database limits the ability to scale semantic search horizontally for growing knowledge bases.",
                    "Medium",
                ))
            else:
                findings.append(_finding(
                    "MEDIUM", "Suboptimal Vector Database",
                    f"'{request.vector_db}' is not designed for high-throughput production workloads and may become a bottleneck.",
                    "Medium",
                ))

        # 4. Framework
        fw_score, fw_rec = self._framework_component(request.framework)
        score += fw_score
        if fw_rec:
            recommendations.append(fw_rec)
            findings.append(_finding(
                "MEDIUM", "Framework Scalability Bottleneck",
                f"'{request.framework}' has limited async/concurrency support, which can become a throughput bottleneck under production load.",
                "Medium",
            ))

        # 5. Monthly traffic
        traffic_score = self._traffic_component(request.monthly_requests)
        score += traffic_score

        # High concurrency without cache is especially risky
        if request.concurrent_users and request.concurrent_users >= 10_000 and not request.cache_enabled:
            recommendations.append(
                "With 10k+ concurrent users, caching is critical to avoid LLM rate limits and latency spikes."
            )

        score = min(score, 100)

        return {
            "scalability_score": score,
            "expected_capacity": _expected_capacity(score),
            "recommendations": recommendations,
            "findings": findings,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _users_component(concurrent_users: int | None) -> int:
        if not concurrent_users:
            return 4
        for threshold, pts in _USER_TIERS:
            if concurrent_users >= threshold:
                return pts
        return 4

    @staticmethod
    def _vector_db_component(vector_db: str | None) -> tuple[int, str | None]:
        if not vector_db:
            return (
                NO_VECTOR_DB_SCORE,
                "No vector database configured. Add a managed vector store "
                "(e.g. Pinecone, Qdrant) to support scalable semantic search.",
            )
        key = vector_db.lower().strip()
        pts = VECTOR_DB_SCORES.get(key, DEFAULT_VECTOR_DB_SCORE)
        rec = None
        if pts < 15:
            rec = (
                f"'{vector_db}' is not optimised for high-throughput production workloads. "
                "Consider Pinecone, Qdrant, or Weaviate for horizontal scalability."
            )
        return pts, rec

    @staticmethod
    def _framework_component(framework: str | None) -> tuple[int, str | None]:
        if not framework:
            return DEFAULT_FRAMEWORK_SCORE, None
        key = framework.lower().strip()
        pts = FRAMEWORK_SCORES.get(key, DEFAULT_FRAMEWORK_SCORE)
        rec = None
        if pts < 18:
            rec = (
                f"'{framework}' has limited async support. Consider FastAPI, Express, "
                "or a Go/Rust framework for higher concurrency throughput."
            )
        return pts, rec

    @staticmethod
    def _traffic_component(monthly_requests: int | None) -> int:
        if not monthly_requests:
            return 2
        for threshold, pts in _TRAFFIC_TIERS:
            if monthly_requests >= threshold:
                return pts
        return 2
