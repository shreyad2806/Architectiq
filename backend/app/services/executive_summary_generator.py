"""ExecutiveSummaryGenerator.

Produces a structured executive summary from all analyzer outputs, formatted
as a senior-level architecture consulting report suitable for engineering
managers and CTOs.
"""

from __future__ import annotations

from app.schemas import ReviewRequest
from app.services.recommendation_engine import AdvancedRecommendationEngine


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ASSESSMENT_THRESHOLDS: list[tuple[int, str]] = [
    (90, "Excellent"),
    (80, "Good"),
    (70, "Fair"),
    (0,  "Needs Improvement"),
]

# Production-grade VDBs worth calling a strength
_STRONG_VDB = {"pinecone", "weaviate", "qdrant", "milvus"}
# High-quality embedding models worth calling a strength
_STRONG_EMBEDDINGS = {"text-embedding-3-large", "bge-large", "bge-m3", "e5-large"}
# Async-native frameworks worth calling a strength
_ASYNC_FRAMEWORKS = {"fastapi", "express", "nestjs", "go", "gin", "actix", "axum"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _overall_assessment(score: int) -> str:
    for threshold, label in _ASSESSMENT_THRESHOLDS:
        if score >= threshold:
            return label
    return "Needs Improvement"


def _top_strengths(request: ReviewRequest, analyzer_results: dict) -> list[str]:
    """Return up to 3 concrete strengths derived from the architecture."""
    strengths: list[str] = []

    fw = (request.framework or "").lower().strip()
    vdb = (request.vector_db or "").lower().strip()
    emb = (request.embedding_model or "").lower().strip()

    # Framework
    if fw in _ASYNC_FRAMEWORKS:
        strengths.append(f"Production-grade async framework ({request.framework})")

    # Authentication
    if request.authentication:
        strengths.append("API authentication is configured")

    # RAG pipeline
    if request.rag_enabled:
        strengths.append("Retrieval-Augmented Generation pipeline is active")

    # Good vector DB
    if vdb in _STRONG_VDB:
        strengths.append(f"Production-grade vector database ({request.vector_db})")

    # Strong embedding model
    if emb in _STRONG_EMBEDDINGS:
        strengths.append(f"High-quality embedding model ({request.embedding_model})")

    # Caching
    if request.cache_enabled:
        strengths.append("Semantic caching is enabled, reducing cost and latency")

    # Retry strategy
    if request.retry_strategy:
        strengths.append("Retry and failover strategy is implemented")

    # Full observability stack
    obs_count = sum([
        bool(request.logging), bool(request.monitoring),
        bool(request.tracing), bool(request.metrics),
    ])
    if obs_count == 4:
        strengths.append("Full observability stack (logging, monitoring, tracing, metrics)")
    elif obs_count >= 2:
        strengths.append("Partial observability configured")

    # Rate limiting
    if request.rate_limiting:
        strengths.append("Rate limiting enforced")

    # Prompt injection protection
    if request.prompt_injection_protection:
        strengths.append("Prompt injection protection is in place")

    # Good RAG score
    rag_score = analyzer_results.get("rag", {}).get("rag_score", 0)
    if rag_score >= 70 and request.rag_enabled:
        strengths.append("Strong RAG retrieval quality score")

    # Good security score
    sec_score = analyzer_results.get("security", {}).get("security_score", 0)
    if sec_score >= 80:
        strengths.append("Strong security posture")

    return strengths[:3]


def _top_risks(top_findings: list[dict]) -> list[str]:
    """Return up to 3 highest-severity risk titles from findings."""
    # findings are already severity-sorted (HIGH first); take the first 3 unique
    seen: set[str] = set()
    risks: list[str] = []
    for f in top_findings:
        title = f.get("title", "")
        if title and title not in seen:
            seen.add(title)
            risks.append(title)
        if len(risks) == 3:
            break
    return risks


def _highest_priority_action(recommendations: list[dict]) -> str:
    """Return the title of the first HIGH-priority recommendation, or the first overall."""
    high = [r for r in recommendations if r.get("priority") == "HIGH"]
    source = high[0] if high else (recommendations[0] if recommendations else None)
    if source is None:
        return "No immediate actions required."
    title = source.get("title", "")
    reason = source.get("reason") or source.get("description", "")
    # Build a single imperative sentence
    if reason:
        return f"{title}. {reason.split('.')[0]}."
    return f"{title}."


def _build_narrative_summary(
    project_name: str,
    overall_score: int,
    assessment: str,
    n_findings: int,
    n_recs: int,
    n_high: int,
    production_score: int,
    estimated_saving: str,
    latency_improvement: str,
) -> str:
    """Generate a concise, professional narrative (≤120 words)."""

    # Opening — score + assessment
    parts: list[str] = [
        f"ArchitectIQ analyzed {project_name} and assigned an overall architecture score "
        f"of {overall_score}/100 ({assessment})."
    ]

    # Findings sentence
    if n_findings > 0:
        severity_note = "several critical" if n_high >= 3 else ("some" if n_findings > 4 else "a few")
        parts.append(
            f"The review identified {n_findings} finding{'s' if n_findings != 1 else ''} "
            f"with {n_high} high-priority issue{'s' if n_high != 1 else ''} requiring immediate attention."
        )
    else:
        parts.append("No critical issues were identified.")

    # Production readiness
    pr_label = "production-ready" if production_score >= 80 else (
        "approaching production readiness" if production_score >= 60 else "not yet production-ready"
    )
    parts.append(f"The system is {pr_label} (readiness score: {production_score}/100).")

    # Savings / latency
    if estimated_saving and estimated_saving != "$0":
        parts.append(
            f"Applying the {n_recs} recommendation{'s' if n_recs != 1 else ''} could reduce "
            f"monthly inference costs by approximately {estimated_saving} "
            f"and improve response latency by up to {latency_improvement}."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class ExecutiveSummaryGenerator:
    """Generate a structured executive summary from all analyzer outputs."""

    def __init__(self) -> None:
        self._advanced_engine = AdvancedRecommendationEngine()

    def generate(
        self,
        request: ReviewRequest,
        overall_score: int,
        production_score: int,
        grade: str,
        top_findings: list[dict],
        recommendations: list[dict],
        analyzer_results: dict,
        advanced_rec_report: dict | None = None,
    ) -> dict:
        """Return a structured executive summary dict.

        Args:
            request:           The architecture review request.
            overall_score:     Weighted architecture score (0-100).
            production_score:  Production readiness score (0-100).
            grade:             Letter grade from ArchitectureScoringService.
            top_findings:      Severity-sorted findings list from ReviewReportBuilder.
            recommendations:   Sorted recommendation list (legacy shape).
            analyzer_results:  Dict keyed by dimension with raw analyzer outputs.

        Returns:
            dict with keys: overall_assessment, summary, top_strengths,
            top_risks, estimated_monthly_saving, estimated_latency_improvement,
            highest_priority_action, production_readiness.
        """
        # Reuse the already-computed report if supplied; otherwise compute it.
        advanced = advanced_rec_report if advanced_rec_report is not None \
            else self._advanced_engine.generate(request)
        estimated_saving     = advanced["total_estimated_monthly_savings"]
        latency_improvement  = advanced["estimated_latency_improvement"]
        rich_recs            = advanced["recommendations"]

        assessment   = _overall_assessment(overall_score)
        strengths    = _top_strengths(request, analyzer_results)
        risks        = _top_risks(top_findings)
        top_action   = _highest_priority_action(rich_recs if rich_recs else recommendations)

        n_high = sum(1 for f in top_findings if f.get("severity") == "HIGH")
        n_recs = len(recommendations)

        summary = _build_narrative_summary(
            project_name=request.project_name,
            overall_score=overall_score,
            assessment=assessment,
            n_findings=len(top_findings),
            n_recs=n_recs,
            n_high=n_high,
            production_score=production_score,
            estimated_saving=estimated_saving,
            latency_improvement=latency_improvement,
        )

        return {
            "overall_assessment":           assessment,
            "summary":                      summary,
            "top_strengths":                strengths,
            "top_risks":                    risks,
            "estimated_monthly_saving":     estimated_saving,
            "estimated_latency_improvement": latency_improvement,
            "highest_priority_action":      top_action,
            "production_readiness":         f"{production_score}/100",
        }
