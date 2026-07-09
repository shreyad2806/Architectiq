import pytest

from app.schemas import ReviewRequest
from app.services.cost_analyzer import CostAnalyzer


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
    analyzer = CostAnalyzer()
    result = analyzer.analyze(sample_review_request)

    # Expected tokens: 100_000 * (1_400 + 500) = 190_000_000
    # gpt-4o cost: (140M/1M * 2.50) + (50M/1M * 10.00) = 350 + 500 = 850
    # gpt-4o-mini baseline: (140M/1M * 0.15) + (50M/1M * 0.60) = 21 + 30 = 51
    # savings: 850 - 51 = 799
    assert result["estimated_monthly_cost"] == 850.0
    assert result["potential_monthly_savings"] == 799.0


def test_cost_analyzer_llama3_is_free():
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
    assert result["estimated_monthly_tokens"] == 120_000_000
    assert result["estimated_monthly_cost"] == 0.0
    assert result["potential_monthly_savings"] == 0.0
