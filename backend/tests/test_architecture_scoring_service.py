import pytest

from app.schemas import ReviewRequest
from app.services.architecture_scoring_service import (
    ArchitectureScoringService,
    WEIGHTS,
    _grade,
    _latency_to_score,
    _cost_to_score,
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


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_grade_thresholds():
    assert _grade(100) == "Excellent"
    assert _grade(85)  == "Excellent"
    assert _grade(84)  == "Good"
    assert _grade(70)  == "Good"
    assert _grade(69)  == "Average"
    assert _grade(50)  == "Average"
    assert _grade(49)  == "Poor"
    assert _grade(0)   == "Poor"


def test_latency_to_score_bounds():
    assert _latency_to_score(0) == 100
    assert _latency_to_score(2_000) == 0
    assert 0 <= _latency_to_score(500) <= 100


def test_cost_to_score_bounds():
    assert _cost_to_score(0) == 100
    assert _cost_to_score(10_000) == 0
    assert 0 <= _cost_to_score(500) <= 100


def test_fully_featured_architecture_excellent():
    request = _make_request()
    result = ArchitectureScoringService().analyze(request)
    assert result["overall_score"] >= 70
    assert result["grade"] in ("Excellent", "Good")
    assert set(result["dimension_scores"].keys()) == set(WEIGHTS.keys())


def test_bare_minimum_architecture_poor():
    request = _make_request(
        memory=False,
        rag_enabled=False,
        cache_enabled=False,
        logging=False,
        monitoring=False,
        tracing=False,
        metrics=False,
        health_endpoint=False,
        authentication=False,
        rate_limiting=False,
        retry_strategy=False,
        prompt_injection_protection=False,
        input_validation=False,
        observability=False,
    )
    result = ArchitectureScoringService().analyze(request)
    assert result["overall_score"] < 70
    assert result["grade"] in ("Poor", "Average")


def test_dimension_scores_all_present():
    request = _make_request()
    result = ArchitectureScoringService().analyze(request)
    for dim in WEIGHTS:
        assert dim in result["dimension_scores"]
        assert 0 <= result["dimension_scores"][dim] <= 100


def test_overall_score_bounded():
    request = _make_request()
    result = ArchitectureScoringService().analyze(request)
    assert 0 <= result["overall_score"] <= 100
