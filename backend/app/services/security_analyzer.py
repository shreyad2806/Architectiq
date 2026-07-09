"""SecurityAnalyzer service.

Evaluates the security posture of a production AI architecture based on
authentication, rate limiting, prompt injection protection, and input
validation characteristics from a ReviewRequest.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ReviewRequest


def _finding(severity: str, title: str, description: str, impact: str) -> dict:
    return {"severity": severity, "title": title, "description": description, "impact": impact}


@dataclass(frozen=True)
class _Check:
    feature: str
    points: int
    finding: str
    recommendation: str
    severity: str
    title: str
    description: str
    impact: str


# Deduction model: start at 100, subtract for each missing security feature.
CHECKS: list[_Check] = [
    _Check(
        feature="authentication", points=35,
        finding="No authentication: API endpoints are publicly accessible without credentials.",
        recommendation="Implement API key or OAuth 2.0 / JWT authentication to restrict access.",
        severity="HIGH", title="Authentication Disabled",
        description="Production APIs should require authentication. Without it any client can call the API freely, risking data leakage and cost overruns.",
        impact="High",
    ),
    _Check(
        feature="rate_limiting", points=25,
        finding="No rate limiting: the service is exposed to brute-force and denial-of-service attacks.",
        recommendation="Add rate limiting (e.g. token-bucket or sliding-window) to prevent abuse.",
        severity="HIGH", title="Rate Limiting Missing",
        description="The service is vulnerable to abuse under high traffic. Without rate limits, a single bad actor can exhaust LLM quotas for all users.",
        impact="High",
    ),
    _Check(
        feature="prompt_injection_protection", points=25,
        finding="No prompt injection protection: malicious users can manipulate LLM behaviour via crafted inputs.",
        recommendation="Sanitise and validate user inputs before injecting them into prompts; consider a guardrails layer.",
        severity="HIGH", title="No Prompt Injection Protection",
        description="Without guardrails, crafted user inputs can override system instructions and exfiltrate sensitive context or produce harmful outputs.",
        impact="High",
    ),
    _Check(
        feature="input_validation", points=15,
        finding="No input validation: unvalidated payloads increase the risk of injection and unexpected model behaviour.",
        recommendation="Enforce strict schema validation (e.g. Pydantic) and reject malformed or oversized requests.",
        severity="MEDIUM", title="Input Validation Missing",
        description="Unvalidated input may contain malformed data, overly large payloads, or injection vectors that bypass application logic.",
        impact="Medium",
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
        structured_findings: list[dict] = []

        for check in CHECKS:
            value = getattr(request, check.feature, False)
            if not value:
                score -= check.points
                findings.append(check.finding)
                recommendations.append(check.recommendation)
                structured_findings.append(_finding(
                    check.severity, check.title, check.description, check.impact
                ))

        score = max(score, 0)

        return {
            "security_score": score,
            "security_findings": findings,
            "recommendations": recommendations,
            "findings": structured_findings,
        }
