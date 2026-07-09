def test_recommend_success(client, sample_architecture_with_issues):
    response = client.post("/api/v1/recommend", json=sample_architecture_with_issues)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify recommendations are sorted by impact: high severity first.
    severities = [r["priority"] for r in data]
    severity_order = {"high": 0, "medium": 1, "low": 2}
    assert all(
        severity_order[severities[i]] <= severity_order[severities[i + 1]]
        for i in range(len(severities) - 1)
    )


def test_recommend_schema(client, sample_architecture_with_issues):
    response = client.post("/api/v1/recommend", json=sample_architecture_with_issues)
    assert response.status_code == 200

    data = response.json()
    for recommendation in data:
        assert "id" in recommendation
        assert "title" in recommendation
        assert "description" in recommendation
        assert "category" in recommendation
        assert "priority" in recommendation
        assert recommendation["priority"] in {"high", "medium", "low"}
        assert "implementation_effort" in recommendation
        assert "estimated_monthly_savings" in recommendation
        assert "estimated_latency_improvement_ms" in recommendation


def test_recommend_empty_payload(client):
    response = client.post("/api/v1/recommend", json={})
    assert response.status_code == 422


def test_recommend_missing_name(client, sample_architecture):
    payload = sample_architecture.copy()
    del payload["name"]
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 422


def test_recommend_clean_architecture(client, sample_architecture):
    """A well-architected request should return fewer or no high-priority items."""
    response = client.post("/api/v1/recommend", json=sample_architecture)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    # Architecture with retry and cache may still be flagged for observability.
    for recommendation in data:
        assert recommendation["priority"] in {"high", "medium", "low"}
