"""Tests for the consulting-grade Executive Summary generator.

Covers:
  - Excellent architecture (score ≥ 90) → optimistic, incremental tone
  - Moderate architecture (60–84)       → balanced, improvement-focused tone
  - Poor architecture (< 60)            → warning-led, risk-first tone
  - Narrative includes: project name, dimension list, findings count,
    high-priority count, highest risk, top actions, savings, latency,
    production readiness, final recommendation
  - Different architectures produce different summaries
  - No hardcoded text survives across different inputs
  - IntelligenceLayer.executive_summary passes through to output
"""

import pytest

from app.services.intelligence_layer import (
    IntelligenceLayer,
    _executive_narrative,
    _final_recommendation,
)
from app.services.executive_summary_generator import (
    ExecutiveSummaryGenerator,
    _build_narrative_summary,
    _final_recommendation as esg_final_rec,
)
from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(**kwargs) -> ReviewRequest:
    defaults = dict(
        project_name="AcmeRAG",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="pinecone",
        framework="fastapi",
        monthly_requests=100_000,
        average_prompt_tokens=1_000,
        average_completion_tokens=500,
        context_window=8_000,
        concurrent_users=1_000,
        prompt_strategy="few-shot",
    )
    defaults.update(kwargs)
    return ReviewRequest(**defaults)


def _narrative(
    project_name="TestProject",
    overall_score=75,
    n_findings=5,
    n_high=2,
    production_score=70,
    saving="$500",
    latency="25%",
    top_risk="API Authentication is disabled",
    actions=None,
) -> str:
    return _executive_narrative(
        project_name=project_name,
        overall_score=overall_score,
        verdict="",
        n_high_risks=n_high,
        n_findings=n_findings,
        n_recs=n_findings,
        estimated_saving=saving,
        latency_improvement=latency,
        production_score=production_score,
        top_risk_title=top_risk,
        top_action_titles=actions or ["Enable Semantic Caching", "Add Rate Limiting"],
    )


def _adv_report(saving="$500", latency="25%", n_recs=3) -> dict:
    return {
        "total_estimated_monthly_savings": saving,
        "estimated_latency_improvement": latency,
        "recommendations": [
            {"title": f"Action {i}", "priority": "HIGH", "reason": f"Reason {i}."}
            for i in range(n_recs)
        ],
    }


def _findings(n_high=2, n_medium=1, n_low=0) -> list[dict]:
    out = []
    for i in range(n_high):
        out.append({"severity": "HIGH", "title": f"High Risk {i}", "description": "", "impact": ""})
    for i in range(n_medium):
        out.append({"severity": "MEDIUM", "title": f"Medium Issue {i}", "description": "", "impact": ""})
    for i in range(n_low):
        out.append({"severity": "LOW", "title": f"Low Issue {i}", "description": "", "impact": ""})
    return out


# ---------------------------------------------------------------------------
# _final_recommendation tier tests
# ---------------------------------------------------------------------------

class TestFinalRecommendationTiers:
    def test_excellent_tier(self):
        text = _final_recommendation(92)
        assert "strong engineering discipline" in text
        assert "enterprise-grade" in text

    def test_moderate_tier(self):
        text = _final_recommendation(78)
        assert "production" in text.lower()
        assert "high-priority" in text

    def test_borderline_tier(self):
        text = _final_recommendation(62)
        assert "foundational gaps" in text or "blocking" in text

    def test_poor_tier(self):
        text = _final_recommendation(40)
        assert "significant production risk" in text or "not ready" in text

    def test_threshold_boundary_90(self):
        assert _final_recommendation(90) == _final_recommendation(95)

    def test_threshold_boundary_75(self):
        assert _final_recommendation(75) == _final_recommendation(80)

    def test_threshold_boundary_60(self):
        assert _final_recommendation(60) == _final_recommendation(65)

    def test_poor_and_excellent_differ(self):
        assert _final_recommendation(95) != _final_recommendation(30)


# ---------------------------------------------------------------------------
# _executive_narrative structure tests
# ---------------------------------------------------------------------------

class TestExecutiveNarrativeStructure:
    def test_always_mentions_project_name(self):
        text = _narrative(project_name="SkylineAI")
        assert "SkylineAI" in text

    def test_always_mentions_dimensions(self):
        text = _narrative()
        assert "cost efficiency" in text
        assert "reliability" in text
        assert "scalability" in text
        assert "security" in text
        assert "latency" in text
        assert "RAG" in text

    def test_mentions_findings_count(self):
        text = _narrative(n_findings=7)
        assert "7" in text

    def test_mentions_high_priority_count(self):
        text = _narrative(n_high=4)
        assert "4" in text
        assert "high-priority" in text

    def test_zero_findings_no_deficiencies_phrase(self):
        text = _narrative(n_findings=0, n_high=0, top_risk="")
        assert "no significant architectural deficiencies" in text

    def test_mentions_top_risk(self):
        text = _narrative(top_risk="API Authentication is disabled")
        assert "API Authentication is disabled" in text

    def test_mentions_single_action(self):
        text = _narrative(actions=["Enable Semantic Caching"])
        assert "Enable Semantic Caching" in text

    def test_mentions_two_actions_joined_with_and(self):
        text = _narrative(actions=["Enable Caching", "Add Retry"])
        assert "Enable Caching and Add Retry" in text

    def test_mentions_three_actions_oxford_comma(self):
        text = _narrative(actions=["A", "B", "C"])
        assert "A, B, and C" in text

    def test_mentions_savings(self):
        text = _narrative(saving="$1,420")
        assert "$1,420" in text

    def test_mentions_latency(self):
        text = _narrative(latency="31%")
        assert "31%" in text

    def test_mentions_production_readiness_score(self):
        text = _narrative(production_score=71)
        assert "71/100" in text

    def test_zero_savings_no_cost_sentence(self):
        text = _narrative(saving="$0", latency="0%")
        assert "reduce monthly AI infrastructure costs" not in text
        assert "improve average response latency" not in text

    def test_no_hardcoded_numbers(self):
        """Different scores produce different production readiness numbers in output."""
        text_a = _narrative(production_score=55)
        text_b = _narrative(production_score=85)
        assert "55/100" in text_a
        assert "85/100" in text_b
        assert "55/100" not in text_b
        assert "85/100" not in text_a


# ---------------------------------------------------------------------------
# Tier-specific tone tests
# ---------------------------------------------------------------------------

class TestTierTones:
    def test_excellent_arch_contains_optimistic_final_rec(self):
        text = _narrative(overall_score=92, n_findings=2, n_high=0, production_score=90)
        assert "strong engineering discipline" in text

    def test_moderate_arch_balanced_tone(self):
        text = _narrative(overall_score=72, n_findings=8, n_high=3, production_score=68)
        assert "identified" in text
        assert "high-priority" in text

    def test_poor_arch_warning_tone(self):
        text = _narrative(overall_score=42, n_findings=15, n_high=7, production_score=40)
        assert "significant production risk" in text or "not ready" in text

    def test_excellent_vs_poor_different_final_rec(self):
        text_ex   = _narrative(overall_score=93, n_findings=1, n_high=0, production_score=92)
        text_poor = _narrative(overall_score=38, n_findings=18, n_high=9, production_score=30)
        assert text_ex != text_poor

    def test_production_readiness_label_excellent(self):
        text = _narrative(production_score=85)
        assert "meets production readiness standards" in text

    def test_production_readiness_label_approaching(self):
        text = _narrative(production_score=68)
        assert "approaching production readiness" in text

    def test_production_readiness_label_not_reached(self):
        text = _narrative(production_score=55)
        assert "has not yet reached production readiness" in text


# ---------------------------------------------------------------------------
# IntelligenceLayer integration tests
# ---------------------------------------------------------------------------

class TestIntelligenceLayerNarrative:
    def _layer(self, overall_score, production_score, n_high=2, saving="$780", latency="31%"):
        layer = IntelligenceLayer()
        return layer.generate(
            overall_score=overall_score,
            production_score=production_score,
            top_findings=_findings(n_high=n_high),
            recommendations=[{"title": "Rec A", "priority": "HIGH"}],
            advanced_rec_report=_adv_report(saving=saving, latency=latency),
        )

    def test_output_has_executive_summary_key(self):
        result = self._layer(82, 75)
        assert "executive_summary" in result

    def test_summary_is_non_empty_string(self):
        result = self._layer(82, 75)
        assert isinstance(result["executive_summary"], str)
        assert len(result["executive_summary"]) > 50

    def test_summary_mentions_dimensions(self):
        result = self._layer(82, 75)
        assert "cost efficiency" in result["executive_summary"]

    def test_summary_mentions_findings(self):
        result = self._layer(75, 65, n_high=3)
        assert "3" in result["executive_summary"] or "high-priority" in result["executive_summary"]

    def test_summary_mentions_savings(self):
        result = self._layer(75, 70, saving="$1,200")
        assert "$1,200" in result["executive_summary"]

    def test_summary_mentions_production_readiness(self):
        result = self._layer(80, 72)
        assert "72/100" in result["executive_summary"]

    def test_excellent_arch_optimistic_summary(self):
        result = self._layer(95, 92, n_high=0, saving="$0", latency="0%")
        text = result["executive_summary"]
        assert "strong engineering discipline" in text or "enterprise-grade" in text

    def test_poor_arch_warning_summary(self):
        result = self._layer(38, 30, n_high=8, saving="$2,000", latency="40%")
        text = result["executive_summary"]
        assert "risk" in text.lower() or "not ready" in text.lower() or "significant" in text.lower()

    def test_different_architectures_different_summaries(self):
        good = self._layer(95, 90, n_high=0, saving="$0",    latency="0%")
        poor = self._layer(35, 28, n_high=8, saving="$2,500", latency="60%")
        assert good["executive_summary"] != poor["executive_summary"]

    def test_top_action_mentioned_in_summary(self):
        layer = IntelligenceLayer()
        result = layer.generate(
            overall_score=72,
            production_score=65,
            top_findings=_findings(n_high=2),
            recommendations=[{"title": "Enable Cache", "priority": "HIGH"}],
            advanced_rec_report={
                "total_estimated_monthly_savings": "$780",
                "estimated_latency_improvement": "35%",
                "recommendations": [
                    {"title": "Enable Cache", "priority": "HIGH", "reason": ""},
                ],
            },
        )
        assert "Enable Cache" in result["executive_summary"]

    def test_highest_risk_mentioned_in_summary(self):
        layer = IntelligenceLayer()
        findings = [{"severity": "HIGH", "title": "No API Authentication", "description": "", "impact": ""}]
        result = layer.generate(
            overall_score=65,
            production_score=60,
            top_findings=findings,
            recommendations=[],
            advanced_rec_report=_adv_report(),
        )
        assert "No API Authentication" in result["executive_summary"]


# ---------------------------------------------------------------------------
# ExecutiveSummaryGenerator._build_narrative_summary direct tests
# ---------------------------------------------------------------------------

class TestBuildNarrativeSummary:
    def _narrative(self, **kwargs) -> str:
        defaults = dict(
            project_name="TestProject",
            overall_score=75,
            assessment="Good",
            n_findings=5,
            n_recs=5,
            n_high=2,
            n_critical=0,
            production_score=70,
            estimated_saving="$500",
            latency_improvement="25%",
            top_risk_title="API Authentication is disabled",
            top_action_titles=["Enable Caching", "Add Retry", "Rate Limiting"],
        )
        defaults.update(kwargs)
        return _build_narrative_summary(**defaults)

    def test_project_name_in_output(self):
        assert "TestProject" in self._narrative()

    def test_findings_count_in_output(self):
        assert "5" in self._narrative(n_findings=5)

    def test_no_findings_phrase(self):
        text = self._narrative(n_findings=0, n_high=0, top_risk_title="")
        assert "no significant architectural deficiencies" in text

    def test_top_risk_in_output(self):
        text = self._narrative(top_risk_title="Missing Rate Limiting")
        assert "Missing Rate Limiting" in text

    def test_savings_in_output(self):
        text = self._narrative(estimated_saving="$1,800")
        assert "$1,800" in text

    def test_latency_in_output(self):
        text = self._narrative(latency_improvement="42%")
        assert "42%" in text

    def test_production_score_in_output(self):
        text = self._narrative(production_score=63)
        assert "63/100" in text

    def test_excellent_final_rec(self):
        text = self._narrative(overall_score=91)
        assert "strong engineering discipline" in text

    def test_poor_final_rec(self):
        text = self._narrative(overall_score=45)
        assert "significant production risk" in text or "not ready" in text

    def test_zero_savings_skips_cost_sentence(self):
        text = self._narrative(estimated_saving="$0", latency_improvement="0%")
        assert "reduce monthly AI infrastructure costs" not in text
