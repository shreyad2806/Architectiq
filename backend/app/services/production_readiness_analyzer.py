"""ProductionReadinessAnalyzer service.

Calculates a production readiness score out of 100 based on the
architecture features declared in a ReviewRequest.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ReviewRequest


@dataclass(frozen=True)
class _Check:
    feature: str
    description: str
    weight: int


# Each check contributes `weight` points to the total score (sum == 100).
CHECKS: list[_Check] = [
    _Check("authentication", "API authentication is enabled", 20),
    _Check("retry_strategy", "Retry and failover strategy is implemented", 20),
    _Check("rate_limiting", "Rate limiting is enforced", 15),
    _Check("observability", "Observability and tracing are configured", 20),
    _Check("cache_enabled", "Response / semantic caching is enabled", 15),
    _Check("memory", "Session memory or state management is present", 10),
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

        for check in CHECKS:
            value = getattr(request, check.feature, False)
            if value:
                score += check.weight
            else:
                missing.append(check.description)

        return {
            "score": score,
            "grade": _grade(score),
            "missing_features": missing,
        }
