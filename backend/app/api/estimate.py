from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.schemas import ArchitectureRequest, EstimateResponse
from app.services.architecture_review import _detect_primary_model
from app.services.cost_analyzer import DetailedCostEstimator
from app.services.estimator import (
    estimate_latency,
    estimate_monthly_tokens,
)
from app.utils.logger import logger

router = APIRouter()

_estimator = DetailedCostEstimator()


@router.post(
    "/estimate",
    response_model=EstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate AI Infrastructure Cost",
    description=(
        "Estimates full infrastructure cost including LLM inference, embedding, "
        "vector DB, storage, and overhead.  Also returns potential savings from "
        "semantic caching and model-switching recommendations."
    ),
    response_description="Detailed cost estimate with 6-line breakdown, token usage, latency, and savings.",
    tags=["Cost Estimation"],
    responses={
        200: {
            "description": "Detailed cost estimate with breakdown and savings projection.",
            "content": {
                "application/json": {
                    "example": {
                        "total_monthly_cost": 2148.0,
                        "model_costs": [
                            {"component": "gpt-4o",                "monthly_cost": 1680.0},
                            {"component": "text-embedding-3-small", "monthly_cost": 152.0},
                            {"component": "pinecone",              "monthly_cost": 94.0},
                            {"component": "storage",               "monthly_cost": 31.0},
                            {"component": "infrastructure",        "monthly_cost": 191.0},
                        ],
                        "tokens": {
                            "input_tokens":  140_000_000,
                            "output_tokens":  50_000_000,
                            "total_tokens":  190_000_000,
                        },
                        "average_latency_ms": 620.0,
                        "potential_monthly_savings": 720.0,
                        "currency": "USD",
                        "breakdown": {
                            "monthly_cost":        2148.0,
                            "llm_cost":            1680.0,
                            "embedding_cost":       152.0,
                            "vector_db_cost":        94.0,
                            "storage_cost":          31.0,
                            "infrastructure_cost":  191.0,
                            "total_before_savings": 2148.0,
                            "estimated_savings":    720.0,
                        },
                    }
                }
            },
        }
    },
)
def create_estimate(request: ArchitectureRequest) -> EstimateResponse:
    """Estimate monthly infrastructure cost with a full 6-line breakdown.

    Cost is never $0 for architectures with real traffic and a paid model.
    Zero-requests architectures are the only valid case where the total may
    reach $0.

    Args:
        request: Validated architecture request.

    Returns:
        EstimateResponse with total cost, per-component breakdown, token usage,
        latency estimate, and potential savings.
    """
    try:
        logger.info(f"Processing cost estimate for: {request.name}")

        # ── Detailed cost via the canonical estimator ──────────────────────
        bd = _estimator.estimate(request)

        # ── Token summary (for backward-compat tokens field) ───────────────
        monthly_tokens = estimate_monthly_tokens(
            requests_per_month=request.monthly_requests,
            avg_input_tokens=request.average_prompt_tokens,
            avg_output_tokens=request.average_completion_tokens,
        )

        # ── Latency estimate ───────────────────────────────────────────────
        primary_model = _detect_primary_model(request.components)
        average_latency_ms = estimate_latency(
            model=primary_model,
            avg_input_tokens=request.average_prompt_tokens,
            avg_output_tokens=request.average_completion_tokens,
        )

        # ── Per-component model_costs list (richer than before) ────────────
        model_costs = [
            {"component": request.llm or primary_model, "monthly_cost": bd.llm_cost},
        ]
        if bd.embedding_cost > 0:
            model_costs.append({
                "component": request.embedding_model or "embedding",
                "monthly_cost": bd.embedding_cost,
            })
        if bd.vector_db_cost > 0:
            model_costs.append({
                "component": request.vector_db or "vector_db",
                "monthly_cost": bd.vector_db_cost,
            })
        if bd.storage_cost > 0:
            model_costs.append({"component": "storage", "monthly_cost": bd.storage_cost})
        if bd.infrastructure_cost > 0:
            model_costs.append({"component": "infrastructure", "monthly_cost": bd.infrastructure_cost})

        logger.info(
            f"Estimate complete for {request.name}: "
            f"gross=${bd.total_before_savings}, net=${bd.monthly_cost}, "
            f"savings=${bd.estimated_savings}, tokens={monthly_tokens['total_tokens']}, "
            f"latency={average_latency_ms}ms"
        )

        return EstimateResponse(
            total_monthly_cost=bd.total_before_savings,
            model_costs=model_costs,
            tokens=monthly_tokens,
            average_latency_ms=average_latency_ms,
            potential_monthly_savings=bd.estimated_savings,
            currency="USD",
            breakdown=bd.to_dict(),
        )
    except ValidationError as exc:
        logger.warning(f"Validation error for estimate {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except Exception as exc:
        logger.error(f"Unexpected error during estimate for {request.name}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the estimate.",
        )
