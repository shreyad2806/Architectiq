import pytest

from app.schemas import ReviewRequest
from app.services.recommendation_engine import (
    AdvancedRecommendationEngine,
    RecommendationEngine,
    _PRIORITY_ORDER,
)


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


# ---------------------------------------------------------------------------
# RecommendationEngine (legacy) tests
# ---------------------------------------------------------------------------

def test_no_security_recs_for_fully_featured_arch():
    request = _make_request()
    recs = RecommendationEngine().generate(request)
    titles = {r["title"] for r in recs}
    assert "Enforce API Authentication (OAuth 2.0 / JWT)" not in titles
    assert "Add Per-User Rate Limiting" not in titles
    assert "Implement Exponential Backoff Retry Strategy" not in titles
    assert "Enable Semantic Caching" not in titles


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


def test_model_switch_rec_for_expensive_model_high_traffic():
    request = _make_request(llm="gpt-4o", monthly_requests=1_000_000)
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert any("GPT-4o Mini" in t for t in titles)


def test_no_duplicate_titles():
    request = _make_request(
        authentication=False,
        cache_enabled=False,
        retry_strategy=False,
    )
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert len(titles) == len(set(titles)), "Duplicate recommendation titles found"


# ---------------------------------------------------------------------------
# AdvancedRecommendationEngine tests
# ---------------------------------------------------------------------------

def test_advanced_output_shape():
    request = _make_request(authentication=False, cache_enabled=False)
    result = AdvancedRecommendationEngine().generate(request)
    assert "executive_summary" in result
    assert "total_estimated_monthly_savings" in result
    assert "estimated_latency_improvement" in result
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


def test_advanced_recommendation_rich_fields():
    request = _make_request(authentication=False)
    result = AdvancedRecommendationEngine().generate(request)
    for rec in result["recommendations"]:
        assert "priority" in rec
        assert "category" in rec
        assert "title" in rec
        assert "reason" in rec
        assert "expected_monthly_saving" in rec
        assert "latency_improvement" in rec
        assert "quality_improvement" in rec
        assert "difficulty" in rec
        assert "implementation_time" in rec


def test_advanced_category_values():
    request = _make_request(
        authentication=False, cache_enabled=False, logging=False,
        retry_strategy=False, rag_enabled=False,
    )
    result = AdvancedRecommendationEngine().generate(request)
    valid_categories = {
        "Cost Optimization", "RAG Optimization", "Performance",
        "Reliability", "Security", "Observability",
    }
    for rec in result["recommendations"]:
        assert rec["category"] in valid_categories, f"Unknown category: {rec['category']}"


def test_advanced_sorted_by_priority():
    request = _make_request(
        authentication=False, rate_limiting=False, cache_enabled=False,
        logging=False, metrics=False,
    )
    result = AdvancedRecommendationEngine().generate(request)
    priorities = [r["priority"] for r in result["recommendations"]]
    order_values = [_PRIORITY_ORDER[p] for p in priorities]
    assert order_values == sorted(order_values)


def test_advanced_no_duplicate_titles():
    request = _make_request(
        authentication=False, cache_enabled=False, retry_strategy=False,
        logging=False, monitoring=False,
    )
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert len(titles) == len(set(titles))


def test_advanced_executive_summary_mentions_project():
    request = _make_request(project_name="Acme RAG System", authentication=False)
    result = AdvancedRecommendationEngine().generate(request)
    assert "Acme RAG System" in result["executive_summary"]


def test_advanced_savings_string_format():
    request = _make_request(cache_enabled=False, llm="gpt-4o", monthly_requests=500_000)
    result = AdvancedRecommendationEngine().generate(request)
    assert result["total_estimated_monthly_savings"].startswith("$")


def test_advanced_latency_improvement_string_format():
    request = _make_request(cache_enabled=False)
    result = AdvancedRecommendationEngine().generate(request)
    assert result["estimated_latency_improvement"].endswith("%")


def test_advanced_no_recs_not_needed():
    """For a best-practice architecture, security/reliability recs must not fire."""
    request = _make_request(
        authentication=True, rate_limiting=True, retry_strategy=True,
        prompt_injection_protection=True, input_validation=True,
        logging=True, monitoring=True, tracing=True, metrics=True,
        health_endpoint=True, cache_enabled=True,
        llm="gpt-4o-mini",
        rag_enabled=False,
        vector_db="",
        context_window=4_000,
        monthly_requests=10_000,
    )
    result = AdvancedRecommendationEngine().generate(request)
    titles = {r["title"] for r in result["recommendations"]}
    assert "Enforce API Authentication (OAuth 2.0 / JWT)" not in titles
    assert "Add Per-User Rate Limiting" not in titles
    assert "Enable Semantic Caching" not in titles


def test_advanced_context_window_rec_fires():
    request = _make_request(context_window=16_000)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert "Reduce Context Window Size" in titles


def test_advanced_vdb_migration_rec():
    request = _make_request(vector_db="chroma", rag_enabled=True)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert any("chroma" in t.lower() for t in titles)


def test_advanced_hybrid_search_rec_when_rag():
    request = _make_request(rag_enabled=True)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert "Add Hybrid Search (Dense + Sparse Retrieval)" in titles


def test_advanced_model_routing_for_very_high_traffic():
    request = _make_request(llm="gpt-4o", monthly_requests=600_000)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert "Implement Intelligent Model Routing" in titles
