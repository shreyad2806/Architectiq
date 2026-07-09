from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from typing import List

from app.schemas import ArchitectureRequest, RecommendationResponse
from app.rules import analyze_architecture
from app.services.recommender import recommend
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/recommend",
    response_model=List[RecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate Optimization Recommendations",
    description="Returns actionable optimization recommendations ranked by severity and expected savings for the provided AI architecture.",
    response_description="Prioritized list of optimization recommendations.",
    tags=["Optimization"],
    responses={
        200: {
            "description": "Prioritized list of optimization recommendations.",
            "content": {
                "application/json": {
                    "example": [
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
                    ]
                }
            },
        }
    },
)
def create_recommendations(request: ArchitectureRequest) -> List[RecommendationResponse]:
    """Run the recommendation engine and return prioritized recommendations.

    Args:
        request: Validated architecture request.

    Returns:
        List of prioritized ``RecommendationResponse`` objects.
    """
    try:
        logger.info(f"Processing recommendations for: {request.name}")

        architecture_dict = request.model_dump()
        findings = analyze_architecture(architecture_dict)
        recommendations = recommend(findings)

        logger.info(
            f"Recommendations complete for {request.name}: "
            f"{len(recommendations)} items found"
        )

        return recommendations
    except ValidationError as exc:
        logger.warning(f"Validation error for recommendations {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except Exception as exc:
        logger.error(f"Unexpected error during recommendations for {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating recommendations.",
        )
