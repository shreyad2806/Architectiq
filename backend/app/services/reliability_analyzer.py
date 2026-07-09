"""ReliabilityAnalyzer service.

Evaluates the reliability of a production AI architecture based on
resilience and security characteristics from a ReviewRequest.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ReviewRequest


@dataclass(frozen=True)
class _Check:
    feature: str
    points: int
    finding: str


# Each check contributes `points` when the feature is ABSENT (deduction model).
# We start at 100 and subtract for each missing feature.
CHECKS: list[_Check] = [
    _Check(
        "retry_strategy",
        25,
        "No retry strategy: transient LLM/network failures will surface directly to users.",
    ),
    _Check(
        "rate_limiting",
        20,
        "No rate limiting: the service is vulnerable to traffic spikes and abuse.",
    ),
    _Check(
        "authentication",
        20,
        "No authentication: API endpoints are publicly accessible without credentials.",
    ),
    _Check(
        "cache_enabled",
        15,
        "No caching: every request hits the LLM, increasing cost and failure surface.",
    ),
    _Check(
        "memory",
        10,
        "No session memory: stateless design may cause inconsistent multi-turn behaviour.",
    ),
]

# Risk thresholds
_RISK_LEVELS: list[tuple[int, str]] = [
    (80, "Low"),
    (50, "Medium"),
    (0,  "High"),
]


def _risk_level(score: int) -> str:
    for threshold, label in _RISK_LEVELS:
        if score >= threshold:
            return label
    return "High"


class ReliabilityAnalyzer:
    """Score the reliability and risk level of an AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``reliability_score``, ``risk_level``, and ``findings``.

        Scoring: starts at 100, deducts points for each absent reliability
        feature. Findings explain every deduction made.

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with:
            - ``reliability_score`` int 0–100
            - ``risk_level``        str  Low | Medium | High
            - ``findings``          list[str] explaining each deduction
        """
        score = 100
        findings: list[str] = []

        for check in CHECKS:
            value = getattr(request, check.feature, False)
            if not value:
                score -= check.points
                findings.append(check.finding)

        score = max(score, 0)

        return {
            "reliability_score": score,
            "risk_level": _risk_level(score),
            "findings": findings,
        }
