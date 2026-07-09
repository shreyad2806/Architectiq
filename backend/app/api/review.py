from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.schemas import ArchitectureRequest, ReviewResponse
from app.services.architecture_review import review
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze AI Architecture",
    description="Analyzes an AI system architecture and returns production readiness, estimated costs, latency analysis, findings, and optimization recommendations.",
    response_description="Complete architecture audit report.",
    tags=["Architecture Review"],
    responses={
        201: {
            "description": "Complete architecture audit report.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "rev-7a8f9d2",
                        "architecture_name": "TalentLens",
                        "overall_score": 87,
                        "production_readiness": 91,
                        "cost_estimate": {
                            "total_monthly_cost": 2480.0,
                            "model_costs": [
                                {"component": "gpt-4o", "monthly_cost": 2480.0}
                            ],
                            "tokens": {
                                "input_tokens": 140000000,
                                "output_tokens": 50000000,
                                "total_tokens": 190000000,
                            },
                            "average_latency_ms": 620.0,
                            "potential_monthly_savings": 820.0,
                            "currency": "USD",
                        },
                        "recommendations": [
                            {
                                "id": "rec-001",
                                "title": "Introduce semantic caching",
                                "category": "cost",
                                "priority": "high",
                                "description": "Repeated prompts increase inference cost. Add a semantic cache to reduce redundant LLM calls.",
                                "estimated_monthly_savings": 820.0,
                                "implementation_effort": "medium",
                                "estimated_latency_improvement_ms": 120.0,
                            }
                        ],
                        "summary": "Architecture is well-structured but can reduce cost by adding semantic caching.",
                    }
                }
            },
        }
    },
)
def create_review(request: ArchitectureRequest) -> ReviewResponse:
    """Submit an architecture for review and return a structured analysis.

    Args:
        request: Validated architecture request.

    Returns:
        ReviewResponse containing scores, cost estimate, and prioritized recommendations.
    """
    try:
        logger.info(f"Processing architecture review for: {request.name}")
        result = review(request)
        logger.info(
            f"Review complete for {request.name}: score={result.overall_score}, "
            f"readiness={result.production_readiness}, "
            f"recommendations={len(result.recommendations)}"
        )
        return result
    except ValidationError as exc:
        logger.warning(f"Validation error for architecture {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except Exception as exc:
        logger.error(f"Unexpected error during review for {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the review.",
        )
