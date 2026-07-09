import pytest

from app.schemas import ReviewRequest
from app.services.recommendation_engine import RecommendationEngine, _PRIORITY_ORDER


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TestArch",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="Pinecone",
        framework="FastAPI",
        memory=True,
        rag_enabled=True,
        cache_enabled=True,
        prompt_strategy="few-shot",
        monthly_requests=100_000,
        average_prompt_tokens=1_400,
        average_completion_tokens=500,
        context_window=128_000,
        concurrent_users=5_000,
        observability=True,
        logging=True,
        monitoring=True,
        tracing=True,
        metrics=True,
        health_endpoint=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
        prompt_injection_protection=True,
        input_validation=True,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_no_findings_for_fully_featured_arch():
    request = _make_request()
    recs = RecommendationEngine().generate(request)
    # gpt-4o still has cost savings potential → may have 1 dynamic rec
    # but no static catalogue entries should fire
    static_titles = {r["title"] for r in recs}
    for entry_title in [
        "Enable API Authentication",
        "Enforce Rate Limiting",
        "Implement Retry and Failover Strategy",
        "Enable Semantic Caching",
    ]:
        assert entry_title not in static_titles


def test_bare_arch_generates_many_recs():
    request = _make_request(
        authentication=False,
        rate_limiting=False,
        retry_strategy=False,
        cache_enabled=False,
        memory=False,
        rag_enabled=False,
        observability=False,
        logging=False,
        monitoring=False,
        tracing=False,
        metrics=False,
        health_endpoint=False,
        prompt_injection_protection=False,
        input_validation=False,
    )
    recs = RecommendationEngine().generate(request)
    assert len(recs) >= 8


def test_sorted_by_priority():
    request = _make_request(
        authentication=False,
        rate_limiting=False,
        logging=False,
        metrics=False,
    )
    recs = RecommendationEngine().generate(request)
    priorities = [r["priority"] for r in recs]
    order_values = [_PRIORITY_ORDER[p] for p in priorities]
    assert order_values == sorted(order_values), "Recommendations not sorted by priority"


def test_required_fields_present():
    request = _make_request(authentication=False)
    recs = RecommendationEngine().generate(request)
    assert len(recs) > 0
    for rec in recs:
        assert "priority" in rec
        assert "title" in rec
        assert "description" in rec
        assert "estimated_monthly_saving" in rec
        assert "estimated_latency_improvement" in rec
        assert "estimated_score_improvement" in rec


def test_priority_values_valid():
    request = _make_request(authentication=False, cache_enabled=False, metrics=False)
    recs = RecommendationEngine().generate(request)
    for rec in recs:
        assert rec["priority"] in ("HIGH", "MEDIUM", "LOW")


def test_cache_rec_present_when_disabled():
    request = _make_request(cache_enabled=False)
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert "Enable Semantic Caching" in titles


def test_dynamic_cost_rec_for_expensive_model():
    request = _make_request(llm="gpt-4o", monthly_requests=1_000_000)
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert "Switch to a More Cost-Efficient LLM" in titles


def test_no_duplicate_titles():
    request = _make_request(
        authentication=False,
        cache_enabled=False,
        retry_strategy=False,
    )
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert len(titles) == len(set(titles)), "Duplicate recommendation titles found"
