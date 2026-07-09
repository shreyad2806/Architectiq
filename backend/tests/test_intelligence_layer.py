import pytest

from app.services.intelligence_layer import (
    IntelligenceLayer,
    _critical_risks,
    _maturity,
    _top_priorities,
    _verdict,
)

# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------

def test_verdict_thresholds():
    assert _verdict(98) == "Enterprise Ready"
    assert _verdict(95) == "Enterprise Ready"
    assert _verdict(90) == "Production Ready"
    assert _verdict(85) == "Production Ready"
    assert _verdict(80) == "Production Ready with Improvements"
    assert _verdict(70) == "Production Ready with Improvements"
    assert _verdict(60) == "Needs Optimization"
    assert _verdict(50) == "Needs Optimization"
    assert _verdict(49) == "Prototype"
    assert _verdict(0)  == "Prototype"


def test_maturity_levels():
    assert _maturity(97) == {"level": 5, "title": "Enterprise Optimized"}
    assert _maturity(95) == {"level": 5, "title": "Enterprise Optimized"}
    assert _maturity(90) == {"level": 4, "title": "Production Ready"}
    assert _maturity(85) == {"level": 4, "title": "Production Ready"}
    assert _maturity(75) == {"level": 3, "title": "Scaling"}
    assert _maturity(70) == {"level": 3, "title": "Scaling"}
    assert _maturity(60) == {"level": 2, "title": "Development"}
    assert _maturity(50) == {"level": 2, "title": "Development"}
    assert _maturity(40) == {"level": 1, "title": "Prototype"}
    assert _maturity(0)  == {"level": 1, "title": "Prototype"}


def test_critical_risks_only_high():
    findings = [
        {"severity": "HIGH",   "title": "Auth missing"},
        {"severity": "MEDIUM", "title": "No caching"},
        {"severity": "HIGH",   "title": "Retry absent"},
        {"severity": "LOW",    "title": "No health endpoint"},
    ]
    risks = _critical_risks(findings)
    assert risks == ["Auth missing", "Retry absent"]
    assert "No caching" not in risks
    assert "No health endpoint" not in risks


def test_critical_risks_all_high_returned():
    findings = [
        {"severity": "HIGH", "title": f"Risk {i}"}
        for i in range(6)
    ]
    risks = _critical_risks(findings)
    assert len(risks) == 6


def test_critical_risks_deduplicates():
    findings = [
        {"severity": "HIGH", "title": "Same Risk"},
        {"severity": "HIGH", "title": "Same Risk"},
        {"severity": "HIGH", "title": "Other Risk"},
    ]
    risks = _critical_risks(findings)
    assert risks.count("Same Risk") == 1


def test_critical_risks_empty_when_no_high():
    findings = [
        {"severity": "MEDIUM", "title": "Something"},
        {"severity": "LOW",    "title": "Another"},
    ]
    assert _critical_risks(findings) == []


def test_top_priorities_takes_first_three():
    recs = [{"title": f"Rec {i}", "priority": "HIGH"} for i in range(6)]
    priorities = _top_priorities(recs)
    assert priorities == ["Rec 0", "Rec 1", "Rec 2"]


def test_top_priorities_fewer_than_three():
    recs = [{"title": "Only one", "priority": "HIGH"}]
    assert _top_priorities(recs) == ["Only one"]


def test_top_priorities_empty():
    assert _top_priorities([]) == []


# ---------------------------------------------------------------------------
# Integration tests for IntelligenceLayer.generate()
# ---------------------------------------------------------------------------

def _make_advanced_report(saving="$500", latency="35%"):
    return {
        "total_estimated_monthly_savings": saving,
        "estimated_latency_improvement": latency,
        "recommendations": [
            {"title": f"Action {i}", "priority": "HIGH", "reason": f"Reason {i}."}
            for i in range(5)
        ],
    }


def _make_findings(n_high=2, n_medium=1):
    findings = []
    for i in range(n_high):
        findings.append({"severity": "HIGH", "title": f"High Risk {i}",
                         "description": "", "impact": ""})
    for i in range(n_medium):
        findings.append({"severity": "MEDIUM", "title": f"Medium Risk {i}",
                         "description": "", "impact": ""})
    return findings


def test_generate_output_keys():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=82,
        production_score=75,
        top_findings=_make_findings(),
        recommendations=[{"title": "Rec A", "priority": "HIGH"}],
        cost_result={"potential_monthly_savings": 500},
        advanced_rec_report=_make_advanced_report(),
    )
    required = [
        "overall_verdict",
        "architecture_score",
        "ai_maturity_level",
        "executive_summary",
        "critical_risks",
        "top_priorities",
        "estimated_monthly_savings",
        "estimated_latency_improvement",
    ]
    for key in required:
        assert key in result, f"Missing key: {key}"


def test_generate_architecture_score_matches():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=88,
        production_score=80,
        top_findings=[],
        recommendations=[],
        cost_result={},
        advanced_rec_report=_make_advanced_report(),
    )
    assert result["architecture_score"] == 88


def test_generate_maturity_level_structure():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=90,
        production_score=85,
        top_findings=[],
        recommendations=[],
        cost_result={},
        advanced_rec_report=_make_advanced_report(),
    )
    ml = result["ai_maturity_level"]
    assert "level" in ml
    assert "title" in ml
    assert isinstance(ml["level"], int)


def test_generate_verdict_matches_score():
    layer = IntelligenceLayer()
    for score, expected_verdict in [
        (97, "Enterprise Ready"),
        (87, "Production Ready"),
        (75, "Production Ready with Improvements"),
        (55, "Needs Optimization"),
        (30, "Prototype"),
    ]:
        result = layer.generate(
            overall_score=score,
            production_score=70,
            top_findings=[],
            recommendations=[],
            cost_result={},
            advanced_rec_report=_make_advanced_report(),
        )
        assert result["overall_verdict"] == expected_verdict, (
            f"Score {score}: expected '{expected_verdict}', got '{result['overall_verdict']}'"
        )


def test_generate_critical_risks_only_high():
    findings = [
        {"severity": "HIGH",   "title": "Auth Disabled", "description": "", "impact": ""},
        {"severity": "MEDIUM", "title": "No Cache",      "description": "", "impact": ""},
        {"severity": "HIGH",   "title": "No Retry",      "description": "", "impact": ""},
    ]
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=75,
        production_score=65,
        top_findings=findings,
        recommendations=[],
        cost_result={},
        advanced_rec_report=_make_advanced_report(),
    )
    assert "Auth Disabled" in result["critical_risks"]
    assert "No Retry" in result["critical_risks"]
    assert "No Cache" not in result["critical_risks"]


def test_generate_top_priorities_max_three():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=75,
        production_score=65,
        top_findings=[],
        recommendations=[{"title": f"R{i}", "priority": "HIGH"} for i in range(6)],
        cost_result={},
        advanced_rec_report=_make_advanced_report(),
    )
    assert len(result["top_priorities"]) <= 3


def test_generate_savings_and_latency_from_advanced_report():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=80,
        production_score=78,
        top_findings=[],
        recommendations=[],
        cost_result={"potential_monthly_savings": 999},
        advanced_rec_report=_make_advanced_report(saving="$1,234", latency="41%"),
    )
    assert result["estimated_monthly_savings"] == "$1,234"
    assert result["estimated_latency_improvement"] == "41%"


def test_generate_executive_summary_non_empty():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=82,
        production_score=75,
        top_findings=_make_findings(n_high=2),
        recommendations=[{"title": "Enable caching", "priority": "HIGH"}],
        cost_result={},
        advanced_rec_report=_make_advanced_report(),
    )
    summary = result["executive_summary"]
    assert isinstance(summary, str)
    assert len(summary) > 20


def test_generate_no_critical_risks_when_no_high_findings():
    layer = IntelligenceLayer()
    result = layer.generate(
        overall_score=88,
        production_score=85,
        top_findings=[{"severity": "MEDIUM", "title": "Minor issue",
                       "description": "", "impact": ""}],
        recommendations=[],
        cost_result={},
        advanced_rec_report=_make_advanced_report(),
    )
    assert result["critical_risks"] == []
