from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.schemas import ArchitectureRequest, EstimateResponse
from app.services.architecture_review import _detect_primary_model
from app.services.estimator import (
    estimate_latency,
    estimate_monthly_cost,
    estimate_monthly_tokens,
    estimate_savings,
)
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/estimate",
    response_model=EstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate AI Infrastructure Cost",
    description="Estimates token usage, monthly inference cost, latency and potential savings for the provided AI architecture.",
    response_description="Cost estimate including tokens, latency, and potential savings.",
    tags=["Cost Estimation"],
    responses={
        200: {
            "description": "Cost estimate including tokens, latency, and potential savings.",
            "content": {
                "application/json": {
                    "example": {
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
                    }
                }
            },
        }
    },
)
def create_estimate(request: ArchitectureRequest) -> EstimateResponse:
    """Estimate monthly cost, token usage, latency, and potential savings.

    Args:
        request: Validated architecture request.

    Returns:
        EstimateResponse containing cost, token, latency, and savings estimates.
    """
    try:
        logger.info(f"Processing cost estimate for: {request.name}")

        requests_per_month = request.estimated_requests_per_month or 0
        avg_input_tokens = request.average_input_tokens
        avg_output_tokens = request.average_output_tokens
        primary_model = _detect_primary_model(request.components)

        monthly_tokens = estimate_monthly_tokens(
            requests_per_month=requests_per_month,
            avg_input_tokens=avg_input_tokens,
            avg_output_tokens=avg_output_tokens,
        )

        total_monthly_cost = estimate_monthly_cost(
            model=primary_model,
            requests_per_month=requests_per_month,
            avg_input_tokens=avg_input_tokens,
            avg_output_tokens=avg_output_tokens,
        )

        average_latency_ms = estimate_latency(
            model=primary_model,
            avg_input_tokens=avg_input_tokens,
            avg_output_tokens=avg_output_tokens,
        )

        savings = estimate_savings(
            current_model=primary_model,
            requests_per_month=requests_per_month,
            avg_input_tokens=avg_input_tokens,
            avg_output_tokens=avg_output_tokens,
        )

        logger.info(
            f"Estimate complete for {request.name}: cost=${total_monthly_cost}, "
            f"tokens={monthly_tokens['total_tokens']}, latency={average_latency_ms}ms, "
            f"savings=${savings['monthly_savings']}"
        )

        return EstimateResponse(
            total_monthly_cost=total_monthly_cost,
            model_costs=[
                {
                    "component": primary_model,
                    "monthly_cost": total_monthly_cost,
                }
            ],
            tokens=monthly_tokens,
            average_latency_ms=average_latency_ms,
            potential_monthly_savings=savings["monthly_savings"],
            currency="USD",
        )
    except ValidationError as exc:
        logger.warning(f"Validation error for estimate {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except Exception as exc:
        logger.error(f"Unexpected error during estimate for {request.name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the estimate.",
        )
