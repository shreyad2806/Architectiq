def test_estimate_success(client, sample_architecture):
    response = client.post("/api/v1/estimate", json=sample_architecture)
    assert response.status_code == 200

    data = response.json()
    assert "total_monthly_cost" in data
    assert "tokens" in data
    assert "average_latency_ms" in data
    assert "potential_monthly_savings" in data
    assert "currency" in data

    assert isinstance(data["total_monthly_cost"], float)
    assert data["total_monthly_cost"] >= 0
    assert isinstance(data["average_latency_ms"], float)
    assert data["average_latency_ms"] >= 0
    assert isinstance(data["potential_monthly_savings"], float)
    assert data["potential_monthly_savings"] >= 0

    tokens = data["tokens"]
    assert "input_tokens" in tokens
    assert "output_tokens" in tokens
    assert "total_tokens" in tokens
    assert tokens["total_tokens"] == tokens["input_tokens"] + tokens["output_tokens"]


def test_estimate_schema(client, sample_architecture):
    response = client.post("/api/v1/estimate", json=sample_architecture)
    assert response.status_code == 200

    data = response.json()
    assert "model_costs" in data
    assert isinstance(data["model_costs"], list)
    assert len(data["model_costs"]) > 0
    assert "component" in data["model_costs"][0]
    assert "monthly_cost" in data["model_costs"][0]


def test_estimate_empty_payload(client):
    response = client.post("/api/v1/estimate", json={})
    assert response.status_code == 422


def test_estimate_missing_components(client, sample_architecture):
    payload = sample_architecture.copy()
    del payload["components"]
    response = client.post("/api/v1/estimate", json=payload)
    assert response.status_code == 422


def test_estimate_zero_traffic(client, sample_architecture):
    payload = sample_architecture.copy()
    payload["estimated_requests_per_month"] = 0
    response = client.post("/api/v1/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_monthly_cost"] == 0.0
    assert data["tokens"]["total_tokens"] == 0
