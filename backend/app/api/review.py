import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas import ArchitectureRequest
from app.services.review_report_builder import ReviewReportBuilder
from app.utils.logger import logger

router = APIRouter()

# Module-level builder instance — avoids re-instantiating all sub-services per request.
_builder = ReviewReportBuilder()


def _findings_summary(top_findings: list[dict]) -> dict:
    """Compute findings_summary counts from the top_findings list."""
    by_sev: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_cat: dict[str, int] = {"security": 0, "reliability": 0, "cost": 0, "latency": 0, "scalability": 0}

    for f in top_findings:
        sev = (f.get("severity") or "").lower()
        if sev in by_sev:
            by_sev[sev] += 1

        dim = (f.get("dimension") or "").lower()
        if "security" in dim:
            by_cat["security"] += 1
        elif "reliability" in dim:
            by_cat["reliability"] += 1
        elif "cost" in dim:
            by_cat["cost"] += 1
        elif "latency" in dim:
            by_cat["latency"] += 1
        elif "scalability" in dim:
            by_cat["scalability"] += 1

    return {
        "total": len(top_findings),
        "by_severity": by_sev,
        "by_category": by_cat,
    }


def _structured_critical_risks(top_findings: list[dict]) -> list[dict]:
    """Return HIGH/CRITICAL findings as structured Risk objects for the frontend."""
    seen: set[str] = set()
    risks: list[dict] = []
    for f in top_findings:
        sev = (f.get("severity") or "").upper()
        if sev not in ("HIGH", "CRITICAL"):
            continue
        title = (f.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        risks.append({
            "severity": sev,
            "title": title,
            "description": f.get("description", ""),
            "impact": f.get("impact", ""),
        })
    return risks


def _build_agent_response(
    clean: dict,
    generated_at: str,
    report_status: str = "complete",
) -> dict:
    """Build the machine-readable agent response block.

    All fields are derived from the live report data — nothing is hardcoded.
    """
    overview     = clean.get("architecture_overview", {})
    cost         = clean.get("cost_analysis", {})
    recs: list   = clean.get("recommendations", [])

    arch_score = overview.get("overall_score", 0)
    grade      = overview.get("architecture_grade") or _letter_grade_local(arch_score)
    prod_ready = overview.get("production_readiness", 0)

    # Cost values arrive as formatted strings (e.g. "$2,140") — keep as-is.
    monthly_cost    = cost.get("estimated_monthly_cost", "$0")
    monthly_savings = cost.get("potential_monthly_savings", "$0")

    # Highest-priority recommendation drives top_priority + next_action.
    top_rec   = recs[0] if recs else {}
    rec_title = top_rec.get("title", "Review architecture findings")
    rec_prio  = (top_rec.get("priority") or "LOW").upper()
    saving    = top_rec.get("expected_monthly_saving", "")
    latency   = top_rec.get("latency_improvement", "")

    impact_parts = []
    if saving and saving not in ("$0", "$0/month", ""):
        impact_parts.append(f"Save approximately {saving} per month")
    if latency and latency not in ("0%", ""):
        impact_parts.append(f"Improve latency by {latency}")
    estimated_impact = " · ".join(impact_parts) if impact_parts else "Improve architecture quality"

    reason    = top_rec.get("reason", "")
    next_action = (
        f"{reason.rstrip('.')}."
        if reason
        else f"Implement {rec_title.lower()} before deploying to production."
    )

    return {
        "agent": {
            "name":         "ArchitectIQ",
            "version":      "1.0.0",
            "status":       "completed",
            "generated_at": generated_at,
        },
        "summary": {
            "architecture_score":      arch_score,
            "grade":                   grade,
            "production_readiness":    prod_ready,
            "estimated_monthly_cost":  monthly_cost,
            "potential_monthly_savings": monthly_savings,
        },
        "top_priority": {
            "title":            rec_title,
            "priority":         rec_prio,
            "estimated_impact": estimated_impact,
        },
        "next_action":   next_action,
        "report_status": report_status,
    }


def _letter_grade_local(score: int) -> str:
    """Fallback grade if architecture_overview doesn't include it."""
    thresholds = [(95,"A+"),(90,"A"),(85,"A-"),(80,"B+"),(75,"B"),(70,"B-"),(65,"C+"),(60,"C"),(50,"C-")]
    for threshold, letter in thresholds:
        if score >= threshold:
            return letter
    return "D"


def _savings_percentage(cost_analysis: dict) -> str:
    """Derive a human-readable savings percentage string from cost_analysis."""
    cost_raw = cost_analysis.get("estimated_monthly_cost", 0)
    savings_raw = cost_analysis.get("potential_monthly_savings", 0)
    try:
        cost = float(str(cost_raw).replace("$", "").replace(",", "").replace("K", "e3"))
        savings = float(str(savings_raw).replace("$", "").replace(",", "").replace("K", "e3"))
        if cost > 0:
            pct = round((savings / cost) * 100, 1)
            return f"{pct}%"
    except (ValueError, TypeError):
        pass
    return "0%"


@router.post(
    "/review",
    status_code=status.HTTP_200_OK,
    summary="Analyze AI Architecture",
    description=(
        "Analyzes an AI system architecture through 8 specialized analyzers "
        "(security, reliability, scalability, cost, latency, RAG, observability, production readiness) "
        "and returns a complete architecture audit report containing scores, risks, "
        "recommendations, an optimization roadmap, and machine-readable findings."
    ),
    response_description="Complete architecture audit report.",
    tags=["Architecture Review"],
    responses={
        200: {
            "description": "Complete architecture audit report.",
            "content": {
                "application/json": {
                    "example": {
                        "project_name": "TalentLens",
                        "intelligence_summary": {
                            "overall_verdict": "Production Ready with Improvements",
                            "architecture_score": 74,
                            "ai_maturity_level": {"level": 3, "title": "Scaling"},
                            "critical_risks": ["No Authentication", "Missing Retry Policy"],
                            "top_priorities": ["Enable Semantic Caching", "Add Circuit Breaker"],
                            "estimated_monthly_savings": "$4,200",
                            "estimated_latency_improvement": "32%",
                        },
                        "architecture_overview": {
                            "overall_score": 74,
                            "architecture_grade": "B",
                            "production_readiness": 61,
                        },
                        "cost_analysis": {
                            "estimated_monthly_cost": "$21,900",
                            "potential_monthly_savings": "$8,700",
                            "savings_percentage": "39.7%",
                        },
                        "critical_risks": [
                            {
                                "severity": "HIGH",
                                "title": "Missing retry policy",
                                "description": "No retry or circuit-breaker configuration detected.",
                                "impact": "Cascading failures under load.",
                            }
                        ],
                        "recommendations": [
                            {
                                "priority": "HIGH",
                                "title": "Enable Semantic Caching",
                                "reason": "Repeated prompts generate unnecessary token costs.",
                                "expected_monthly_saving": "$4,200/month",
                                "latency_improvement": "-32%",
                                "difficulty": "Easy",
                                "implementation_time": "2 hours",
                            }
                        ],
                        "optimization_roadmap": [
                            {
                                "phase": 1,
                                "title": "Immediate Wins",
                                "timeline": "Today",
                                "tasks": ["Enable Semantic Caching", "Add Rate Limiting"],
                            }
                        ],
                        "findings_summary": {
                            "total": 12,
                            "by_severity": {"critical": 0, "high": 4, "medium": 6, "low": 2},
                            "by_category": {"security": 2, "reliability": 3, "cost": 4, "latency": 2, "scalability": 1},
                        },
                        "audit_report": {
                            "report_id": "arc-3f7a9c12",
                            "generated_at": "2026-01-15T10:30:00Z",
                            "audit_duration_ms": 312,
                            "total_findings": 12,
                            "total_recommendations": 8,
                        },
                    }
                }
            },
        }
    },
)
def create_review(request: ArchitectureRequest) -> JSONResponse:
    """Submit an architecture for review and return a complete audit report.

    Args:
        request: Validated architecture request.

    Returns:
        Complete architecture audit report as JSON.
    """
    try:
        logger.info(f"Processing architecture review for: {request.project_name}")
        t_start = time.monotonic()
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── Run the full analysis pipeline ────────────────────────────────
        raw = _builder.build(request)

        # raw["audit_report"] is the clean ReportGenerator output:
        # { intelligence_summary, architecture_overview, score_breakdown,
        #   cost_analysis, latency_analysis, rag_analysis, security_analysis,
        #   reliability_analysis, scalability_analysis, observability_analysis,
        #   recommendations, optimization_roadmap }
        clean = raw["audit_report"]

        # ── Augment with fields Report.tsx needs that ReportGenerator
        #    does not yet include ─────────────────────────────────────────
        top_findings: list[dict] = raw.get("top_findings", [])
        findings_summary = _findings_summary(top_findings)
        critical_risks   = _structured_critical_risks(top_findings)

        cost_analysis = clean.get("cost_analysis", {})

        audit_duration_ms = round((time.monotonic() - t_start) * 1000)
        report_id = raw.get("report_id") or f"arc-{uuid.uuid4().hex[:8]}"

        response = {
            "project_name": request.project_name,

            # ── Core sections from ReportGenerator ────────────────────────
            "intelligence_summary":   clean.get("intelligence_summary", {}),
            "architecture_overview":  clean.get("architecture_overview", {}),
            "score_breakdown":        clean.get("score_breakdown", {}),
            "cost_analysis": cost_analysis,
            "latency_analysis":       clean.get("latency_analysis", {}),
            "rag_analysis":           clean.get("rag_analysis", {}),
            "security_analysis":      clean.get("security_analysis", {}),
            "reliability_analysis":   clean.get("reliability_analysis", {}),
            "scalability_analysis":   clean.get("scalability_analysis", {}),
            "observability_analysis": clean.get("observability_analysis", {}),
            "recommendations":        clean.get("recommendations", []),
            "optimization_roadmap":   clean.get("optimization_roadmap", []),

            # ── Extra sections required by Report.tsx ─────────────────────
            "critical_risks":   critical_risks,
            "findings_summary": findings_summary,

            # ── Audit metadata envelope ────────────────────────────────────
            "audit_report": {
                "report_id":            report_id,
                "generated_at":         generated_at,
                "audit_duration_ms":    audit_duration_ms,
                "total_findings":       findings_summary["total"],
                "total_recommendations": len(clean.get("recommendations", [])),
                "content_type":         "application/json",
            },

            # ── Machine-readable AI agent response ─────────────────────────
            "agent_response": _build_agent_response(clean, generated_at),

            # ── Professional report metadata ───────────────────────────────
            "report_metadata": {
                "report_id":           report_id,
                "generated_at":        generated_at,
                "analysis_duration_ms": audit_duration_ms,
                "architectiq_version": "1.0.0",
                "environment":         "Production",
                "analyzers_executed":  8,
            },
        }

        logger.info(
            f"Review complete for {request.project_name}: "
            f"score={clean.get('architecture_overview', {}).get('overall_score')}, "
            f"findings={findings_summary['total']}, "
            f"recommendations={len(clean.get('recommendations', []))}, "
            f"duration_ms={audit_duration_ms}"
        )
        return JSONResponse(content=response)

    except ValidationError as exc:
        logger.warning(f"Validation error for architecture {request.project_name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except Exception as exc:
        logger.error(f"Unexpected error during review for {request.project_name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the review.",
        )
