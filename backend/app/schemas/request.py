from pydantic import BaseModel, Field, model_validator


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


class ReviewRequest(BaseModel):
    """Comprehensive request model for submitting a production AI architecture for review."""

    project_name: str = Field(
        ...,
        description="Human-readable name of the AI project or architecture.",
        examples=["TalentLens"],
    )
    llm: str = Field(
        ...,
        description="Primary large language model used in the architecture.",
        examples=["gpt-4o"],
    )
    embedding_model: str = Field(
        ...,
        description="Embedding model used for vector search and retrieval.",
        examples=["text-embedding-3-small"],
    )
    vector_db: str = Field(
        ...,
        description="Vector database provider used for storage and retrieval.",
        examples=["Pinecone"],
    )
    framework: str = Field(
        ...,
        description="Backend framework used to build the AI service.",
        examples=["FastAPI"],
    )
    memory: bool = Field(
        default=False,
        description="Whether the architecture uses memory or session state.",
        examples=[False],
    )
    rag_enabled: bool = Field(
        default=False,
        description="Whether retrieval-augmented generation is enabled.",
        examples=[True],
    )
    cache_enabled: bool = Field(
        default=False,
        description="Whether caching is enabled for prompts or responses.",
        examples=[False],
    )
    prompt_strategy: str = Field(
        ...,
        description="Strategy used for prompt design, such as few-shot or chain-of-thought.",
        examples=["few-shot"],
    )
    monthly_requests: int = Field(
        ...,
        description="Expected monthly request volume for cost estimation.",
        ge=0,
        examples=[100000],
    )
    average_prompt_tokens: int = Field(
        ...,
        description="Average number of input tokens per request.",
        ge=1,
        examples=[1400],
    )
    average_completion_tokens: int = Field(
        ...,
        description="Average number of output tokens per request.",
        ge=1,
        examples=[500],
    )
    context_window: int = Field(
        ...,
        description="Maximum number of tokens the model can handle in its context window.",
        ge=1,
        examples=[128000],
    )
    concurrent_users: int = Field(
        ...,
        description="Expected number of concurrent users.",
        ge=0,
        examples=[5000],
    )
    observability: bool = Field(
        default=False,
        description="Whether observability and tracing are configured.",
        examples=[True],
    )
    logging: bool = Field(
        default=False,
        description="Whether structured logging is enabled.",
        examples=[True],
    )
    monitoring: bool = Field(
        default=False,
        description="Whether a monitoring solution (e.g. Prometheus, Datadog) is configured.",
        examples=[True],
    )
    tracing: bool = Field(
        default=False,
        description="Whether distributed tracing (e.g. OpenTelemetry, Jaeger) is enabled.",
        examples=[True],
    )
    metrics: bool = Field(
        default=False,
        description="Whether application metrics are collected and exported.",
        examples=[True],
    )
    health_endpoint: bool = Field(
        default=False,
        description="Whether a dedicated health check endpoint is exposed.",
        examples=[True],
    )
    authentication: bool = Field(
        default=False,
        description="Whether authentication is enabled for the API.",
        examples=[True],
    )
    rate_limiting: bool = Field(
        default=False,
        description="Whether rate limiting is enforced.",
        examples=[True],
    )
    retry_strategy: bool = Field(
        default=False,
        description="Whether a retry and failover strategy is implemented.",
        examples=[True],
    )
    prompt_injection_protection: bool = Field(
        default=False,
        description="Whether prompt injection protection or guardrails are in place.",
        examples=[True],
    )
    input_validation: bool = Field(
        default=False,
        description="Whether strict input validation is applied to incoming requests.",
        examples=[True],
    )

    # Backwards-compatible fields for the existing pipeline.
    name: str | None = Field(
        default=None,
        description="Deprecated human-readable name (use project_name).",
        examples=["TalentLens"],
    )
    description: str | None = Field(
        default=None,
        description="Deprecated optional summary (no longer used).",
        examples=["AI-powered talent matching platform"],
    )
    components: list[Component] = Field(
        default_factory=list,
        description="Deprecated list of components (use llm, vector_db, framework).",
        examples=[
            [
                {"type": "llm", "provider": "openai", "model": "gpt-4o"},
                {"type": "vector_store", "provider": "pinecone"},
            ]
        ],
    )
    estimated_requests_per_month: int | None = Field(
        default=None,
        description="Deprecated monthly request volume (use monthly_requests).",
        ge=0,
        examples=[100000],
    )
    average_input_tokens: int | None = Field(
        default=None,
        description="Deprecated average input tokens (use average_prompt_tokens).",
        ge=1,
        examples=[1400],
    )
    average_output_tokens: int | None = Field(
        default=None,
        description="Deprecated average output tokens (use average_completion_tokens).",
        ge=1,
        examples=[500],
    )

    @model_validator(mode="after")
    def _sync_legacy_fields(self):
        """Populate legacy fields from new fields to keep existing services unchanged."""
        if self.name is None:
            self.name = self.project_name
        if self.estimated_requests_per_month is None:
            self.estimated_requests_per_month = self.monthly_requests
        if self.average_input_tokens is None:
            self.average_input_tokens = self.average_prompt_tokens
        if self.average_output_tokens is None:
            self.average_output_tokens = self.average_completion_tokens
        if not self.components:
            self.components = []
            if self.llm:
                self.components.append(Component(type="llm", provider="openai", model=self.llm))
            if self.embedding_model:
                self.components.append(Component(type="embedding", provider="openai", model=self.embedding_model))
            if self.vector_db:
                self.components.append(Component(type="vector_store", provider=self.vector_db))
            if self.framework:
                self.components.append(Component(type="gateway", provider=self.framework))
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_name": "TalentLens",
                "llm": "gpt-4o",
                "embedding_model": "text-embedding-3-small",
                "vector_db": "Pinecone",
                "framework": "FastAPI",
                "memory": False,
                "rag_enabled": True,
                "cache_enabled": False,
                "prompt_strategy": "few-shot",
                "monthly_requests": 100000,
                "average_prompt_tokens": 1400,
                "average_completion_tokens": 500,
                "context_window": 128000,
                "concurrent_users": 5000,
                "observability": True,
                "logging": True,
                "monitoring": True,
                "tracing": True,
                "metrics": True,
                "health_endpoint": True,
                "authentication": True,
                "rate_limiting": True,
                "retry_strategy": True,
                "prompt_injection_protection": True,
                "input_validation": True,
            }
        }
    }


# Backwards-compatible alias used by the existing API endpoints.
ArchitectureRequest = ReviewRequest
