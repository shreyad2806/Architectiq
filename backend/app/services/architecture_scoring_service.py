"""ArchitectureScoringService.

Combines all individual analyzer scores into a single weighted overall score
with a letter grade.
"""

from __future__ import annotations

from app.schemas import ReviewRequest
from app.services.cost_analyzer import CostAnalyzer
from app.services.latency_analyzer import LatencyAnalyzer
from app.services.observability_analyzer import ObservabilityAnalyzer
from app.services.production_readiness_analyzer import ProductionReadinessAnalyzer
from app.services.rag_analyzer import RagAnalyzer
from app.services.reliability_analyzer import ReliabilityAnalyzer
from app.services.scalability_analyzer import ScalabilityAnalyzer
from app.services.security_analyzer import SecurityAnalyzer


# ---------------------------------------------------------------------------
# Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
WEIGHTS: dict[str, float] = {
    "production":   0.20,
    "security":     0.15,
    "reliability":  0.15,
    "scalability":  0.15,
    "rag":          0.15,
    "latency":      0.10,
    "cost":         0.05,
    "observability": 0.05,
}

# Grade thresholds
_GRADES: list[tuple[int, str]] = [
    (85, "Excellent"),
    (70, "Good"),
    (50, "Average"),
    (0,  "Poor"),
]

# Latency: convert ms → 0-100 score (lower is better)
_LATENCY_MAX_MS = 2_000.0

# Cost: convert monthly cost → 0-100 score (lower is better).
# Reference ceiling: $10 000 / month maps to score 0.
_COST_CEILING_USD = 10_000.0


def _grade(score: int) -> str:
    for threshold, label in _GRADES:
        if score >= threshold:
            return label
    return "Poor"


def _latency_to_score(latency_ms: float) -> int:
    """Invert latency so lower latency → higher score (0-100)."""
    score = max(0.0, 1.0 - latency_ms / _LATENCY_MAX_MS) * 100
    return round(score)


def _cost_to_score(monthly_cost: float) -> int:
    """Invert cost so lower cost → higher score (0-100)."""
    score = max(0.0, 1.0 - monthly_cost / _COST_CEILING_USD) * 100
    return round(score)


class ArchitectureScoringService:
    """Produce a single weighted overall score for an AI architecture."""

    def __init__(self) -> None:
        self._production = ProductionReadinessAnalyzer()
        self._security = SecurityAnalyzer()
        self._reliability = ReliabilityAnalyzer()
        self._scalability = ScalabilityAnalyzer()
        self._rag = RagAnalyzer()
        self._latency = LatencyAnalyzer()
        self._cost = CostAnalyzer()
        self._observability = ObservabilityAnalyzer()

    def analyze(self, request: ReviewRequest) -> dict:
        """Return ``overall_score``, ``grade``, and ``dimension_scores``.

        Args:
            request: The architecture review request.

        Returns:
            Dictionary with:
            - ``overall_score``    int 0–100
            - ``grade``            str  Excellent | Good | Average | Poor
            - ``dimension_scores`` dict mapping each dimension to its raw score
        """
        production_score   = self._production.analyze(request)["score"]
        security_score     = self._security.analyze(request)["security_score"]
        reliability_score  = self._reliability.analyze(request)["reliability_score"]
        scalability_score  = self._scalability.analyze(request)["scalability_score"]
        rag_score          = self._rag.analyze(request)["rag_score"]
        latency_score      = _latency_to_score(self._latency.analyze(request)["estimated_latency_ms"])
        cost_score         = _cost_to_score(self._cost.analyze(request)["estimated_monthly_cost"])
        observability_score = self._observability.analyze(request)["observability_score"]

        dimension_scores = {
            "production":    production_score,
            "security":      security_score,
            "reliability":   reliability_score,
            "scalability":   scalability_score,
            "rag":           rag_score,
            "latency":       latency_score,
            "cost":          cost_score,
            "observability": observability_score,
        }

        overall = sum(
            dimension_scores[dim] * weight
            for dim, weight in WEIGHTS.items()
        )
        overall_score = round(overall)

        return {
            "overall_score":    overall_score,
            "grade":            _grade(overall_score),
            "dimension_scores": dimension_scores,
        }
