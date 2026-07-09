"""Recommender that converts architecture rule findings into prioritized recommendations."""

from __future__ import annotations

import uuid
from typing import Any

from app.rules import RuleFinding
from app.schemas import RecommendationResponse


# Latency improvement estimates in milliseconds for each rule category.
DEFAULT_LATENCY_IMPROVEMENT_MS: dict[str, float] = {
    "large-prompts-input": 400.0,
    "large-prompts-output": 200.0,
    "missing-retry": 150.0,
    "missing-caching": 350.0,
    "no-observability": 0.0,
    "no-monitoring": 0.0,
    "large-traffic": 0.0,
    "high-traffic": 0.0,
    "expensive-model": 100.0,
    "vector-db-replicas": 300.0,
    "vector-db-index": 150.0,
}


def _severity_weight(severity: str) -> int:
    """Map severity string to a numeric weight for sorting."""
    return {"high": 3, "medium": 2, "low": 1}.get(severity.lower(), 0)


def _compute_latency_improvement(finding: RuleFinding) -> float:
    """Return an estimated latency improvement in milliseconds for a finding."""
    if finding.estimated_latency_improvement_ms is not None:
        return finding.estimated_latency_improvement_ms
    return DEFAULT_LATENCY_IMPROVEMENT_MS.get(finding.rule_id, 0.0)


def _compute_savings(finding: RuleFinding) -> float:
    """Return a concrete savings estimate. Falls back to 0 if not provided."""
    return float(finding.estimated_monthly_savings or 0.0)


def _compute_impact_score(recommendation: RecommendationResponse) -> float:
    """Compute an impact score used to sort recommendations.

    Score combines severity, savings, and latency improvement."""
    severity = _severity_weight(recommendation.priority)
    savings = recommendation.estimated_monthly_savings or 0.0
    latency = recommendation.estimated_latency_improvement_ms or 0.0

    # Severity has the largest weight; savings and latency provide a secondary tie-break.
    return severity * 1000 + (savings / 10) + (latency / 5)


def _build_recommendation(finding: RuleFinding, index: int) -> RecommendationResponse:
    """Map a single rule finding to a structured recommendation."""
    latency_improvement = _compute_latency_improvement(finding)
    savings = _compute_savings(finding)

    return RecommendationResponse(
        id=f"rec-{index:03d}-{uuid.uuid4().hex[:6]}",
        title=finding.title,
        description=finding.description,
        category=finding.category,
        priority=finding.severity,
        estimated_monthly_savings=savings if savings > 0 else None,
        implementation_effort=finding.implementation_effort,
        estimated_latency_improvement_ms=latency_improvement if latency_improvement > 0 else None,
    )


def prioritize_recommendations(findings: list[RuleFinding]) -> list[RecommendationResponse]:
    """Convert findings into prioritized recommendations sorted by impact.

    Args:
        findings: List of rule findings produced by the architecture analyzer.

    Returns:
        List of ``RecommendationResponse`` objects sorted by impact score descending.
    """
    recommendations = [
        _build_recommendation(finding, index) for index, finding in enumerate(findings)
    ]
    recommendations.sort(key=_compute_impact_score, reverse=True)
    return recommendations


def recommend(
    findings: list[RuleFinding],
    top_k: int | None = None,
) -> list[RecommendationResponse]:
    """Public alias for ``prioritize_recommendations`` with optional top-k limit.

    Args:
        findings: List of rule findings.
        top_k: Optional maximum number of recommendations to return.

    Returns:
        Prioritized list of recommendations, optionally truncated to ``top_k``.
    """
    recommendations = prioritize_recommendations(findings)
    if top_k is not None:
        return recommendations[:top_k]
    return recommendations
