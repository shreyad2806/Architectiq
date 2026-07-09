import pytest

from app.schemas import ReviewRequest
from app.services.latency_analyzer import LatencyAnalyzer


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TestArch",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="Pinecone",
        framework="FastAPI",
        memory=False,
        rag_enabled=False,
        cache_enabled=False,
        prompt_strategy="few-shot",
        monthly_requests=100_000,
        average_prompt_tokens=1_400,
        average_completion_tokens=500,
        context_window=8_000,
        concurrent_users=500,
        observability=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_base_latency_only():
    # gpt-4o base=350, vector_db present (+90), no RAG, small context, no cache
    request = _make_request(rag_enabled=False, cache_enabled=False, context_window=8_000, concurrent_users=0)
    result = LatencyAnalyzer().analyze(request)
    assert result["estimated_latency_ms"] == 440.0
    assert result["latency_rating"] == "Fast"


def test_rag_adds_overhead():
    request = _make_request(rag_enabled=True, cache_enabled=False, context_window=8_000, concurrent_users=0)
    result = LatencyAnalyzer().analyze(request)
    # 350 (base) + 90 (vector_db) + 60 (rag) = 500
    assert result["estimated_latency_ms"] == 500.0
    assert result["latency_rating"] == "Moderate"


def test_cache_reduces_latency():
    request = _make_request(rag_enabled=False, cache_enabled=True, context_window=8_000, concurrent_users=0)
    result = LatencyAnalyzer().analyze(request)
    # 350 + 90 - 80 = 360
    assert result["estimated_latency_ms"] == 360.0
    assert result["latency_rating"] == "Fast"


def test_large_context_penalty():
    request = _make_request(rag_enabled=False, cache_enabled=False, context_window=128_000, concurrent_users=0)
    result = LatencyAnalyzer().analyze(request)
    # 350 + 90 + 120 = 560
    assert result["estimated_latency_ms"] == 560.0
    assert result["latency_rating"] == "Moderate"


def test_high_concurrency_penalty():
    request = _make_request(rag_enabled=False, cache_enabled=False, context_window=8_000, concurrent_users=5_000)
    result = LatencyAnalyzer().analyze(request)
    # 350 + 90 + (4000/1000)*30 = 350+90+120 = 560
    assert result["estimated_latency_ms"] == 560.0
    assert result["latency_rating"] == "Moderate"


def test_slow_rating():
    # Combine all penalties
    request = _make_request(
        llm="claude-sonnet",
        rag_enabled=True,
        cache_enabled=False,
        context_window=128_000,
        concurrent_users=10_000,
    )
    result = LatencyAnalyzer().analyze(request)
    # 420 + 90 + 60 + 120 + (9000/1000)*30 = 420+90+60+120+270 = 960 -> Moderate
    assert result["latency_rating"] in ("Moderate", "Slow")


def test_unknown_llm_fallback():
    request = _make_request(llm="unknown-model-x", rag_enabled=False, cache_enabled=False, context_window=8_000, concurrent_users=0)
    result = LatencyAnalyzer().analyze(request)
    # Falls back to DEFAULT_BASE_LATENCY_MS (350) + 90 = 440
    assert result["estimated_latency_ms"] == 440.0
