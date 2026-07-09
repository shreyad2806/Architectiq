import pytest

from app.schemas import ReviewRequest
from app.services.security_analyzer import SecurityAnalyzer


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
        retry_strategy=True,
        prompt_injection_protection=False,
        input_validation=False,
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


def test_all_controls_perfect_score():
    request = _make_request(
        authentication=True,
        rate_limiting=True,
        prompt_injection_protection=True,
        input_validation=True,
    )
    result = SecurityAnalyzer().analyze(request)
    assert result["security_score"] == 100
    assert result["security_findings"] == []
    assert result["recommendations"] == []


def test_no_controls_zero_score():
    request = _make_request()
    result = SecurityAnalyzer().analyze(request)
    # 100 - 35 - 25 - 25 - 15 = 0
    assert result["security_score"] == 0
    assert len(result["security_findings"]) == 4
    assert len(result["recommendations"]) == 4


def test_auth_only():
    request = _make_request(authentication=True)
    result = SecurityAnalyzer().analyze(request)
    # 100 - 25 - 25 - 15 = 35
    assert result["security_score"] == 35


def test_auth_and_rate_limit():
    request = _make_request(authentication=True, rate_limiting=True)
    result = SecurityAnalyzer().analyze(request)
    # 100 - 25 - 15 = 60
    assert result["security_score"] == 60


def test_findings_content():
    request = _make_request(authentication=False, rate_limiting=False)
    result = SecurityAnalyzer().analyze(request)
    findings = " ".join(result["security_findings"]).lower()
    assert "authentication" in findings
    assert "rate limit" in findings


def test_recommendations_content():
    request = _make_request(prompt_injection_protection=False, input_validation=False)
    result = SecurityAnalyzer().analyze(request)
    recs = " ".join(result["recommendations"]).lower()
    assert "prompt" in recs or "injection" in recs
    assert "validation" in recs


def test_score_does_not_go_below_zero():
    request = _make_request()
    result = SecurityAnalyzer().analyze(request)
    assert result["security_score"] >= 0


def test_findings_and_recs_parallel():
    """findings and recommendations should have same length."""
    request = _make_request()
    result = SecurityAnalyzer().analyze(request)
    assert len(result["security_findings"]) == len(result["recommendations"])
