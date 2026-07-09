import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI TestClient for the ArchitectIQ app."""
    return TestClient(app)


@pytest.fixture
def sample_architecture() -> dict:
    """Return a valid sample architecture request payload."""
    return {
        "project_name": "Production RAG Pipeline",
        "llm": "gpt-4o",
        "embedding_model": "text-embedding-3-small",
        "vector_db": "pinecone",
        "framework": "FastAPI",
        "memory": False,
        "rag_enabled": True,
        "cache_enabled": True,
        "prompt_strategy": "few-shot",
        "monthly_requests": 1_000_000,
        "average_prompt_tokens": 1_500,
        "average_completion_tokens": 400,
        "context_window": 128_000,
        "concurrent_users": 5_000,
        "observability": True,
        "authentication": True,
        "rate_limiting": True,
        "retry_strategy": True,
    }


@pytest.fixture
def sample_architecture_with_issues() -> dict:
    """Return a sample architecture request with several production issues."""
    return {
        "project_name": "Costly RAG Pipeline",
        "llm": "gpt-4",
        "embedding_model": "text-embedding-3-small",
        "vector_db": "pinecone",
        "framework": "FastAPI",
        "memory": False,
        "rag_enabled": True,
        "cache_enabled": False,
        "prompt_strategy": "zero-shot",
        "monthly_requests": 1_500_000,
        "average_prompt_tokens": 4_000,
        "average_completion_tokens": 1_500,
        "context_window": 128_000,
        "concurrent_users": 10_000,
        "observability": False,
        "authentication": False,
        "rate_limiting": False,
        "retry_strategy": False,
    }
