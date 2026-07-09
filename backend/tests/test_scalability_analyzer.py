import pytest

from app.schemas import ReviewRequest
from app.services.scalability_analyzer import ScalabilityAnalyzer


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TestArch",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="Pinecone",
        framework="FastAPI",
        memory=False,
        rag_enabled=True,
        cache_enabled=True,
        prompt_strategy="few-shot",
        monthly_requests=1_000_000,
        average_prompt_tokens=1_400,
        average_completion_tokens=500,
        context_window=128_000,
        concurrent_users=50_000,
        observability=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_top_tier_stack_high_score():
    """FastAPI + Pinecone + cache + high traffic + 50k users => Enterprise."""
    request = _make_request()
    result = ScalabilityAnalyzer().analyze(request)
    # 20 (users) + 20 (cache) + 25 (pinecone) + 25 (fastapi) + 8 (1M traffic) = 98 -> capped 100
    assert result["scalability_score"] >= 90
    assert result["expected_capacity"].startswith("Enterprise")
    assert result["recommendations"] == []


def test_no_cache_recommendation():
    request = _make_request(cache_enabled=False, concurrent_users=500)
    result = ScalabilityAnalyzer().analyze(request)
    assert any("cach" in r.lower() for r in result["recommendations"])


def test_no_vector_db_recommendation():
    request = _make_request(vector_db="")
    result = ScalabilityAnalyzer().analyze(request)
    assert any("vector" in r.lower() for r in result["recommendations"])


def test_low_tier_framework_recommendation():
    request = _make_request(framework="rails")
    result = ScalabilityAnalyzer().analyze(request)
    assert any("rails" in r.lower() for r in result["recommendations"])


def test_high_concurrency_no_cache_extra_warning():
    request = _make_request(concurrent_users=15_000, cache_enabled=False)
    result = ScalabilityAnalyzer().analyze(request)
    recs = " ".join(result["recommendations"]).lower()
    assert "10k" in recs or "caching" in recs or "cache" in recs


def test_small_scale_capacity():
    request = _make_request(
        concurrent_users=200,
        cache_enabled=False,
        vector_db="sqlite-vss",
        framework="rails",
        monthly_requests=5_000,
    )
    result = ScalabilityAnalyzer().analyze(request)
    assert result["expected_capacity"].startswith("Small-scale")


def test_score_capped_at_100():
    request = _make_request()
    result = ScalabilityAnalyzer().analyze(request)
    assert result["scalability_score"] <= 100


def test_mid_scale_capacity():
    request = _make_request(
        concurrent_users=3_000,
        cache_enabled=True,
        vector_db="chroma",
        framework="fastapi",
        monthly_requests=200_000,
    )
    result = ScalabilityAnalyzer().analyze(request)
    # 8 (3k users) + 20 (cache) + 15 (chroma) + 25 (fastapi) + 6 (200k traffic) = 74 -> Large-scale
    assert result["scalability_score"] == 74
    assert result["expected_capacity"].startswith("Large-scale")
