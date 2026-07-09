import pytest


def test_review_success(client, sample_architecture_with_issues):
    response = client.post("/api/v1/review", json=sample_architecture_with_issues)
    assert response.status_code == 201

    data = response.json()
    assert data["architecture_name"] == sample_architecture_with_issues["name"]
    assert isinstance(data["id"], str)
    assert isinstance(data["overall_score"], int)
    assert 0 <= data["overall_score"] <= 100
    assert isinstance(data["production_readiness"], int)
    assert 0 <= data["production_readiness"] <= 100
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) > 0
    assert data["summary"]
    assert "cost_estimate" in data
    assert isinstance(data["cost_estimate"]["total_monthly_cost"], float)
    assert isinstance(data["cost_estimate"]["potential_monthly_savings"], float)


def test_review_schema_validation(client, sample_architecture_with_issues):
    response = client.post("/api/v1/review", json=sample_architecture_with_issues)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert "architecture_name" in data
    assert "overall_score" in data
    assert "production_readiness" in data
    assert "cost_estimate" in data
    assert "recommendations" in data
    assert "summary" in data

    for recommendation in data["recommendations"]:
        assert "id" in recommendation
        assert "title" in recommendation
        assert "description" in recommendation
        assert "category" in recommendation
        assert "priority" in recommendation
        assert recommendation["priority"] in {"high", "medium", "low"}
        assert "implementation_effort" in recommendation


def test_review_empty_payload(client):
    response = client.post("/api/v1/review", json={})
    assert response.status_code == 422


def test_review_missing_name(client, sample_architecture):
    payload = sample_architecture.copy()
    del payload["name"]
    response = client.post("/api/v1/review", json=payload)
    assert response.status_code == 422


def test_review_invalid_component_type(client, sample_architecture):
    payload = sample_architecture.copy()
    payload["components"] = [{"type": 123, "provider": "openai"}]
    response = client.post("/api/v1/review", json=payload)
    assert response.status_code == 422


def test_review_negative_tokens(client, sample_architecture):
    payload = sample_architecture.copy()
    payload["average_input_tokens"] = -100
    response = client.post("/api/v1/review", json=payload)
    assert response.status_code == 422
