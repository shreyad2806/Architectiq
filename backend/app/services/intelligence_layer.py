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
# Consulting-grade executive narrative
# ---------------------------------------------------------------------------

_DIMENSIONS_REVIEWED = (
    "cost efficiency, reliability, scalability, security, latency, and RAG retrieval quality"
)

_FINAL_REC_THRESHOLDS: list[tuple[int, str]] = [
    (90, (
        "The architecture demonstrates strong engineering discipline. "
        "The recommended optimizations are incremental improvements that will push performance "
        "and cost efficiency to enterprise-grade standards."
    )),
    (75, (
        "With the identified improvements in place, this system can meet production "
        "reliability and cost targets. Prioritise the high-priority items before the next "
        "release milestone to reduce operational risk."
    )),
    (60, (
        "Several foundational gaps must be addressed before this system is suitable for "
        "sustained production traffic. The engineering team should treat the high-priority "
        "findings as blocking issues and resolve them in the current sprint."
    )),
    (0, (
        "This architecture carries significant production risk and is not ready for live "
        "traffic at scale. A focused remediation effort targeting the critical findings "
        "should be undertaken before any production deployment."
    )),
]


def _final_recommendation(score: int) -> str:
    for threshold, text in _FINAL_REC_THRESHOLDS:
        if score >= threshold:
            return text
    return _FINAL_REC_THRESHOLDS[-1][1]


def _executive_narrative(
    project_name: str,
    overall_score: int,
    verdict: str,
    n_high_risks: int,
    n_findings: int,
    n_recs: int,
    estimated_saving: str,
    latency_improvement: str,
    production_score: int,
    top_risk_title: str,
    top_action_titles: list[str],
) -> str:
    """Consulting-grade narrative — Gartner / McKinsey / AWS Well-Architected style.

    Tone adapts to three quality tiers:
      • Excellent (≥ 85): optimistic, incremental-improvement framing
      • Moderate  (60-84): balanced, improvement-focused
      • Poor      (< 60):  warning-led, risk-first language
    """
    parts: list[str] = []

    # Sentence 1 — scope
    parts.append(
        f"ArchitectIQ analyzed {project_name} across {_DIMENSIONS_REVIEWED}."
    )

    # Sentence 2 — findings count + severity
    if n_findings == 0:
        parts.append(
            "The review found no significant architectural deficiencies — "
            "the system meets all evaluated quality criteria."
        )
    else:
        high_note = (
            f", including {n_high_risks} high-priority "
            f"issue{'s' if n_high_risks != 1 else ''} affecting production readiness"
            if n_high_risks > 0 else ""
        )
        parts.append(
            f"The review identified {n_findings} "
            f"finding{'s' if n_findings != 1 else ''}{high_note}."
        )

    # Sentence 3 — highest risk (if any)
    if top_risk_title:
        parts.append(f"The most critical risk is: {top_risk_title}.")

    # Sentence 4 — top optimization actions
    if top_action_titles:
        if len(top_action_titles) == 1:
            actions_str = top_action_titles[0]
        elif len(top_action_titles) == 2:
            actions_str = f"{top_action_titles[0]} and {top_action_titles[1]}"
        else:
            actions_str = (
                f"{', '.join(top_action_titles[:-1])}, and {top_action_titles[-1]}"
            )
        parts.append(f"The most impactful improvements are {actions_str}.")

    # Sentence 5 — savings / latency
    has_saving  = bool(estimated_saving and estimated_saving not in ("$0", "$0.00"))
    has_latency = bool(latency_improvement and latency_improvement not in ("0%", "0.0%"))
    if has_saving and has_latency:
        parts.append(
            f"These optimizations are expected to reduce monthly AI infrastructure costs "
            f"by approximately {estimated_saving} while improving average response "
            f"latency by {latency_improvement}."
        )
    elif has_saving:
        parts.append(
            f"Implementing these recommendations could reduce monthly AI infrastructure "
            f"costs by approximately {estimated_saving}."
        )
    elif has_latency:
        parts.append(
            f"Applying these changes is expected to improve average response latency "
            f"by {latency_improvement}."
        )

    # Sentence 6 — production readiness
    pr_qualifier = (
        "meets production readiness standards"    if production_score >= 80 else
        "is approaching production readiness"     if production_score >= 65 else
        "has not yet reached production readiness"
    )
    parts.append(
        f"Overall production readiness is {production_score}/100 — "
        f"the system {pr_qualifier}."
    )

    # Sentence 7 — final recommendation
    parts.append(_final_recommendation(overall_score))

    return " ".join(parts)


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
        advanced_rec_report: dict,
        project_name: str = "this architecture",
    ) -> dict:
        """Return the ``intelligence_summary`` dict.

        Args:
            overall_score:        Weighted architecture score (0-100).
            production_score:     Production readiness score (0-100).
            top_findings:         Severity-sorted findings from ReviewReportBuilder.
            recommendations:      Priority-sorted recommendations (legacy shape).
            advanced_rec_report:  Output from AdvancedRecommendationEngine.generate().
            project_name:         Human-readable project name for the narrative.

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
        n_findings      = len(top_findings)

        # Highest-risk title — first HIGH finding, fallback to first finding
        high_findings  = [f for f in top_findings if f.get("severity") == "HIGH"]
        top_risk_title = (
            (high_findings[0].get("title") or "").strip()
            if high_findings
            else ((top_findings[0].get("title") or "").strip() if top_findings else "")
        )

        # Top-3 action titles from rich recommendations (already priority-sorted)
        source_recs       = rich_recs if rich_recs else recommendations
        top_action_titles = [r["title"] for r in source_recs[:3] if r.get("title")]

        narrative = _executive_narrative(
            project_name=project_name,
            overall_score=overall_score,
            verdict=_verdict(overall_score),
            n_high_risks=n_high_risks,
            n_findings=n_findings,
            n_recs=len(recommendations),
            estimated_saving=estimated_saving,
            latency_improvement=latency_improvement,
            production_score=production_score,
            top_risk_title=top_risk_title,
            top_action_titles=top_action_titles,
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
