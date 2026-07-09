"""IntelligenceLayer.

Aggregates all analyzer outputs and the Recommendation Engine into a single
top-level ``intelligence_summary`` object.  All computation is deterministic
and reuses already-executed analyzer results — no additional API or LLM calls.
"""

from __future__ import annotations

from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# AI Maturity Level thresholds
# ---------------------------------------------------------------------------

_MATURITY_LEVELS: list[tuple[int, int, str]] = [
    (95, 5, "Enterprise Optimized"),
    (85, 4, "Production Ready"),
    (70, 3, "Scaling"),
    (50, 2, "Development"),
    (0,  1, "Prototype"),
]


def _maturity(score: int) -> dict:
    for threshold, level, title in _MATURITY_LEVELS:
        if score >= threshold:
            return {"level": level, "title": title}
    return {"level": 1, "title": "Prototype"}


# ---------------------------------------------------------------------------
# Overall verdict
# ---------------------------------------------------------------------------

_VERDICT_THRESHOLDS: list[tuple[int, str]] = [
    (95, "Enterprise Ready"),
    (85, "Production Ready"),
    (70, "Production Ready with Improvements"),
    (50, "Needs Optimization"),
    (0,  "Prototype"),
]


def _verdict(score: int) -> str:
    for threshold, label in _VERDICT_THRESHOLDS:
        if score >= threshold:
            return label
    return "Prototype"


# ---------------------------------------------------------------------------
# Critical risks — only HIGH severity findings
# ---------------------------------------------------------------------------

def _critical_risks(top_findings: list[dict]) -> list[str]:
    """Return unique titles of HIGH-severity findings."""
    seen: set[str] = set()
    risks: list[str] = []
    for f in top_findings:
        if f.get("severity") != "HIGH":
            continue
        title = f.get("title", "").strip()
        if title and title not in seen:
            seen.add(title)
            risks.append(title)
    return risks


# ---------------------------------------------------------------------------
# Top priorities — three highest-impact recommendations
# ---------------------------------------------------------------------------

def _top_priorities(recommendations: list[dict]) -> list[str]:
    """Return titles of the top 3 recommendations (already priority-sorted)."""
    return [r["title"] for r in recommendations[:3] if r.get("title")]


# ---------------------------------------------------------------------------
# Executive summary narrative (≤100 words)
# ---------------------------------------------------------------------------

def _executive_narrative(
    project_name: str,
    overall_score: int,
    verdict: str,
    n_high_risks: int,
    n_recs: int,
    estimated_saving: str,
    latency_improvement: str,
    production_score: int,
) -> str:
    quality = (
        "technically sound"        if overall_score >= 80 else
        "functionally capable"     if overall_score >= 65 else
        "functional but immature"
    )

    risk_note = (
        f" {n_high_risks} critical risk{'s require' if n_high_risks != 1 else ' requires'} immediate attention."
        if n_high_risks > 0 else " No critical risks were identified."
    )

    saving_note = (
        f" Addressing the {n_recs} identified recommendation{'s' if n_recs != 1 else ''} "
        f"could reduce monthly inference costs by approximately {estimated_saving} "
        f"and improve response latency by {latency_improvement}."
        if estimated_saving != "$0" else ""
    )

    pr_note = (
        " The system meets production readiness standards."
        if production_score >= 80
        else f" Production readiness is at {production_score}/100 and needs improvement before full deployment."
    )

    return (
        f"ArchitectIQ analyzed your AI architecture and found it {quality} "
        f"with several opportunities to reduce operational cost and improve production resilience."
        f"{risk_note}{pr_note}{saving_note}"
    ).strip()


# ---------------------------------------------------------------------------
# Intelligence Layer
# ---------------------------------------------------------------------------

class IntelligenceLayer:
    """Aggregate all analyzer outputs into a concise intelligence_summary."""

    def generate(
        self,
        overall_score: int,
        production_score: int,
        top_findings: list[dict],
        recommendations: list[dict],
        cost_result: dict,
        advanced_rec_report: dict,
    ) -> dict:
        """Return the ``intelligence_summary`` dict.

        Args:
            overall_score:        Weighted architecture score (0-100).
            production_score:     Production readiness score (0-100).
            top_findings:         Severity-sorted findings from ReviewReportBuilder.
            recommendations:      Priority-sorted recommendations (legacy shape).
            cost_result:          Raw output from CostAnalyzer.analyze().
            advanced_rec_report:  Output from AdvancedRecommendationEngine.generate().

        Returns:
            Dict with keys: overall_verdict, architecture_score,
            ai_maturity_level, executive_summary, critical_risks,
            top_priorities, estimated_monthly_savings,
            estimated_latency_improvement.
        """
        estimated_saving     = advanced_rec_report["total_estimated_monthly_savings"]
        latency_improvement  = advanced_rec_report["estimated_latency_improvement"]
        rich_recs            = advanced_rec_report["recommendations"]

        critical_risks  = _critical_risks(top_findings)
        top_priorities  = _top_priorities(rich_recs if rich_recs else recommendations)
        n_high_risks    = len(critical_risks)

        narrative = _executive_narrative(
            project_name="your AI architecture",
            overall_score=overall_score,
            verdict=_verdict(overall_score),
            n_high_risks=n_high_risks,
            n_recs=len(recommendations),
            estimated_saving=estimated_saving,
            latency_improvement=latency_improvement,
            production_score=production_score,
        )

        return {
            "overall_verdict":              _verdict(overall_score),
            "architecture_score":           overall_score,
            "ai_maturity_level":            _maturity(overall_score),
            "executive_summary":            narrative,
            "critical_risks":               critical_risks,
            "top_priorities":               top_priorities,
            "estimated_monthly_savings":    estimated_saving,
            "estimated_latency_improvement": latency_improvement,
        }
