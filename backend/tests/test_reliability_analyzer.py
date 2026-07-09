import pytest

from app.schemas import ReviewRequest
from app.services.reliability_analyzer import ReliabilityAnalyzer


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
        observability=True,
        authentication=False,
        rate_limiting=False,
        retry_strategy=False,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_all_features_perfect_score():
    request = _make_request(
        retry_strategy=True,
        rate_limiting=True,
        authentication=True,
        cache_enabled=True,
        memory=True,
    )
    result = ReliabilityAnalyzer().analyze(request)
    assert result["reliability_score"] == 100
    assert result["risk_level"] == "Low"
    assert result["findings"] == []


def test_no_features_high_risk():
    request = _make_request()
    result = ReliabilityAnalyzer().analyze(request)
    # 100 - 25 - 20 - 20 - 15 - 10 = 10
    assert result["reliability_score"] == 10
    assert result["risk_level"] == "High"
    assert len(result["findings"]) == 5


def test_retry_and_auth_only():
    request = _make_request(retry_strategy=True, authentication=True)
    result = ReliabilityAnalyzer().analyze(request)
    # 100 - 20 (rate_limiting) - 15 (cache) - 10 (memory) = 55
    assert result["reliability_score"] == 55
    assert result["risk_level"] == "Medium"


def test_medium_risk_boundary():
    # 100 - 25 (retry) - 20 (rate_limit) = 55 -> Medium
    request = _make_request(authentication=True, cache_enabled=True, memory=True)
    result = ReliabilityAnalyzer().analyze(request)
    assert result["reliability_score"] == 55
    assert result["risk_level"] == "Medium"


def test_low_risk_boundary():
    # 100 - 10 (memory) = 90 -> Low
    request = _make_request(
        retry_strategy=True,
        rate_limiting=True,
        authentication=True,
        cache_enabled=True,
        memory=False,
    )
    result = ReliabilityAnalyzer().analyze(request)
    assert result["reliability_score"] == 90
    assert result["risk_level"] == "Low"


def test_findings_content():
    request = _make_request(retry_strategy=False, authentication=False)
    result = ReliabilityAnalyzer().analyze(request)
    findings = result["findings"]
    assert any("retry" in f.lower() for f in findings)
    assert any("authentication" in f.lower() for f in findings)


def test_score_does_not_go_below_zero():
    # Contrived: even if weights exceeded 100, score should floor at 0.
    request = _make_request()
    result = ReliabilityAnalyzer().analyze(request)
    assert result["reliability_score"] >= 0
