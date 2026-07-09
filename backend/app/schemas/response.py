from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    """A single optimization recommendation for an architecture review."""

    id: str = Field(
        ...,
        description="Unique identifier for the recommendation.",
        examples=["rec-001"],
    )
    title: str = Field(
        ...,
        description="Short, actionable title of the recommendation.",
        examples=["Switch to a tiered embedding model"],
    )
    category: str = Field(
        ...,
        description="Category the recommendation belongs to.",
        examples=["cost", "performance", "reliability", "security"],
    )
    priority: str = Field(
        ...,
        description="Priority level of the recommendation.",
        pattern="^(?i)(high|medium|low)$",
        examples=["high"],
    )
    description: str = Field(
        ...,
        description="Detailed explanation of the issue and proposed fix.",
        examples=["Use a smaller embedding model for first-pass retrieval."],
    )
    estimated_monthly_savings: float | None = Field(
        default=None,
        description="Estimated monthly cost savings in USD if applied.",
        ge=0,
        examples=[2300.00],
    )
    implementation_effort: str = Field(
        ...,
        description="Relative effort to implement the recommendation.",
        examples=["low", "medium", "high"],
    )
    estimated_latency_improvement_ms: float | None = Field(
        default=None,
        description="Estimated latency improvement in milliseconds if the recommendation is applied.",
        ge=0,
        examples=[250.0],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "rec-001",
                "title": "Introduce semantic caching",
                "category": "cost",
                "priority": "high",
                "description": "Repeated prompts increase inference cost. Add a semantic cache to reduce redundant LLM calls.",
                "estimated_monthly_savings": 820.0,
                "implementation_effort": "medium",
                "estimated_latency_improvement_ms": 120.0,
            }
        }
    }


class EstimateResponse(BaseModel):
    """Cost estimation summary for a submitted architecture."""

    total_monthly_cost: float = Field(
        ...,
        description="Total estimated monthly cost in USD.",
        ge=0,
        examples=[12450.00],
    )
    model_costs: list[dict] = Field(
        ...,
        description="Per-model or per-component cost breakdown.",
        examples=[
            [
                {"component": "gpt-4", "monthly_cost": 8200.00},
                {"component": "embedding", "monthly_cost": 1200.00},
            ]
        ],
    )
    tokens: dict = Field(
        ...,
        description="Estimated token usage breakdown per month.",
        examples=[
            {"input_tokens": 1500000000, "output_tokens": 400000000, "total_tokens": 1900000000}
        ],
    )
    average_latency_ms: float = Field(
        ...,
        description="Estimated average latency per request in milliseconds.",
        ge=0,
        examples=[550.0],
    )
    potential_monthly_savings: float = Field(
        ...,
        description="Total estimated monthly savings in USD from applying recommendations.",
        ge=0,
        examples=[6600.00],
    )
    currency: str = Field(
        default="USD",
        description="Currency code for all monetary values.",
        examples=["USD"],
    )

    model_config = {
        "json_schema_extra": {
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
    }


class ReviewResponse(BaseModel):
    """Complete architecture review result returned by the analyzer."""

    id: str = Field(
        ...,
        description="Unique identifier for the review.",
        examples=["rev-7a8f9d2"],
    )
    architecture_name: str = Field(
        ...,
        description="Name of the architecture that was reviewed.",
        examples=["Production RAG Pipeline"],
    )
    overall_score: int = Field(
        ...,
        description="Overall architecture score from 0 to 100.",
        ge=0,
        le=100,
        examples=[78],
    )
    production_readiness: int = Field(
        ...,
        description="Production readiness score from 0 to 100.",
        ge=0,
        le=100,
        examples=[65],
    )
    cost_estimate: EstimateResponse = Field(
        ...,
        description="Cost estimation and savings projection for the architecture.",
    )
    recommendations: list[RecommendationResponse] = Field(
        ...,
        description="Ranked list of optimization recommendations.",
    )
    summary: str = Field(
        ...,
        description="High-level natural language summary of the review findings.",
        examples=["Architecture is strong but cost and retry logic can be improved."],
    )

    model_config = {
        "json_schema_extra": {
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
    }
