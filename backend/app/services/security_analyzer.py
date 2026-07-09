"""SecurityAnalyzer service.

Evaluates the security posture of a production AI architecture based on
authentication, rate limiting, prompt injection protection, and input
validation characteristics from a ReviewRequest.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ReviewRequest


@dataclass(frozen=True)
class _Check:
    feature: str
    points: int
    finding: str
    recommendation: str


# Deduction model: start at 100, subtract for each missing security feature.
CHECKS: list[_Check] = [
    _Check(
        feature="authentication",
        points=35,
        finding="No authentication: API endpoints are publicly accessible without credentials.",
        recommendation="Implement API key or OAuth 2.0 / JWT authentication to restrict access.",
    ),
    _Check(
        feature="rate_limiting",
        points=25,
        finding="No rate limiting: the service is exposed to brute-force and denial-of-service attacks.",
        recommendation="Add rate limiting (e.g. token-bucket or sliding-window) to prevent abuse.",
    ),
    _Check(
        feature="prompt_injection_protection",
        points=25,
        finding="No prompt injection protection: malicious users can manipulate LLM behaviour via crafted inputs.",
        recommendation="Sanitise and validate user inputs before injecting them into prompts; consider a guardrails layer.",
    ),
    _Check(
        feature="input_validation",
        points=15,
        finding="No input validation: unvalidated payloads increase the risk of injection and unexpected model behaviour.",
        recommendation="Enforce strict schema validation (e.g. Pydantic) and reject malformed or oversized requests.",
    ),
]


class SecurityAnalyzer:
    """Score the security posture of an AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``security_score``, ``security_findings``, and ``recommendations``.

        Scoring: starts at 100, deducts points for each absent security
        control.  Both findings and recommendations are populated for every
        failing check so callers can surface them independently.

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with:
            - ``security_score``    int 0–100
            - ``security_findings`` list[str] describing each gap
            - ``recommendations``   list[str] with actionable fixes
        """
        score = 100
        findings: list[str] = []
        recommendations: list[str] = []

        for check in CHECKS:
            value = getattr(request, check.feature, False)
            if not value:
                score -= check.points
                findings.append(check.finding)
                recommendations.append(check.recommendation)

        score = max(score, 0)

        return {
            "security_score": score,
            "security_findings": findings,
            "recommendations": recommendations,
        }
