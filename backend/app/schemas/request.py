from pydantic import BaseModel, Field


class Component(BaseModel):
    """A single architecture component (e.g. model, vector store, gateway)."""

    type: str = Field(
        ...,
        description="Type of component (e.g. llm, vector_store, gateway, cache).",
        examples=["llm"],
    )
    provider: str = Field(
        ...,
        description="Provider or service name for the component.",
        examples=["openai"],
    )
    model: str | None = Field(
        default=None,
        description="Model name, if applicable (e.g. gpt-4o, claude-sonnet).",
        examples=["gpt-4o"],
    )


class ArchitectureRequest(BaseModel):
    """Request model for submitting an AI architecture for review."""

    name: str = Field(
        ...,
        description="Human-readable name for the architecture being reviewed.",
        examples=["Production RAG Pipeline"],
    )
    description: str | None = Field(
        default=None,
        description="Optional summary describing the architecture purpose and use case.",
        examples=["Retrieval-augmented generation stack for customer support."],
    )
    components: list[Component] = Field(
        ...,
        description="List of architecture components (models, vector stores, gateways, etc.).",
        examples=[
            [
                {"type": "llm", "provider": "openai", "model": "gpt-4"},
                {"type": "vector_store", "provider": "pinecone"},
            ]
        ],
    )
    estimated_requests_per_month: int | None = Field(
        default=None,
        description="Expected monthly request volume for cost estimation.",
        ge=0,
        examples=[1000000],
    )
    average_input_tokens: int = Field(
        default=1000,
        description="Average number of input tokens per request.",
        ge=1,
        examples=[1500],
    )
    average_output_tokens: int = Field(
        default=250,
        description="Average number of output tokens per request.",
        ge=1,
        examples=[400],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "TalentLens",
                "description": "AI-powered talent matching platform built with FastAPI and React, featuring RAG and Hybrid Search.",
                "components": [
                    {"type": "llm", "provider": "openai", "model": "gpt-4o"},
                    {"type": "vector_store", "provider": "pinecone"},
                    {"type": "gateway", "provider": "internal"},
                ],
                "estimated_requests_per_month": 100000,
                "average_input_tokens": 1400,
                "average_output_tokens": 500,
            }
        }
    }
