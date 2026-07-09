"""ProductionReadinessAnalyzer service.

Calculates a production readiness score out of 100 based on the
architecture features declared in a ReviewRequest.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ReviewRequest


def _finding(severity: str, title: str, description: str, impact: str) -> dict:
    return {"severity": severity, "title": title, "description": description, "impact": impact}


@dataclass(frozen=True)
class _Check:
    feature: str
    description: str
    weight: int
    finding_severity: str
    finding_title: str
    finding_description: str
    finding_impact: str


# Each check contributes `weight` points to the total score (sum == 100).
CHECKS: list[_Check] = [
    _Check(
        "authentication", "API authentication is enabled", 20,
        "HIGH", "Authentication Missing",
        "No authentication is configured. Production APIs must require credentials to prevent unauthorised access.",
        "High",
    ),
    _Check(
        "retry_strategy", "Retry and failover strategy is implemented", 20,
        "HIGH", "Retry Strategy Missing",
        "Without retries, transient LLM or network failures will propagate to end users and degrade reliability.",
        "High",
    ),
    _Check(
        "rate_limiting", "Rate limiting is enforced", 15,
        "HIGH", "Rate Limiting Disabled",
        "No rate limiting exposes the service to traffic spikes and abuse, risking LLM quota exhaustion.",
        "High",
    ),
    _Check(
        "observability", "Observability and tracing are configured", 20,
        "MEDIUM", "Observability Missing",
        "Without observability you cannot diagnose incidents, measure SLOs, or detect regressions in production.",
        "Medium",
    ),
    _Check(
        "cache_enabled", "Response / semantic caching is enabled", 15,
        "MEDIUM", "No Caching Configured",
        "Every request hits the LLM directly, increasing cost, latency, and the blast radius of provider outages.",
        "Medium",
    ),
    _Check(
        "memory", "Session memory or state management is present", 10,
        "LOW", "Session Memory Absent",
        "Stateless design may produce inconsistent responses across multi-turn conversations.",
        "Low",
    ),
]

# Grade thresholds
_GRADES = [
    (95, "A+"),
    (80, "A"),
    (60, "B"),
    (0,  "C"),
]


def _grade(score: int) -> str:
    for threshold, label in _GRADES:
        if score >= threshold:
            return label
    return "C"


class ProductionReadinessAnalyzer:
    """Score the production readiness of an AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``score``, ``grade``, and ``missing_features``.

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with:
            - ``score``            int 0–100
            - ``grade``            str  A+ | A | B | C
            - ``missing_features`` list[str] of failing check descriptions
        """
        score = 0
        missing: list[str] = []
        findings: list[dict] = []

        for check in CHECKS:
            value = getattr(request, check.feature, False)
            if value:
                score += check.weight
            else:
                missing.append(check.description)
                findings.append(_finding(
                    check.finding_severity,
                    check.finding_title,
                    check.finding_description,
                    check.finding_impact,
                ))

        return {
            "score": score,
            "grade": _grade(score),
            "missing_features": missing,
            "findings": findings,
        }
