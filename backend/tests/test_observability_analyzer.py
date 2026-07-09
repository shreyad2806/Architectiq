import pytest

from app.schemas import ReviewRequest
from app.services.observability_analyzer import ObservabilityAnalyzer


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
        logging=False,
        monitoring=False,
        tracing=False,
        metrics=False,
        health_endpoint=False,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
        prompt_injection_protection=False,
        input_validation=False,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_all_pillars_perfect_score():
    request = _make_request(
        logging=True,
        monitoring=True,
        tracing=True,
        metrics=True,
        health_endpoint=True,
    )
    result = ObservabilityAnalyzer().analyze(request)
    assert result["observability_score"] == 100
    assert result["missing_features"] == []
    assert result["recommendations"] == []


def test_no_pillars_zero_score():
    request = _make_request()
    result = ObservabilityAnalyzer().analyze(request)
    # 100 - 25 - 25 - 20 - 20 - 10 = 0
    assert result["observability_score"] == 0
    assert len(result["missing_features"]) == 5
    assert len(result["recommendations"]) == 5


def test_logging_only():
    request = _make_request(logging=True)
    result = ObservabilityAnalyzer().analyze(request)
    # 100 - 25 - 20 - 20 - 10 = 25
    assert result["observability_score"] == 25
    assert "Structured logging" not in result["missing_features"]
    assert "Monitoring solution" in result["missing_features"]


def test_logging_and_monitoring():
    request = _make_request(logging=True, monitoring=True)
    result = ObservabilityAnalyzer().analyze(request)
    # 100 - 20 - 20 - 10 = 50
    assert result["observability_score"] == 50


def test_missing_health_endpoint():
    request = _make_request(logging=True, monitoring=True, tracing=True, metrics=True)
    result = ObservabilityAnalyzer().analyze(request)
    # 100 - 10 = 90
    assert result["observability_score"] == 90
    assert "Health check endpoint" in result["missing_features"]


def test_recommendations_match_missing_features():
    request = _make_request()
    result = ObservabilityAnalyzer().analyze(request)
    assert len(result["missing_features"]) == len(result["recommendations"])


def test_score_floor_zero():
    request = _make_request()
    result = ObservabilityAnalyzer().analyze(request)
    assert result["observability_score"] >= 0


def test_recommendation_content():
    request = _make_request(tracing=False, health_endpoint=False)
    result = ObservabilityAnalyzer().analyze(request)
    recs = " ".join(result["recommendations"]).lower()
    assert "tracing" in recs
    assert "health" in recs
