import pytest

from app.schemas import ReviewRequest
from app.services.production_readiness_analyzer import ProductionReadinessAnalyzer


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TestArch",
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
        observability=False,
        authentication=False,
        rate_limiting=False,
        retry_strategy=False,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_all_features_enabled_is_perfect():
    request = _make_request(
        authentication=True,
        retry_strategy=True,
        rate_limiting=True,
        observability=True,
        cache_enabled=True,
        memory=True,
    )
    result = ProductionReadinessAnalyzer().analyze(request)
    assert result["score"] == 100
    assert result["grade"] == "A+"
    assert result["missing_features"] == []


def test_no_features_is_zero():
    request = _make_request()
    result = ProductionReadinessAnalyzer().analyze(request)
    assert result["score"] == 0
    assert result["grade"] == "C"
    assert len(result["missing_features"]) == 6


def test_partial_score_grade_a():
    # authentication(20) + retry(20) + observability(20) + rate_limiting(15) = 75 -> B
    # add cache(15) = 90 -> A
    request = _make_request(
        authentication=True,
        retry_strategy=True,
        observability=True,
        rate_limiting=True,
        cache_enabled=True,
    )
    result = ProductionReadinessAnalyzer().analyze(request)
    assert result["score"] == 90
    assert result["grade"] == "A"
    assert "Session memory or state management is present" in result["missing_features"]


def test_partial_score_grade_b():
    # authentication(20) + retry(20) + observability(20) = 60 -> B
    request = _make_request(
        authentication=True,
        retry_strategy=True,
        observability=True,
    )
    result = ProductionReadinessAnalyzer().analyze(request)
    assert result["score"] == 60
    assert result["grade"] == "B"


def test_missing_features_content():
    request = _make_request(authentication=True)
    result = ProductionReadinessAnalyzer().analyze(request)
    missing = result["missing_features"]
    assert "Retry and failover strategy is implemented" in missing
    assert "Rate limiting is enforced" in missing
    assert "Observability and tracing are configured" in missing
    assert "Response / semantic caching is enabled" in missing
    assert "Session memory or state management is present" in missing
    assert "API authentication is enabled" not in missing
