import pytest

from app.schemas import ReviewRequest
from app.services.rag_analyzer import RagAnalyzer


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TestRAG",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="Pinecone",
        framework="FastAPI",
        memory=False,
        rag_enabled=True,
        cache_enabled=False,
        prompt_strategy="few-shot",
        monthly_requests=100_000,
        average_prompt_tokens=1_400,
        average_completion_tokens=500,
        context_window=128_000,
        concurrent_users=5_000,
        observability=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_no_vector_db_low_score():
    """No vector DB configured should yield a very low score."""
    request = _make_request(vector_db="", rag_enabled=False, cache_enabled=False, context_window=4_000)
    result = RagAnalyzer().analyze(request)
    assert result["rag_score"] <= 30
    assert result["retrieval_quality"] == "Poor"
    assert any("vector" in r.lower() for r in result["recommendations"])


def test_high_quality_stack_excellent():
    """Pinecone + BGE-large + large context + cache should score very high."""
    request = _make_request(
        embedding_model="bge-large",
        vector_db="pinecone",
        rag_enabled=True,
        cache_enabled=True,
        context_window=128_000,
    )
    result = RagAnalyzer().analyze(request)
    assert result["rag_score"] >= 90
    assert result["retrieval_quality"] == "Excellent"
    assert result["recommendations"] == []


def test_rag_disabled_recommendation():
    request = _make_request(rag_enabled=False)
    result = RagAnalyzer().analyze(request)
    assert any("RAG" in r for r in result["recommendations"])


def test_cache_disabled_recommendation():
    request = _make_request(cache_enabled=False)
    result = RagAnalyzer().analyze(request)
    assert any("cach" in r.lower() for r in result["recommendations"])


def test_low_tier_embedding_recommendation():
    request = _make_request(embedding_model="text-embedding-ada-002")
    result = RagAnalyzer().analyze(request)
    assert any("embedding" in r.lower() for r in result["recommendations"])


def test_basic_vector_db_recommendation():
    request = _make_request(vector_db="faiss")
    result = RagAnalyzer().analyze(request)
    assert any("faiss" in r.lower() for r in result["recommendations"])


def test_score_capped_at_100():
    request = _make_request(
        embedding_model="bge-large",
        vector_db="pinecone",
        rag_enabled=True,
        cache_enabled=True,
        context_window=128_000,
    )
    result = RagAnalyzer().analyze(request)
    assert result["rag_score"] <= 100


def test_small_context_window_recommendation():
    request = _make_request(context_window=2_000)
    result = RagAnalyzer().analyze(request)
    assert any("context" in r.lower() for r in result["recommendations"])
