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
        "name": "Production RAG Pipeline",
        "description": "Retrieval-augmented generation for customer support.",
        "components": [
            {"type": "llm", "provider": "openai", "model": "gpt-4o"},
            {"type": "vector_store", "provider": "pinecone"},
            {"type": "gateway", "provider": "internal"},
        ],
        "estimated_requests_per_month": 1_000_000,
        "average_input_tokens": 1_500,
        "average_output_tokens": 400,
    }


@pytest.fixture
def sample_architecture_with_issues() -> dict:
    """Return a sample architecture request with several production issues."""
    return {
        "name": "Costly RAG Pipeline",
        "description": "High traffic RAG pipeline with missing production patterns.",
        "components": [
            {"type": "llm", "provider": "openai", "model": "gpt-4"},
            {"type": "vector_store", "provider": "pinecone"},
            {"type": "gateway", "provider": "internal"},
        ],
        "estimated_requests_per_month": 1_500_000,
        "average_input_tokens": 4_000,
        "average_output_tokens": 1_500,
    }
