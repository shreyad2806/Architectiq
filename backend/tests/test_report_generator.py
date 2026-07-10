import pytest

from app.services.report_generator import (
    ReportGenerator,
    _build_optimization_roadmap,
    _is_fast,
    _phase_for,
    _letter_grade,
    _build_architecture_overview,
    _build_score_breakdown,
)


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _raw_report(
    overall_score: int = 82,
    production_score: int = 75,
    extra_recs: bool = False,
) -> dict:
    """Minimal raw report dict that mimics ReviewReportBuilder.build() output."""
    recs = [
        {
            "priority": "HIGH",
            "title": "Enable Semantic Caching",
            "category": "Cost Optimization",
            "difficulty": "Easy",
            "implementation_time": "2 hours",
            "expected_monthly_saving": "$780",
            "description": "Add a semantic cache.",
            "estimated_monthly_saving": 780.0,
            "estimated_latency_improvement": 80.0,
            "estimated_score_improvement": 7,
        },
        {
            "priority": "HIGH",
            "title": "Enforce API Authentication",
            "category": "Security",
            "difficulty": "Easy",
            "implementation_time": "2 hours",
            "expected_monthly_saving": "$0",
            "description": "Add JWT auth.",
            "estimated_monthly_saving": 0.0,
            "estimated_latency_improvement": 0.0,
            "estimated_score_improvement": 10,
        },
        {
            "priority": "MEDIUM",
            "title": "Add Hybrid Search",
            "category": "RAG Optimization",
            "difficulty": "Medium",
            "implementation_time": "4 hours",
            "expected_monthly_saving": "$0",
            "description": "Combine BM25 + dense.",
            "estimated_monthly_saving": 0.0,
            "estimated_latency_improvement": 30.0,
            "estimated_score_improvement": 4,
        },
        {
            "priority": "LOW",
            "title": "Expose /health Endpoint",
            "category": "Observability",
            "difficulty": "Easy",
            "implementation_time": "15 minutes",
            "expected_monthly_saving": "$0",
            "description": "Add health check.",
            "estimated_monthly_saving": 0.0,
            "estimated_latency_improvement": 0.0,
            "estimated_score_improvement": 2,
        },
    ]

    return {
        "intelligence_summary": {
            "overall_verdict": "Production Ready with Improvements",
            "architecture_score": overall_score,
            "ai_maturity_level": {"level": 3, "title": "Scaling"},
            "executive_summary": "System is technically sound.",
            "critical_risks": ["No cache", "No auth"],
            "top_priorities": ["Enable Semantic Caching"],
            "estimated_monthly_savings": "$780",
            "estimated_latency_improvement": "35%",
        },
        "architecture_score": {
            "overall_score": overall_score,
            "grade": "Good",
            "dimension_scores": {
                "cost": 82,
                "latency": 78,
                "rag": 91,
                "reliability": 76,
                "security": 88,
                "scalability": 83,
                "observability": 71,
                "production": production_score,
            },
        },
        "production_readiness": {
            "score": production_score,
            "grade": "Good",
            "missing_features": [],
        },
        "cost_analysis": {
            "estimated_monthly_tokens": 190_000_000,
            "estimated_monthly_cost": 2_480.0,
            "potential_monthly_savings": 820.0,
            "currency": "USD",
        },
        "latency_analysis": {
            "estimated_latency_ms": 620,
            "latency_rating": "Moderate",
        },
        "rag_analysis": {
            "rag_score": 91,
            "retrieval_quality": "Excellent",
            "recommendations": [],
        },
        "security_analysis": {
            "security_score": 88,
            "severity": "INFO",
            "security_findings": [],
            "recommendations": [],
        },
        "reliability_analysis": {
            "reliability_score": 76,
            "risk_level": "Medium",
            "findings": [],
        },
        "scalability_analysis": {
            "scalability_score": 83,
            "expected_capacity": "High",
            "recommendations": [],
        },
        "observability_analysis": {
            "observability_score": 71,
            "missing_features": [],
            "recommendations": [],
        },
        "recommendations": recs,
        "rich_recommendations": recs,
        "executive_summary": {
            "overall_assessment": "Good",
            "summary": "A narrative.",
            "top_strengths": [],
            "top_risks": [],
            "estimated_monthly_saving": "$780",
            "estimated_latency_improvement": "35%",
            "highest_priority_action": "Enable caching.",
            "production_readiness": f"{production_score}/100",
        },
        "top_findings": [],
        "dynamic_roadmap": [
            {
                "phase": 1, "title": "Quick Wins", "timeline": "Today",
                "tasks": [
                    {"title": "Enforce API Authentication (OAuth 2.0 / JWT)",
                     "priority": "HIGH", "category": "Security",
                     "reason": "Unauthenticated endpoints.",
                     "expected_monthly_saving": "$0", "latency_improvement": "0%",
                     "difficulty": "Easy", "implementation_time": "2 hours"},
                    {"title": "Enable Semantic Caching",
                     "priority": "HIGH", "category": "Cost Optimization",
                     "reason": "Reduce token spend.",
                     "expected_monthly_saving": "$780", "latency_improvement": "35%",
                     "difficulty": "Easy", "implementation_time": "2 hours"},
                ],
            },
            {
                "phase": 2, "title": "Performance Improvements", "timeline": "This Week",
                "tasks": [
                    {"title": "Add Hybrid Search (Dense + Sparse Retrieval)",
                     "priority": "MEDIUM", "category": "RAG Optimization",
                     "reason": "Improve recall.",
                     "expected_monthly_saving": "$0", "latency_improvement": "0%",
                     "difficulty": "Medium", "implementation_time": "4 hours"},
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# _letter_grade unit tests
# ---------------------------------------------------------------------------

def test_letter_grade_thresholds():
    assert _letter_grade(97) == "A+"
    assert _letter_grade(95) == "A+"
    assert _letter_grade(92) == "A"
    assert _letter_grade(90) == "A"
    assert _letter_grade(87) == "A-"
    assert _letter_grade(85) == "A-"
    assert _letter_grade(82) == "B+"
    assert _letter_grade(80) == "B+"
    assert _letter_grade(77) == "B"
    assert _letter_grade(75) == "B"
    assert _letter_grade(72) == "B-"
    assert _letter_grade(70) == "B-"
    assert _letter_grade(67) == "C+"
    assert _letter_grade(65) == "C+"
    assert _letter_grade(62) == "C"
    assert _letter_grade(60) == "C"
    assert _letter_grade(55) == "C-"
    assert _letter_grade(50) == "C-"
    assert _letter_grade(30) == "D"
    assert _letter_grade(0)  == "D"


# ---------------------------------------------------------------------------
# _is_fast unit tests
# ---------------------------------------------------------------------------

def test_is_fast_minutes():
    assert _is_fast("15 minutes") is True
    assert _is_fast("30 min") is True
    assert _is_fast("2 hours") is True
    assert _is_fast("4 hours") is True


def test_is_fast_not_fast():
    assert _is_fast("1 day") is False
    assert _is_fast("1 week") is False
    assert _is_fast("2 weeks") is False


def test_is_fast_empty():
    assert _is_fast("") is False


# ---------------------------------------------------------------------------
# _phase_for unit tests
# ---------------------------------------------------------------------------

def test_phase_for_immediate_easy_fast_high():
    rec = {"difficulty": "Easy", "implementation_time": "2 hours",
           "priority": "HIGH", "category": "Cost Optimization"}
    assert _phase_for(rec) == 1


def test_phase_for_immediate_easy_fast_medium():
    rec = {"difficulty": "Easy", "implementation_time": "30 minutes",
           "priority": "MEDIUM", "category": "Security"}
    assert _phase_for(rec) == 1


def test_phase_for_not_immediate_low_priority():
    rec = {"difficulty": "Easy", "implementation_time": "15 minutes",
           "priority": "LOW", "category": "Observability"}
    assert _phase_for(rec) == 2


def test_phase_for_production_hardening_medium_difficulty():
    rec = {"difficulty": "Medium", "implementation_time": "1 day",
           "priority": "HIGH", "category": "Cost Optimization"}
    assert _phase_for(rec) == 2


def test_phase_for_scale_hard_difficulty():
    rec = {"difficulty": "Hard", "implementation_time": "1 week",
           "priority": "MEDIUM", "category": "RAG Optimization"}
    assert _phase_for(rec) == 3


def test_phase_for_scale_multi_week():
    rec = {"difficulty": "Medium", "implementation_time": "2 weeks",
           "priority": "LOW", "category": "Scalability"}
    assert _phase_for(rec) == 3


def test_phase_for_scale_rag_medium():
    rec = {"difficulty": "Medium", "implementation_time": "4 hours",
           "priority": "MEDIUM", "category": "RAG Optimization"}
    assert _phase_for(rec) == 3


# ---------------------------------------------------------------------------
# _build_optimization_roadmap unit tests
# (function now reads raw_report["dynamic_roadmap"] — delegate contract)
# ---------------------------------------------------------------------------

def test_roadmap_output_keys():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins", "timeline": "Today",
         "tasks": [{"title": "Enable Cache", "priority": "HIGH",
                    "category": "Cost Optimization", "reason": "",
                    "difficulty": "Easy", "implementation_time": "2 hours",
                    "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    assert len(roadmap) == 1
    phase = roadmap[0]
    assert "phase" in phase
    assert "title" in phase
    assert "timeline" in phase
    assert "tasks" in phase


def test_roadmap_tasks_are_dicts():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins", "timeline": "Today",
         "tasks": [
             {"title": "Enable Cache", "priority": "HIGH", "category": "Cost Optimization",
              "reason": "", "difficulty": "Easy", "implementation_time": "2 hours",
              "expected_monthly_saving": "$0", "latency_improvement": "0%"},
             {"title": "Add Auth", "priority": "HIGH", "category": "Security",
              "reason": "", "difficulty": "Easy", "implementation_time": "1 hour",
              "expected_monthly_saving": "$0", "latency_improvement": "0%"},
         ]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    for phase in roadmap:
        for task in phase["tasks"]:
            assert isinstance(task, dict)
            assert "title" in task


def test_roadmap_phase_titles():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins",              "timeline": "Today",       "tasks": [{"title": "T1", "priority": "HIGH", "category": "", "reason": "", "difficulty": "Easy", "implementation_time": "1 hour", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
        {"phase": 2, "title": "Performance Improvements", "timeline": "This Week",  "tasks": [{"title": "T2", "priority": "MEDIUM", "category": "", "reason": "", "difficulty": "Medium", "implementation_time": "1 day", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
        {"phase": 3, "title": "Production Scaling",       "timeline": "This Month", "tasks": [{"title": "T3", "priority": "LOW", "category": "", "reason": "", "difficulty": "Hard", "implementation_time": "1 week", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    titles = {p["title"] for p in roadmap}
    assert "Quick Wins" in titles
    assert "Performance Improvements" in titles
    assert "Production Scaling" in titles


def test_roadmap_phase_timelines():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins",              "timeline": "Today",       "tasks": [{"title": "T1", "priority": "HIGH", "category": "", "reason": "", "difficulty": "Easy", "implementation_time": "1 hour", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
        {"phase": 2, "title": "Performance Improvements", "timeline": "This Week",  "tasks": [{"title": "T2", "priority": "MEDIUM", "category": "", "reason": "", "difficulty": "Medium", "implementation_time": "1 day", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
        {"phase": 3, "title": "Production Scaling",       "timeline": "This Month", "tasks": [{"title": "T3", "priority": "LOW", "category": "", "reason": "", "difficulty": "Hard", "implementation_time": "1 week", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    timelines = {p["timeline"] for p in roadmap}
    assert "Today" in timelines
    assert "This Week" in timelines
    assert "This Month" in timelines


def test_roadmap_phases_sorted():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins",              "timeline": "Today",       "tasks": [{"title": "T1", "priority": "HIGH", "category": "", "reason": "", "difficulty": "Easy", "implementation_time": "1 hour", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
        {"phase": 3, "title": "Production Scaling",       "timeline": "This Month", "tasks": [{"title": "T3", "priority": "LOW", "category": "", "reason": "", "difficulty": "Hard", "implementation_time": "1 week", "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    phase_nums = [p["phase"] for p in roadmap]
    assert phase_nums == sorted(phase_nums)


def test_roadmap_omits_empty_phases():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins", "timeline": "Today",
         "tasks": [{"title": "Only Easy", "priority": "HIGH", "category": "Security",
                    "reason": "", "difficulty": "Easy", "implementation_time": "2 hours",
                    "expected_monthly_saving": "$0", "latency_improvement": "0%"}]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    assert len(roadmap) == 1
    assert roadmap[0]["title"] == "Quick Wins"


def test_roadmap_multiple_tasks_in_phase():
    raw = {"dynamic_roadmap": [
        {"phase": 1, "title": "Quick Wins", "timeline": "Today",
         "tasks": [
             {"title": f"Task {i}", "priority": "HIGH", "category": "Security",
              "reason": "", "difficulty": "Easy", "implementation_time": "1 hour",
              "expected_monthly_saving": "$0", "latency_improvement": "0%"}
             for i in range(4)
         ]},
    ]}
    roadmap = _build_optimization_roadmap(raw)
    assert roadmap[0]["title"] == "Quick Wins"
    assert len(roadmap[0]["tasks"]) == 4


def test_roadmap_empty_dynamic_roadmap():
    assert _build_optimization_roadmap({"dynamic_roadmap": []}) == []


def test_roadmap_missing_key_returns_empty():
    assert _build_optimization_roadmap({}) == []


# ---------------------------------------------------------------------------
# ReportGenerator.generate() integration tests
# ---------------------------------------------------------------------------

def test_generate_output_keys():
    report = ReportGenerator().generate(_raw_report())
    required = [
        "intelligence_summary",
        "architecture_overview",
        "score_breakdown",
        "cost_analysis",
        "latency_analysis",
        "rag_analysis",
        "security_analysis",
        "reliability_analysis",
        "scalability_analysis",
        "observability_analysis",
        "recommendations",
        "optimization_roadmap",
    ]
    for key in required:
        assert key in report, f"Missing key: {key}"


def test_generate_architecture_overview_values():
    report = ReportGenerator().generate(_raw_report(overall_score=82, production_score=75))
    ov = report["architecture_overview"]
    assert ov["overall_score"] == 82
    assert ov["production_readiness"] == 75
    assert ov["architecture_grade"] == "B+"


def test_generate_score_breakdown_all_dimensions():
    report = ReportGenerator().generate(_raw_report())
    sb = report["score_breakdown"]
    assert sb["cost_score"] == 82
    assert sb["latency_score"] == 78
    assert sb["rag_score"] == 91
    assert sb["reliability_score"] == 76
    assert sb["security_score"] == 88
    assert sb["scalability_score"] == 83
    assert sb["observability_score"] == 71


def test_generate_cost_analysis_has_saving_from_recs():
    report = ReportGenerator().generate(_raw_report())
    ca = report["cost_analysis"]
    assert "estimated_saving_from_recs" in ca
    assert ca["estimated_saving_from_recs"] == "$780"
    assert ca["currency"] == "USD"


def test_generate_latency_has_improvement():
    report = ReportGenerator().generate(_raw_report())
    la = report["latency_analysis"]
    assert "estimated_improvement" in la
    assert la["estimated_improvement"] == "35%"


def test_generate_roadmap_phase_shape():
    report = ReportGenerator().generate(_raw_report())
    roadmap = report["optimization_roadmap"]
    assert isinstance(roadmap, list)
    assert len(roadmap) >= 1
    for phase in roadmap:
        assert "phase"    in phase
        assert "title"    in phase
        assert "timeline" in phase
        assert "tasks"    in phase
        assert isinstance(phase["tasks"], list)
        for task in phase["tasks"]:
            assert isinstance(task, dict)
            assert "title" in task
            assert "priority" in task


def test_generate_roadmap_timelines():
    report = ReportGenerator().generate(_raw_report())
    roadmap = report["optimization_roadmap"]
    timelines = {p["timeline"] for p in roadmap}
    assert timelines.issubset({"Today", "This Week", "This Month"})


def test_generate_roadmap_phase_titles_new():
    report = ReportGenerator().generate(_raw_report())
    roadmap = report["optimization_roadmap"]
    titles = {p["title"] for p in roadmap}
    assert titles.issubset({"Quick Wins", "Performance Improvements", "Production Scaling"})


def test_generate_intelligence_summary_passed_through():
    report = ReportGenerator().generate(_raw_report())
    intel = report["intelligence_summary"]
    assert intel["overall_verdict"] == "Production Ready with Improvements"
    assert intel["architecture_score"] == 82


def test_generate_no_duplication_of_scores():
    """score_breakdown must not repeat overall_score."""
    report = ReportGenerator().generate(_raw_report(overall_score=85))
    assert "overall_score" not in report["score_breakdown"]


def test_generate_recommendations_preserved():
    report = ReportGenerator().generate(_raw_report())
    recs = report["recommendations"]
    assert isinstance(recs, list)
    assert len(recs) == 4


def test_generate_roadmap_tasks_are_rich_dicts():
    """Each task in the roadmap must be a rich dict with at least title and priority."""
    report = ReportGenerator().generate(_raw_report())
    roadmap = report["optimization_roadmap"]
    for phase in roadmap:
        for task in phase["tasks"]:
            assert isinstance(task, dict)
            assert isinstance(task.get("title"), str) and len(task["title"]) > 0
            assert task.get("priority") in {"HIGH", "MEDIUM", "LOW"}
