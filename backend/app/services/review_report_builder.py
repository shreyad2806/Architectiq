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
from app.services.recommendation_engine import RecommendationEngine


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


def _executive_summary(
    project_name: str,
    overall_score: int,
    grade: str,
    top_findings: list[dict],
    recommendations: list[dict],
) -> str:
    high_recs = [r for r in recommendations if r["priority"] == "HIGH"]
    n_findings = len(top_findings)
    n_high = len(high_recs)

    severity_label = "excellent" if overall_score >= 85 else (
        "good" if overall_score >= 70 else (
            "fair" if overall_score >= 50 else "poor"
        )
    )

    parts = [
        f"{project_name} received an overall architecture score of {overall_score}/100 (grade: {grade}), "
        f"indicating {severity_label} production readiness."
    ]

    if n_findings:
        parts.append(
            f"The review surfaced {n_findings} finding{'s' if n_findings != 1 else ''} "
            f"across security, reliability, observability, and RAG quality dimensions."
        )

    if n_high:
        parts.append(
            f"There {'are' if n_high > 1 else 'is'} {n_high} high-priority recommendation{'s' if n_high != 1 else ''} "
            "that should be addressed before production deployment."
        )
    else:
        parts.append("No high-priority issues were identified.")

    return " ".join(parts)


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
        self._recs         = RecommendationEngine()

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
        recommendations     = self._recs.generate(request)

        # ── Top findings: collect all critical/warning signals ─────────────
        top_findings: list[dict] = []

        for finding in security_result["security_findings"]:
            top_findings.append({"dimension": "Security", "severity": "HIGH", "detail": finding})

        for finding in reliability_result["findings"]:
            top_findings.append({"dimension": "Reliability", "severity": "HIGH", "detail": finding})

        for missing in production_result["missing_features"]:
            top_findings.append({"dimension": "Production Readiness", "severity": "MEDIUM", "detail": missing})

        for missing in observability_result["missing_features"]:
            top_findings.append({"dimension": "Observability", "severity": "MEDIUM", "detail": missing})

        for rec in rag_result["recommendations"]:
            top_findings.append({"dimension": "RAG Quality", "severity": "LOW", "detail": rec})

        for rec in scalability_result["recommendations"]:
            top_findings.append({"dimension": "Scalability", "severity": "LOW", "detail": rec})

        # Sort: HIGH first, then MEDIUM, then LOW
        _order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        top_findings.sort(key=lambda f: _order.get(f["severity"], 99))

        # ── Assemble report ────────────────────────────────────────────────
        report = {
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
                "estimated_monthly_tokens": cost_result["estimated_monthly_tokens"],
                "estimated_monthly_cost":   cost_result["estimated_monthly_cost"],
                "potential_monthly_savings": cost_result["potential_monthly_savings"],
                "currency": "USD",
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

            # ── Executive Summary ──────────────────────────────────────────
            "executive_summary": _executive_summary(
                project_name=request.project_name,
                overall_score=scoring_result["overall_score"],
                grade=scoring_result["grade"],
                top_findings=top_findings,
                recommendations=recommendations,
            ),
        }

        return report
