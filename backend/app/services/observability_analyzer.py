"""ObservabilityAnalyzer service.

Evaluates the observability posture of a production AI architecture based on
logging, monitoring, tracing, metrics, and health endpoint configuration.
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
    missing_feature: str
    recommendation: str
    severity: str
    title: str
    description: str
    impact: str


# Deduction model: start at 100, subtract for each absent observability pillar.
CHECKS: list[_Check] = [
    _Check(
        feature="logging", points=25,
        missing_feature="Structured logging",
        recommendation="Enable structured logging (e.g. JSON logs via loguru or structlog) to capture request context and errors.",
        severity="HIGH", title="No Structured Logging",
        description="Without structured logging, debugging production incidents is extremely difficult. Log every request, LLM call, and error with contextual metadata.",
        impact="High",
    ),
    _Check(
        feature="monitoring", points=25,
        missing_feature="Monitoring solution",
        recommendation="Integrate a monitoring platform (e.g. Prometheus + Grafana, Datadog) to track system health in real time.",
        severity="HIGH", title="No Monitoring Configured",
        description="No monitoring means silent failures and degraded performance go undetected. You will discover problems only after users report them.",
        impact="High",
    ),
    _Check(
        feature="tracing", points=20,
        missing_feature="Distributed tracing",
        recommendation="Add distributed tracing (e.g. OpenTelemetry with Jaeger or Tempo) to diagnose latency across services.",
        severity="MEDIUM", title="Distributed Tracing Missing",
        description="Without tracing you cannot correlate latency across LLM calls, vector DB queries, and API responses, making performance diagnosis nearly impossible.",
        impact="Medium",
    ),
    _Check(
        feature="metrics", points=20,
        missing_feature="Application metrics collection",
        recommendation="Export application metrics (request counts, token usage, error rates) to a metrics backend.",
        severity="MEDIUM", title="No Application Metrics",
        description="Without metrics you cannot set SLOs, detect regressions, or build dashboards that reflect actual production behaviour.",
        impact="Medium",
    ),
    _Check(
        feature="health_endpoint", points=10,
        missing_feature="Health check endpoint",
        recommendation="Expose a /health endpoint so load balancers and orchestrators can verify service readiness.",
        severity="LOW", title="No Health Check Endpoint",
        description="Orchestration platforms (Kubernetes, ECS) rely on health endpoints to route traffic. Without one, unhealthy instances continue to receive requests.",
        impact="Low",
    ),
]


class ObservabilityAnalyzer:
    """Score the observability posture of an AI architecture."""

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``observability_score``, ``missing_features``, and ``recommendations``.

        Scoring: starts at 100, deducts points for each absent observability
        pillar.

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with:
            - ``observability_score`` int 0–100
            - ``missing_features``    list[str] naming each absent pillar
            - ``recommendations``     list[str] with actionable fixes
        """
        score = 100
        missing_features: list[str] = []
        recommendations: list[str] = []
        findings: list[dict] = []

        for check in CHECKS:
            value = getattr(request, check.feature, False)
            if not value:
                score -= check.points
                missing_features.append(check.missing_feature)
                recommendations.append(check.recommendation)
                findings.append(_finding(
                    check.severity, check.title, check.description, check.impact
                ))

        score = max(score, 0)

        return {
            "observability_score": score,
            "missing_features": missing_features,
            "recommendations": recommendations,
            "findings": findings,
        }
