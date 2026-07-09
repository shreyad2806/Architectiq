"""Architecture review pipeline.

This module orchestrates the end-to-end review process: running rules, estimating
cost and latency, generating recommendations, and computing scores. It does not use
AI models — only engineering heuristics.
"""

from __future__ import annotations

import uuid

from app.rules import analyze_architecture
from app.schemas import (
    ArchitectureRequest,
    EstimateResponse,
    RecommendationResponse,
    ReviewResponse,
)
from app.services.estimator import (
    estimate_latency,
    estimate_monthly_cost,
    estimate_monthly_tokens,
    estimate_savings,
)
from app.services.recommender import recommend


# Score weights and baseline constants.
_SEVERITY_PENALTY = {
    "high": 8,
    "medium": 4,
    "low": 1,
}

_MAX_SCORE = 100


def _detect_primary_model(components: list) -> str:
    """Return the first LLM model name found in the architecture components.

    Normalizes legacy or variant names to a supported estimator model key.
    Accepts both plain dicts and Pydantic ``Component`` models.
    """
    _MODEL_ALIASES = {
        "gpt-4": "gpt-4o",
        "gpt-4-turbo": "gpt-4o",
        "gpt-4-turbo-preview": "gpt-4o",
        "claude-3-opus": "claude-sonnet",
        "claude-3.5-sonnet": "claude-sonnet",
        "claude-3.5-sonnet-4k": "claude-sonnet-4",
        "gemini-1.5-pro": "gemini-2.5-pro",
    }

    for component in components:
        component_type = getattr(component, "type", None)
        component_model = getattr(component, "model", None)
        if component_type is None:
            component_type = component.get("type")
            component_model = component.get("model")

        if component_type == "llm":
            model = (component_model or "").lower()
            if model:
                return _MODEL_ALIASES.get(model, model)
    return "gpt-4o"


def _architecture_score(findings: list, latency: float) -> int:
    """Compute the overall architecture score from 0 to 100.

    Starts at 100 and deducts points for each finding based on severity.
    Latency adds a small penalty to the score.
    """
    score = _MAX_SCORE
    for finding in findings:
        severity = getattr(finding, "severity", "low").lower()
        score -= _SEVERITY_PENALTY.get(severity, 1)

    # Latency penalty: requests taking longer than 5 seconds lose points.
    if latency > 5000:
        score -= 5
    if latency > 10000:
        score -= 5

    return max(0, min(_MAX_SCORE, score))


def _production_readiness_score(findings: list) -> int:
    """Compute the production readiness score from 0 to 100.

    Penalizes reliability and observability findings more heavily.
    """
    score = _MAX_SCORE
    for finding in findings:
        category = getattr(finding, "category", "").lower()
        severity = getattr(finding, "severity", "low").lower()
        base = _SEVERITY_PENALTY.get(severity, 1)

        # Reliability and observability issues are critical for production readiness.
        if category in {"reliability", "observability"}:
            score -= base * 2
        else:
            score -= base

    return max(0, min(_MAX_SCORE, score))


def _build_summary(recommendations: list[RecommendationResponse]) -> str:
    """Generate a concise human-readable summary of the review."""
    if not recommendations:
        return "No significant issues found. The architecture looks production-ready."

    high = sum(1 for r in recommendations if r.priority == "high")
    medium = sum(1 for r in recommendations if r.priority == "medium")
    low = sum(1 for r in recommendations if r.priority == "low")

    return (
        f"Review found {high} high, {medium} medium, and {low} low priority "
        f"improvements. Address high-priority reliability and cost issues first."
    )


def review(architecture: ArchitectureRequest) -> ReviewResponse:
    """Run the complete architecture review pipeline.

    Args:
        architecture: Validated architecture request.

    Returns:
        A single ``ReviewResponse`` containing scores, cost estimate, and
        prioritized recommendations.
    """
    # Prepare the architecture dict consumed by rules and estimators.
    architecture_dict = architecture.model_dump()

    # 1. Run architecture rules.
    findings = analyze_architecture(architecture_dict)

    # 2. Estimate cost and latency.
    requests_per_month = architecture.estimated_requests_per_month or 0
    avg_input_tokens = architecture.average_input_tokens
    avg_output_tokens = architecture.average_output_tokens
    primary_model = _detect_primary_model(architecture.components)

    monthly_tokens = estimate_monthly_tokens(
        requests_per_month=requests_per_month,
        avg_input_tokens=avg_input_tokens,
        avg_output_tokens=avg_output_tokens,
    )

    total_monthly_cost = estimate_monthly_cost(
        model=primary_model,
        requests_per_month=requests_per_month,
        avg_input_tokens=avg_input_tokens,
        avg_output_tokens=avg_output_tokens,
    )

    current_latency_ms = estimate_latency(
        model=primary_model,
        avg_input_tokens=avg_input_tokens,
        avg_output_tokens=avg_output_tokens,
    )

    savings = estimate_savings(
        current_model=primary_model,
        requests_per_month=requests_per_month,
        avg_input_tokens=avg_input_tokens,
        avg_output_tokens=avg_output_tokens,
    )

    # 3. Generate prioritized recommendations.
    recommendations = recommend(findings)

    # 4. Compute scores.
    overall_score = _architecture_score(findings, current_latency_ms)
    production_readiness = _production_readiness_score(findings)

    # 5. Build the cost estimate response.
    cost_estimate = EstimateResponse(
        total_monthly_cost=total_monthly_cost,
        model_costs=[
            {
                "component": primary_model,
                "monthly_cost": total_monthly_cost,
            }
        ],
        tokens=monthly_tokens,
        average_latency_ms=current_latency_ms,
        potential_monthly_savings=savings["monthly_savings"],
        currency="USD",
    )

    # 6. Build summary.
    summary = _build_summary(recommendations)

    return ReviewResponse(
        id=f"rev-{uuid.uuid4().hex[:8]}",
        architecture_name=architecture.name,
        overall_score=overall_score,
        production_readiness=production_readiness,
        cost_estimate=cost_estimate,
        recommendations=recommendations,
        summary=summary,
    )
