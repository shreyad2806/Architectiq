"""ReviewReportBuilder.

Assembles a complete, enterprise-grade architecture audit report by
combining the outputs of every analyzer into a single structured response.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas import ReviewRequest
from app.services.architecture_scoring_service import ArchitectureScoringService
from app.services.cost_analyzer import CostAnalyzer
from app.services.latency_analyzer import LatencyAnalyzer
from app.services.observability_analyzer import ObservabilityAnalyzer
from app.services.production_readiness_analyzer import ProductionReadinessAnalyzer
from app.services.rag_analyzer import RagAnalyzer
from app.services.reliability_analyzer import ReliabilityAnalyzer
from app.services.scalability_analyzer import ScalabilityAnalyzer
from app.services.security_analyzer import SecurityAnalyzer
from app.services.recommendation_engine import AdvancedRecommendationEngine, RecommendationEngine
from app.services.executive_summary_generator import ExecutiveSummaryGenerator
from app.services.intelligence_layer import IntelligenceLayer
from app.services.architecture_health_aggregator import ArchitectureHealthAggregator
from app.services.roadmap_generator import RoadmapGenerator
from app.services.report_generator import ReportGenerator


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

_SCORE_TO_SEVERITY: list[tuple[int, str]] = [
    (80, "INFO"),
    (60, "WARNING"),
    (0,  "CRITICAL"),
]


def _severity(score: int) -> str:
    for threshold, label in _SCORE_TO_SEVERITY:
        if score >= threshold:
            return label
    return "CRITICAL"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class ReviewReportBuilder:
    """Build a complete architecture audit report from a ReviewRequest."""

    def __init__(self) -> None:
        self._scoring      = ArchitectureScoringService()
        self._cost         = CostAnalyzer()
        self._latency      = LatencyAnalyzer()
        self._observability = ObservabilityAnalyzer()
        self._production   = ProductionReadinessAnalyzer()
        self._rag          = RagAnalyzer()
        self._reliability  = ReliabilityAnalyzer()
        self._scalability  = ScalabilityAnalyzer()
        self._security     = SecurityAnalyzer()
        self._recs             = RecommendationEngine()
        self._advanced_recs    = AdvancedRecommendationEngine()
        self._exec_summary     = ExecutiveSummaryGenerator()
        self._intelligence     = IntelligenceLayer()
        self._health_aggregator = ArchitectureHealthAggregator()
        self._roadmap_generator = RoadmapGenerator()
        self._report_generator = ReportGenerator()

    def build(self, request: ReviewRequest) -> dict:
        """Return a complete architecture audit report.

        Args:
            request: The architecture review request.

        Returns:
            Structured report dict suitable for API responses and rendering.
        """
        # ── Run all analyzers ──────────────────────────────────────────────
        scoring_result      = self._scoring.analyze(request)
        cost_result         = self._cost.analyze(request)
        latency_result      = self._latency.analyze(request)
        production_result   = self._production.analyze(request)
        rag_result          = self._rag.analyze(request)
        reliability_result  = self._reliability.analyze(request)
        scalability_result  = self._scalability.analyze(request)
        security_result     = self._security.analyze(request)
        observability_result = self._observability.analyze(request)
        recommendations        = self._recs.generate(request)
        advanced_rec_report    = self._advanced_recs.generate(request)

        # ── Top findings: structured objects from every analyzer ──────────
        _order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        top_findings: list[dict] = []

        def _add(dimension: str, findings: list[dict]) -> None:
            for f in findings:
                top_findings.append({
                    "dimension": dimension,
                    "severity":  f["severity"],
                    "title":     f["title"],
                    "description": f["description"],
                    "impact":    f["impact"],
                })

        _add("Security",            security_result["findings"])
        _add("Reliability",         reliability_result["structured_findings"])
        _add("Production Readiness", production_result["findings"])
        _add("Observability",       observability_result["findings"])
        _add("Scalability",         scalability_result["findings"])
        _add("RAG Quality",         rag_result["findings"])
        _add("Cost",                cost_result["findings"])
        _add("Latency",             latency_result["findings"])

        top_findings.sort(key=lambda f: _order.get(f["severity"], 99))

        # ── Intelligence Summary ───────────────────────────────────────────
        intelligence_summary = self._intelligence.generate(
            overall_score=scoring_result["overall_score"],
            production_score=production_result["score"],
            top_findings=top_findings,
            recommendations=recommendations,
            advanced_rec_report=advanced_rec_report,
            project_name=request.project_name,
        )

        # ── Assemble report ────────────────────────────────────────────────
        report = {
            # ── Intelligence Summary (top-level) ──────────────────────────
            "intelligence_summary": intelligence_summary,

            "report_id": f"report-{uuid.uuid4().hex[:8]}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_name": request.project_name,

            # ── Architecture Score ─────────────────────────────────────────
            "architecture_score": {
                "overall_score":    scoring_result["overall_score"],
                "grade":            scoring_result["grade"],
                "dimension_scores": scoring_result["dimension_scores"],
            },

            # ── Production Readiness ───────────────────────────────────────
            "production_readiness": {
                "score":            production_result["score"],
                "grade":            production_result["grade"],
                "missing_features": production_result["missing_features"],
            },

            # ── Cost Analysis ──────────────────────────────────────────────
            "cost_analysis": {
                "estimated_monthly_tokens":  cost_result["estimated_monthly_tokens"],
                "estimated_monthly_cost":    cost_result["estimated_monthly_cost"],
                "potential_monthly_savings": cost_result["potential_monthly_savings"],
                "currency": "USD",
                "breakdown": cost_result.get("breakdown", {}),
            },

            # ── Latency Analysis ───────────────────────────────────────────
            "latency_analysis": {
                "estimated_latency_ms": latency_result["estimated_latency_ms"],
                "latency_rating":       latency_result["latency_rating"],
            },

            # ── Security Analysis ──────────────────────────────────────────
            "security_analysis": {
                "security_score":    security_result["security_score"],
                "severity":          _severity(security_result["security_score"]),
                "security_findings": security_result["security_findings"],
                "recommendations":   security_result["recommendations"],
            },

            # ── Reliability Analysis ───────────────────────────────────────
            "reliability_analysis": {
                "reliability_score": reliability_result["reliability_score"],
                "risk_level":        reliability_result["risk_level"],
                "findings":          reliability_result["findings"],
            },

            # ── Scalability Analysis ───────────────────────────────────────
            "scalability_analysis": {
                "scalability_score":  scalability_result["scalability_score"],
                "expected_capacity":  scalability_result["expected_capacity"],
                "recommendations":    scalability_result["recommendations"],
            },

            # ── Observability Analysis ─────────────────────────────────────
            "observability_analysis": {
                "observability_score": observability_result["observability_score"],
                "missing_features":    observability_result["missing_features"],
                "recommendations":     observability_result["recommendations"],
            },

            # ── RAG Analysis ───────────────────────────────────────────────
            "rag_analysis": {
                "rag_score":         rag_result["rag_score"],
                "retrieval_quality": rag_result["retrieval_quality"],
                "recommendations":   rag_result["recommendations"],
            },

            # ── Top Findings ───────────────────────────────────────────────
            "top_findings": top_findings,

            # ── Prioritised Recommendations ────────────────────────────────
            "recommendations": recommendations,

            # ── Rich Recommendations (advanced engine, for roadmap) ─────────
            "rich_recommendations": advanced_rec_report["recommendations"],

            # ── Executive Summary ──────────────────────────────────────────
            "executive_summary": self._exec_summary.generate(
                request=request,
                overall_score=scoring_result["overall_score"],
                production_score=production_result["score"],
                grade=scoring_result["grade"],
                top_findings=top_findings,
                recommendations=recommendations,
                analyzer_results={
                    "rag":           rag_result,
                    "security":      security_result,
                    "reliability":   reliability_result,
                    "scalability":   scalability_result,
                    "observability": observability_result,
                    "cost":          cost_result,
                    "latency":       latency_result,
                },
                advanced_rec_report=advanced_rec_report,
            ),
        }

        report["dynamic_roadmap"] = self._roadmap_generator.generate(
            recommendations=advanced_rec_report["recommendations"],
            request=request,
        )

        report["architecture_health"] = self._health_aggregator.aggregate(
            request=request,
            cost_result=cost_result,
            latency_result=latency_result,
            reliability_result=reliability_result,
            scalability_result=scalability_result,
        )

        report["audit_report"] = self._report_generator.generate(report)

        return report
