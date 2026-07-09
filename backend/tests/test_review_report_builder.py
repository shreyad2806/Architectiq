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
    "intelligence_summary",
    "audit_report",
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


def test_intelligence_summary_structure():
    report = ReviewReportBuilder().build(_make_request())
    intel = report["intelligence_summary"]
    assert isinstance(intel, dict)
    for key in (
        "overall_verdict", "architecture_score", "ai_maturity_level",
        "executive_summary", "critical_risks", "top_priorities",
        "estimated_monthly_savings", "estimated_latency_improvement",
    ):
        assert key in intel, f"intelligence_summary missing key: {key}"
    assert intel["overall_verdict"] in (
        "Enterprise Ready", "Production Ready",
        "Production Ready with Improvements", "Needs Optimization", "Prototype",
    )
    ml = intel["ai_maturity_level"]
    assert "level" in ml and "title" in ml
    assert isinstance(ml["level"], int) and 1 <= ml["level"] <= 5
    assert isinstance(intel["critical_risks"], list)
    assert isinstance(intel["top_priorities"], list)
    assert len(intel["top_priorities"]) <= 3
    assert intel["estimated_monthly_savings"].startswith("$")
    assert intel["estimated_latency_improvement"].endswith("%")


def test_audit_report_structure():
    report = ReviewReportBuilder().build(_make_request())
    ar = report["audit_report"]
    for key in (
        "intelligence_summary", "architecture_overview", "score_breakdown",
        "cost_analysis", "latency_analysis", "rag_analysis",
        "security_analysis", "reliability_analysis", "scalability_analysis",
        "observability_analysis", "recommendations", "optimization_roadmap",
    ):
        assert key in ar, f"audit_report missing key: {key}"


def test_audit_report_architecture_overview_fields():
    report = ReviewReportBuilder().build(_make_request())
    ov = report["audit_report"]["architecture_overview"]
    assert "overall_score" in ov
    assert "architecture_grade" in ov
    assert "production_readiness" in ov
    assert isinstance(ov["overall_score"], int)
    assert isinstance(ov["architecture_grade"], str)


def test_audit_report_score_breakdown_fields():
    report = ReviewReportBuilder().build(_make_request())
    sb = report["audit_report"]["score_breakdown"]
    for key in ("cost_score", "latency_score", "rag_score", "reliability_score",
                "security_score", "scalability_score", "observability_score"):
        assert key in sb
        assert isinstance(sb[key], int)


def test_audit_report_optimization_roadmap_phases():
    request = _make_request(
        authentication=False, cache_enabled=False, retry_strategy=False,
        logging=False, monitoring=False,
    )
    report = ReviewReportBuilder().build(request)
    roadmap = report["audit_report"]["optimization_roadmap"]
    assert isinstance(roadmap, list)
    assert len(roadmap) >= 1
    for phase in roadmap:
        assert "phase"    in phase
        assert "title"    in phase
        assert "timeline" in phase
        assert "tasks"    in phase
        assert isinstance(phase["tasks"], list)


def test_audit_report_score_matches_architecture_score():
    report = ReviewReportBuilder().build(_make_request())
    assert report["audit_report"]["architecture_overview"]["overall_score"] == \
        report["architecture_score"]["overall_score"]


def test_intelligence_summary_score_matches_architecture_score():
    report = ReviewReportBuilder().build(_make_request())
    assert report["intelligence_summary"]["architecture_score"] == \
        report["architecture_score"]["overall_score"]


def test_executive_summary_is_dict():
    report = ReviewReportBuilder().build(_make_request())
    summary = report["executive_summary"]
    assert isinstance(summary, dict), "executive_summary should be a dict"


def test_executive_summary_required_keys():
    report = ReviewReportBuilder().build(_make_request())
    summary = report["executive_summary"]
    required_keys = [
        "overall_assessment",
        "summary",
        "top_strengths",
        "top_risks",
        "estimated_monthly_saving",
        "estimated_latency_improvement",
        "highest_priority_action",
        "production_readiness",
    ]
    for key in required_keys:
        assert key in summary, f"Missing key in executive_summary: {key}"


def test_executive_summary_assessment_values():
    report = ReviewReportBuilder().build(_make_request())
    assert report["executive_summary"]["overall_assessment"] in (
        "Excellent", "Good", "Fair", "Needs Improvement"
    )


def test_executive_summary_lists():
    report = ReviewReportBuilder().build(_make_request())
    summary = report["executive_summary"]
    assert isinstance(summary["top_strengths"], list)
    assert isinstance(summary["top_risks"], list)
    assert len(summary["top_strengths"]) <= 3
    assert len(summary["top_risks"]) <= 3


def test_executive_summary_project_name_in_narrative():
    report = ReviewReportBuilder().build(_make_request(project_name="TalentLens"))
    assert "TalentLens" in report["executive_summary"]["summary"]


def test_executive_summary_saving_format():
    report = ReviewReportBuilder().build(_make_request())
    saving = report["executive_summary"]["estimated_monthly_saving"]
    assert saving.startswith("$")


def test_executive_summary_latency_format():
    report = ReviewReportBuilder().build(_make_request())
    latency = report["executive_summary"]["estimated_latency_improvement"]
    assert latency.endswith("%")


def test_executive_summary_production_readiness_format():
    report = ReviewReportBuilder().build(_make_request())
    pr = report["executive_summary"]["production_readiness"]
    assert "/100" in pr


def test_executive_summary_highest_priority_action_non_empty():
    request = _make_request(authentication=False, cache_enabled=False)
    report = ReviewReportBuilder().build(request)
    action = report["executive_summary"]["highest_priority_action"]
    assert isinstance(action, str) and len(action) > 5


def test_executive_summary_strengths_populated_for_good_arch():
    request = _make_request(
        authentication=True,
        cache_enabled=True,
        rag_enabled=True,
        framework="FastAPI",
    )
    report = ReviewReportBuilder().build(request)
    strengths = report["executive_summary"]["top_strengths"]
    assert len(strengths) >= 1


def test_executive_summary_risks_populated_for_bare_arch():
    request = _make_request(
        authentication=False,
        retry_strategy=False,
        logging=False,
        monitoring=False,
    )
    report = ReviewReportBuilder().build(request)
    risks = report["executive_summary"]["top_risks"]
    assert len(risks) >= 1


def test_report_id_unique():
    r1 = ReviewReportBuilder().build(_make_request())
    r2 = ReviewReportBuilder().build(_make_request())
    assert r1["report_id"] != r2["report_id"]


def test_project_name_in_report():
    report = ReviewReportBuilder().build(_make_request())
    assert report["project_name"] == "TalentLens"
