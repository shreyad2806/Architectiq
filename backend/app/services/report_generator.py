"""ReportGenerator.

Assembles the final, clean architecture audit report from the outputs
already produced by ReviewReportBuilder.  No analyzer is re-executed here —
every value is derived from the dict returned by ``ReviewReportBuilder.build()``.

Public API:
    ReportGenerator().generate(raw_report: dict) -> dict
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Letter-grade mapping for the architecture_overview block
# ---------------------------------------------------------------------------

_GRADE_LETTER: list[tuple[int, str]] = [
    (95, "A+"),
    (90, "A"),
    (85, "A-"),
    (80, "B+"),
    (75, "B"),
    (70, "B-"),
    (65, "C+"),
    (60, "C"),
    (50, "C-"),
    (0,  "D"),
]


def _letter_grade(score: int) -> str:
    for threshold, letter in _GRADE_LETTER:
        if score >= threshold:
            return letter
    return "D"


# ---------------------------------------------------------------------------
# Optimization Roadmap builder
# ---------------------------------------------------------------------------

# Phase definitions
_PHASES: list[dict] = [
    {"phase": 1, "title": "Immediate Wins",        "timeline": "Today"},
    {"phase": 2, "title": "Production Hardening",  "timeline": "This Week"},
    {"phase": 3, "title": "Scale",                 "timeline": "This Month"},
]

# Substrings that indicate an implementation time fits within one day
_FAST_TIME_TOKENS = {
    "minute", "minutes", "min", "hour", "hours", "hr",
}


def _is_fast(implementation_time: str) -> bool:
    """Return True when the implementation_time fits within one working day."""
    token = implementation_time.lower()
    # Explicit single-day markers that are NOT sub-day
    if token in ("1 day", "one day", "1day"):
        return False
    return any(t in token for t in _FAST_TIME_TOKENS)


def _phase_for(rec: dict) -> int:
    """Classify a recommendation into phase 1, 2, or 3.

    Phase 1 — Immediate Wins (Today)
        Easy difficulty AND implementation_time < 1 day AND priority HIGH or MEDIUM

    Phase 2 — Production Hardening (This Week)
        Medium difficulty OR implementation_time of ~1 day OR LOW-priority quick wins
        OR infrastructure-oriented categories

    Phase 3 — Scale (This Month)
        Hard difficulty OR long implementation_time OR advanced optimisations
    """
    difficulty = (rec.get("difficulty") or "").lower().strip()
    impl_time  = (rec.get("implementation_time") or "").lower().strip()
    priority   = (rec.get("priority") or "LOW").upper()
    category   = (rec.get("category") or "").lower()

    fast = _is_fast(impl_time)

    # Phase 1: Easy + fast + high/medium impact
    if difficulty == "easy" and fast and priority in ("HIGH", "MEDIUM"):
        return 1

    # Phase 3: Hard difficulty or multi-week work or advanced/scale categories
    if difficulty == "hard":
        return 3
    multi_week_tokens = ("week", "month", "sprint")
    if any(t in impl_time for t in multi_week_tokens):
        return 3
    advanced_categories = ("rag optimiz", "scale", "model routing", "hybrid")
    if any(c in category for c in advanced_categories) and difficulty != "easy":
        return 3

    # Phase 2: everything else — medium effort, infra work, 1-day tasks
    return 2


def _build_optimization_roadmap(raw_report: dict) -> list[dict]:
    """Return the dynamic roadmap pre-built by RoadmapGenerator.

    RoadmapGenerator (called by ReviewReportBuilder before ReportGenerator)
    stores the result in raw_report["dynamic_roadmap"].  We return it
    directly so no re-classification work happens here.

    Falls back to an empty list when the key is absent (e.g. in unit tests
    that construct a raw_report without running the full builder pipeline).
    """
    return raw_report.get("dynamic_roadmap") or []


# ---------------------------------------------------------------------------
# Architecture Overview builder
# ---------------------------------------------------------------------------

def _build_architecture_overview(raw_report: dict) -> dict:
    arch_score = raw_report.get("architecture_score", {})
    pr         = raw_report.get("production_readiness", {})
    health     = raw_report.get("architecture_health", {})

    overall_score    = arch_score.get("overall_score", 0)
    production_score = pr.get("score", 0)

    score_breakdown: dict = {}
    if health:
        score_breakdown = {
            "cost_efficiency":          health.get("cost_efficiency", 0),
            "latency":                  health.get("latency", 0),
            "reliability":              health.get("reliability", 0),
            "scalability":              health.get("scalability", 0),
            "cost_efficiency_insight":  health.get("cost_efficiency_insight", ""),
            "latency_insight":          health.get("latency_insight", ""),
            "reliability_insight":      health.get("reliability_insight", ""),
            "scalability_insight":      health.get("scalability_insight", ""),
        }

    return {
        "overall_score":        overall_score,
        "architecture_grade":   _letter_grade(overall_score),
        "production_readiness": production_score,
        "score_breakdown":      score_breakdown,
    }


# ---------------------------------------------------------------------------
# Score Breakdown builder
# ---------------------------------------------------------------------------

def _build_score_breakdown(raw_report: dict) -> dict:
    dims = raw_report.get("architecture_score", {}).get("dimension_scores", {})
    return {
        "cost_score":          dims.get("cost", 0),
        "latency_score":       dims.get("latency", 0),
        "rag_score":           dims.get("rag", 0),
        "reliability_score":   dims.get("reliability", 0),
        "security_score":      dims.get("security", 0),
        "scalability_score":   dims.get("scalability", 0),
        "observability_score": dims.get("observability", 0),
    }


# ---------------------------------------------------------------------------
# Cost Analysis reshaper
# ---------------------------------------------------------------------------

def _fmt_cost(value: float) -> str:
    """Format a float dollar value as a human-readable string."""
    if value >= 1_000:
        return f"${value:,.0f}"
    if value > 0:
        return f"${value:.2f}"
    return "$0"


def _savings_pct(total: float, savings: float) -> str:
    if total <= 0:
        return "0%"
    return f"{min(round((savings / total) * 100), 99)}%"


def _build_cost_analysis(raw_report: dict) -> dict:
    ca    = raw_report.get("cost_analysis", {})
    intel = raw_report.get("intelligence_summary", {})
    bd    = ca.get("breakdown", {})

    gross   = bd.get("total_before_savings", ca.get("estimated_monthly_cost", 0.0))
    savings = bd.get("estimated_savings", ca.get("potential_monthly_savings", 0.0))
    net     = bd.get("monthly_cost", gross)

    return {
        "estimated_monthly_tokens":   ca.get("estimated_monthly_tokens", 0),
        "estimated_monthly_cost":     _fmt_cost(net),
        "potential_monthly_savings":  _fmt_cost(savings),
        "savings_percentage":         _savings_pct(gross, savings),
        "estimated_saving_from_recs": intel.get("estimated_monthly_savings", "$0"),
        "currency":                   ca.get("currency", "USD"),
        "breakdown": {
            "monthly_cost":         round(net, 2),
            "llm_cost":             round(bd.get("llm_cost", 0.0), 2),
            "embedding_cost":       round(bd.get("embedding_cost", 0.0), 2),
            "vector_db_cost":       round(bd.get("vector_db_cost", 0.0), 2),
            "storage_cost":         round(bd.get("storage_cost", 0.0), 2),
            "infrastructure_cost":  round(bd.get("infrastructure_cost", 0.0), 2),
            "total_before_savings": round(gross, 2),
            "estimated_savings":    round(savings, 2),
        } if bd else {},
    }


# ---------------------------------------------------------------------------
# Latency Analysis reshaper
# ---------------------------------------------------------------------------

def _build_latency_analysis(raw_report: dict) -> dict:
    la = raw_report.get("latency_analysis", {})
    intel = raw_report.get("intelligence_summary", {})
    return {
        "estimated_latency_ms":      la.get("estimated_latency_ms", 0),
        "latency_rating":            la.get("latency_rating", ""),
        "estimated_improvement":     intel.get("estimated_latency_improvement", "0%"),
    }


# ---------------------------------------------------------------------------
# Analyzer section pass-throughs (clean, no duplication)
# ---------------------------------------------------------------------------

def _build_rag_analysis(raw_report: dict) -> dict:
    ra = raw_report.get("rag_analysis", {})
    return {
        "rag_score":         ra.get("rag_score", 0),
        "retrieval_quality": ra.get("retrieval_quality", ""),
        "recommendations":   ra.get("recommendations", []),
    }


def _build_security_analysis(raw_report: dict) -> dict:
    sa = raw_report.get("security_analysis", {})
    return {
        "security_score":    sa.get("security_score", 0),
        "severity":          sa.get("severity", ""),
        "security_findings": sa.get("security_findings", []),
        "recommendations":   sa.get("recommendations", []),
    }


def _build_reliability_analysis(raw_report: dict) -> dict:
    ra = raw_report.get("reliability_analysis", {})
    return {
        "reliability_score": ra.get("reliability_score", 0),
        "risk_level":        ra.get("risk_level", ""),
        "findings":          ra.get("findings", []),
    }


def _build_scalability_analysis(raw_report: dict) -> dict:
    sa = raw_report.get("scalability_analysis", {})
    return {
        "scalability_score": sa.get("scalability_score", 0),
        "expected_capacity": sa.get("expected_capacity", ""),
        "recommendations":   sa.get("recommendations", []),
    }


def _build_observability_analysis(raw_report: dict) -> dict:
    oa = raw_report.get("observability_analysis", {})
    return {
        "observability_score": oa.get("observability_score", 0),
        "missing_features":    oa.get("missing_features", []),
        "recommendations":     oa.get("recommendations", []),
    }


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Reshape a raw ReviewReportBuilder report into the clean audit format."""

    def generate(self, raw_report: dict) -> dict:
        """Return a clean, structured architecture audit report.

        Args:
            raw_report: The dict returned by ``ReviewReportBuilder.build()``.

        Returns:
            Clean report with keys: intelligence_summary, architecture_overview,
            score_breakdown, cost_analysis, latency_analysis, rag_analysis,
            security_analysis, reliability_analysis, scalability_analysis,
            observability_analysis, recommendations, optimization_roadmap.
        """
        raw_recs  = raw_report.get("recommendations", [])
        # rich_recommendations contains the full advanced engine output
        # (with category, difficulty, implementation_time, etc.)
        # stored by ReviewReportBuilder to avoid re-running the engine.
        adv_recs: list[dict] = raw_report.get("rich_recommendations") or raw_recs

        return {
            "intelligence_summary":   raw_report.get("intelligence_summary", {}),
            "architecture_overview":  _build_architecture_overview(raw_report),
            "score_breakdown":        _build_score_breakdown(raw_report),
            "cost_analysis":          _build_cost_analysis(raw_report),
            "latency_analysis":       _build_latency_analysis(raw_report),
            "rag_analysis":           _build_rag_analysis(raw_report),
            "security_analysis":      _build_security_analysis(raw_report),
            "reliability_analysis":   _build_reliability_analysis(raw_report),
            "scalability_analysis":   _build_scalability_analysis(raw_report),
            "observability_analysis": _build_observability_analysis(raw_report),
            # Use rich recommendations (adv_recs) so the frontend receives the
            # correct field names: priority, title, reason, expected_monthly_saving,
            # latency_improvement, difficulty, implementation_time.
            "recommendations":        adv_recs,
            "optimization_roadmap":   _build_optimization_roadmap(raw_report),
        }
