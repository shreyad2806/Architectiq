"""RagAnalyzer service.

Evaluates RAG pipeline quality based on architecture characteristics
from a ReviewRequest and returns a rag_score, retrieval_quality label,
and actionable recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ReviewRequest


def _finding(severity: str, title: str, description: str, impact: str) -> dict:
    return {"severity": severity, "title": title, "description": description, "impact": impact}


# ---------------------------------------------------------------------------
# Scoring tables
# ---------------------------------------------------------------------------

# Points awarded for embedding model tier (out of 30)
EMBEDDING_SCORES: dict[str, int] = {
    # High-quality dedicated embedding models
    "text-embedding-3-large": 30,
    "bge-large": 30,
    "bge-m3": 30,
    "e5-large": 28,
    "e5-mistral-7b": 28,
    # Mid-tier
    "text-embedding-3-small": 22,
    "bge-base": 22,
    "e5-base": 20,
    # Lower-tier / general-purpose
    "text-embedding-ada-002": 15,
    "text-embedding-002": 15,
}
DEFAULT_EMBEDDING_SCORE = 10  # unknown / generic

# Points awarded for vector database tier (out of 30)
VECTOR_DB_SCORES: dict[str, int] = {
    "pinecone": 30,
    "weaviate": 28,
    "qdrant": 28,
    "milvus": 26,
    "chroma": 22,
    "pgvector": 18,
    "faiss": 15,
    "sqlite-vss": 10,
}
DEFAULT_VECTOR_DB_SCORE = 5   # unknown / missing

# Context window bonus: larger windows allow retrieving more chunks (out of 20)
CONTEXT_WINDOW_SCORES: list[tuple[int, int]] = [
    (128_000, 20),
    (32_000,  15),
    (16_000,  10),
    (8_000,    5),
]
DEFAULT_CONTEXT_SCORE = 2

# Cache bonus (out of 10)
CACHE_BONUS = 10

# RAG enabled baseline bonus (out of 10)
RAG_ENABLED_BONUS = 10

# Retrieval quality thresholds
_QUALITY_LABELS: list[tuple[int, str]] = [
    (85, "Excellent"),
    (70, "Good"),
    (50, "Fair"),
    (0,  "Poor"),
]


def _retrieval_quality(score: int) -> str:
    for threshold, label in _QUALITY_LABELS:
        if score >= threshold:
            return label
    return "Poor"


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class RagAnalyzer:
    """Evaluate the RAG pipeline quality of an AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``rag_score``, ``retrieval_quality``, and ``recommendations``.

        Scoring breakdown (max 100):
            RAG enabled presence    10
            Embedding model tier    30
            Vector DB tier          30
            Context window size     20
            Caching enabled         10

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with ``rag_score`` (int 0-100),
            ``retrieval_quality`` (str), and ``recommendations`` (list[str]).
        """
        recommendations: list[str] = []
        findings: list[dict] = []
        score = 0

        # 1. RAG enabled baseline
        if request.rag_enabled:
            score += RAG_ENABLED_BONUS
        else:
            recommendations.append(
                "Enable RAG to ground responses in your knowledge base and reduce hallucinations."
            )
            findings.append(_finding(
                "HIGH", "RAG Pipeline Disabled",
                "Retrieval-Augmented Generation is not enabled. Without RAG the LLM relies solely on training data, increasing hallucination risk for domain-specific queries.",
                "High",
            ))

        # 2. Embedding model
        embedding_score, emb_rec = self._embedding_component(request.embedding_model)
        score += embedding_score
        if emb_rec:
            recommendations.append(emb_rec)
            findings.append(_finding(
                "MEDIUM", "Weak Embedding Model",
                f"The embedding model '{request.embedding_model}' is lower-tier and may produce less accurate similarity matches, reducing retrieval quality.",
                "Medium",
            ))

        # 3. Vector database
        vdb_score, vdb_rec = self._vector_db_component(request.vector_db)
        score += vdb_score
        if vdb_rec:
            recommendations.append(vdb_rec)
            if not request.vector_db:
                findings.append(_finding(
                    "HIGH", "No Vector Database Configured",
                    "Without a vector store there is no semantic retrieval capability. RAG requires a vector database to index and query embeddings.",
                    "High",
                ))
            else:
                findings.append(_finding(
                    "MEDIUM", "Basic Vector Store in Use",
                    f"'{request.vector_db}' is not optimised for production-scale ANN queries. This may become a bottleneck under high retrieval load.",
                    "Medium",
                ))

        # 4. Context window
        ctx_score, ctx_rec = self._context_component(request.context_window)
        score += ctx_score
        if ctx_rec:
            recommendations.append(ctx_rec)
            findings.append(_finding(
                "MEDIUM", "Small Context Window Limits Retrieval",
                "A small context window restricts how many chunks can be retrieved and included per request, limiting answer completeness.",
                "Medium",
            ))

        # 5. Caching
        if request.cache_enabled:
            score += CACHE_BONUS
        else:
            recommendations.append(
                "Enable semantic caching to reduce redundant retrieval calls and lower latency."
            )
            findings.append(_finding(
                "LOW", "No Retrieval Cache",
                "Repeated similar queries trigger full vector DB lookups every time. Semantic caching would reduce latency and retrieval costs.",
                "Low",
            ))

        score = min(score, 100)

        return {
            "rag_score": score,
            "retrieval_quality": _retrieval_quality(score),
            "recommendations": recommendations,
            "findings": findings,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _embedding_component(embedding_model: str | None) -> tuple[int, str | None]:
        if not embedding_model:
            return (
                DEFAULT_EMBEDDING_SCORE,
                "Specify a dedicated embedding model (e.g. text-embedding-3-large or BGE-large) for higher retrieval quality.",
            )
        key = embedding_model.lower().strip()
        pts = EMBEDDING_SCORES.get(key, DEFAULT_EMBEDDING_SCORE)
        rec = None
        if pts < 22:
            rec = (
                f"Consider upgrading from '{embedding_model}' to a higher-quality embedding model "
                "such as text-embedding-3-large or BGE-large for better retrieval accuracy."
            )
        return pts, rec

    @staticmethod
    def _vector_db_component(vector_db: str | None) -> tuple[int, str | None]:
        if not vector_db:
            return (
                0,
                "No vector database configured. Add a vector store (e.g. Pinecone, Qdrant, Weaviate) to enable semantic retrieval.",
            )
        key = vector_db.lower().strip()
        pts = VECTOR_DB_SCORES.get(key, DEFAULT_VECTOR_DB_SCORE)
        rec = None
        if pts < 22:
            rec = (
                f"'{vector_db}' is a basic vector store. Consider Pinecone, Qdrant, or Weaviate "
                "for production-grade ANN indexing and filtering."
            )
        return pts, rec

    @staticmethod
    def _context_component(context_window: int | None) -> tuple[int, str | None]:
        if not context_window:
            return DEFAULT_CONTEXT_SCORE, "Specify a context_window to allow retrieval of more document chunks."
        for threshold, pts in CONTEXT_WINDOW_SCORES:
            if context_window >= threshold:
                return pts, None
        rec = "Use a model with a larger context window (≥ 8k tokens) to retrieve more relevant chunks."
        return DEFAULT_CONTEXT_SCORE, rec
