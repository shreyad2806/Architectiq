import pytest

from app.schemas import ReviewRequest
from app.services.cost_analyzer import CostAnalyzer, DetailedCostEstimator


@pytest.fixture
def sample_review_request() -> ReviewRequest:
    return ReviewRequest(
        project_name="TalentLens",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="Pinecone",
        framework="FastAPI",
        memory=False,
        rag_enabled=True,
        cache_enabled=False,
        prompt_strategy="few-shot",
        monthly_requests=100000,
        average_prompt_tokens=1400,
        average_completion_tokens=500,
        context_window=128000,
        concurrent_users=5000,
        observability=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
    )


def test_cost_analyzer_tokens(sample_review_request):
    analyzer = CostAnalyzer()
    result = analyzer.analyze(sample_review_request)
    assert result["estimated_monthly_tokens"] == 190_000_000


def test_cost_analyzer_cost_and_savings(sample_review_request):
    """Gross total must be larger than LLM-only cost; savings must be positive."""
    analyzer = CostAnalyzer()
    result = analyzer.analyze(sample_review_request)
    bd = result["breakdown"]

    # LLM inference:  (140M * $2.50 + 50M * $10.00) / 1M = 350 + 500 = 850
    assert bd["llm_cost"] == 850.0

    # Total includes VDB, storage, infra overhead — must exceed LLM alone
    assert result["estimated_monthly_cost"] > bd["llm_cost"]

    # Savings = model-switch saving (gpt-4o vs gpt-4o-mini baseline)
    # gpt-4o-mini: 140M*0.15 + 50M*0.60 = 21+30 = 51  → saving = 850-51 = 799
    assert bd["savings_from_model_switch"] == 799.0
    assert result["potential_monthly_savings"] > 0


def test_cost_analyzer_llama3_has_zero_llm_cost():
    """llama3 LLM inference is free; infra/storage still contribute a small total."""
    request = ReviewRequest(
        project_name="OpenSource",
        llm="llama3",
        embedding_model="text-embedding-3-small",
        vector_db="FAISS",
        framework="FastAPI",
        memory=False,
        rag_enabled=False,
        cache_enabled=False,
        prompt_strategy="zero-shot",
        monthly_requests=100000,
        average_prompt_tokens=1000,
        average_completion_tokens=200,
        context_window=128000,
        concurrent_users=100,
        observability=False,
        authentication=False,
        rate_limiting=False,
        retry_strategy=False,
    )
    result = CostAnalyzer().analyze(request)
    bd = result["breakdown"]
    assert result["estimated_monthly_tokens"] == 120_000_000
    # LLM inference must be $0 for self-hosted llama3
    assert bd["llm_cost"] == 0.0
    # Embedding is also zero (RAG disabled)
    assert bd["embedding_cost"] == 0.0
    # Vector DB is zero (RAG disabled)
    assert bd["vector_db_cost"] == 0.0
    # No model-switch saving (already at minimum cost)
    assert result["potential_monthly_savings"] == 0.0
