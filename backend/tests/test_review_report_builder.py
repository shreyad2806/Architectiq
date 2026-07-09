import pytest

from app.schemas import ReviewRequest
from app.services.review_report_builder import ReviewReportBuilder


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TalentLens",
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


_REQUIRED_SECTIONS = [
    "report_id",
    "generated_at",
    "project_name",
    "architecture_score",
    "production_readiness",
    "cost_analysis",
    "latency_analysis",
    "security_analysis",
    "reliability_analysis",
    "scalability_analysis",
    "observability_analysis",
    "rag_analysis",
    "top_findings",
    "recommendations",
    "executive_summary",
]


def test_all_sections_present():
    report = ReviewReportBuilder().build(_make_request())
    for section in _REQUIRED_SECTIONS:
        assert section in report, f"Missing section: {section}"


def test_architecture_score_structure():
    report = ReviewReportBuilder().build(_make_request())
    score_section = report["architecture_score"]
    assert "overall_score" in score_section
    assert "grade" in score_section
    assert "dimension_scores" in score_section
    assert 0 <= score_section["overall_score"] <= 100
    assert score_section["grade"] in ("Excellent", "Good", "Average", "Poor")


def test_production_readiness_structure():
    report = ReviewReportBuilder().build(_make_request())
    pr = report["production_readiness"]
    assert "score" in pr
    assert "grade" in pr
    assert "missing_features" in pr
    assert isinstance(pr["missing_features"], list)


def test_cost_analysis_structure():
    report = ReviewReportBuilder().build(_make_request())
    ca = report["cost_analysis"]
    assert "estimated_monthly_tokens" in ca
    assert "estimated_monthly_cost" in ca
    assert "potential_monthly_savings" in ca
    assert ca["currency"] == "USD"
    assert ca["estimated_monthly_tokens"] > 0


def test_latency_analysis_structure():
    report = ReviewReportBuilder().build(_make_request())
    la = report["latency_analysis"]
    assert "estimated_latency_ms" in la
    assert la["latency_rating"] in ("Fast", "Moderate", "Slow")


def test_security_analysis_structure():
    report = ReviewReportBuilder().build(_make_request())
    sa = report["security_analysis"]
    assert "security_score" in sa
    assert "severity" in sa
    assert sa["severity"] in ("INFO", "WARNING", "CRITICAL")
    assert isinstance(sa["security_findings"], list)
    assert isinstance(sa["recommendations"], list)


def test_reliability_structure():
    report = ReviewReportBuilder().build(_make_request())
    ra = report["reliability_analysis"]
    assert ra["risk_level"] in ("Low", "Medium", "High")


def test_scalability_structure():
    report = ReviewReportBuilder().build(_make_request())
    sc = report["scalability_analysis"]
    assert "scalability_score" in sc
    assert "expected_capacity" in sc


def test_observability_structure():
    report = ReviewReportBuilder().build(_make_request())
    ob = report["observability_analysis"]
    assert "observability_score" in ob
    assert isinstance(ob["missing_features"], list)


def test_rag_structure():
    report = ReviewReportBuilder().build(_make_request())
    rag = report["rag_analysis"]
    assert "rag_score" in rag
    assert rag["retrieval_quality"] in ("Excellent", "Good", "Fair", "Poor")


def test_top_findings_severity_sorted():
    request = _make_request(
        authentication=False,
        retry_strategy=False,
        logging=False,
        metrics=False,
    )
    report = ReviewReportBuilder().build(request)
    findings = report["top_findings"]
    _order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    severities = [_order[f["severity"]] for f in findings]
    assert severities == sorted(severities)


def test_recommendations_sorted_by_priority():
    request = _make_request(
        authentication=False,
        cache_enabled=False,
        logging=False,
    )
    report = ReviewReportBuilder().build(request)
    _order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    priorities = [_order[r["priority"]] for r in report["recommendations"]]
    assert priorities == sorted(priorities)


def test_executive_summary_non_empty():
    report = ReviewReportBuilder().build(_make_request())
    summary = report["executive_summary"]
    assert isinstance(summary, str)
    assert len(summary) > 50
    assert "TalentLens" in summary


def test_report_id_unique():
    r1 = ReviewReportBuilder().build(_make_request())
    r2 = ReviewReportBuilder().build(_make_request())
    assert r1["report_id"] != r2["report_id"]


def test_project_name_in_report():
    report = ReviewReportBuilder().build(_make_request())
    assert report["project_name"] == "TalentLens"
