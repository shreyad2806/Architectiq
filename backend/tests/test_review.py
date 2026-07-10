import pytest


def test_review_success(client, sample_architecture_with_issues):
    response = client.post("/api/v1/review", json=sample_architecture_with_issues)
    assert response.status_code == 200

    data = response.json()
    assert data["project_name"] == sample_architecture_with_issues["project_name"]

    # architecture_overview
    ao = data["architecture_overview"]
    assert isinstance(ao["overall_score"], int)
    assert 0 <= ao["overall_score"] <= 100
    assert isinstance(ao["architecture_grade"], str)
    assert isinstance(ao["production_readiness"], int)
    assert 0 <= ao["production_readiness"] <= 100

    # cost_analysis
    ca = data["cost_analysis"]
    assert "estimated_monthly_cost" in ca
    assert "potential_monthly_savings" in ca
    assert "savings_percentage" in ca

    # recommendations — rich shape
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) > 0
    for rec in data["recommendations"]:
        assert "priority" in rec
        assert rec["priority"] in {"HIGH", "MEDIUM", "LOW"}
        assert "title" in rec
        assert "reason" in rec

    # optimization_roadmap
    assert isinstance(data["optimization_roadmap"], list)

    # findings_summary
    fs = data["findings_summary"]
    assert isinstance(fs["total"], int)
    assert "by_severity" in fs
    assert "by_category" in fs

    # critical_risks
    assert isinstance(data["critical_risks"], list)

    # audit_report metadata
    ar = data["audit_report"]
    assert isinstance(ar["report_id"], str)
    assert isinstance(ar["audit_duration_ms"], int)
    assert isinstance(ar["total_findings"], int)
    assert isinstance(ar["total_recommendations"], int)

    # agent_response — new rich machine-readable block
    assert "agent_response" in data
    agr = data["agent_response"]

    # agent block
    agent = agr["agent"]
    assert agent["name"] == "ArchitectIQ"
    assert agent["version"] == "1.0.0"
    assert agent["status"] == "completed"
    assert isinstance(agent["generated_at"], str) and "T" in agent["generated_at"]

    # summary block — all dynamic from live report
    summary = agr["summary"]
    assert isinstance(summary["architecture_score"], int)
    assert 0 <= summary["architecture_score"] <= 100
    assert isinstance(summary["grade"], str) and len(summary["grade"]) >= 1
    assert isinstance(summary["production_readiness"], int)
    assert isinstance(summary["estimated_monthly_cost"], str)
    assert isinstance(summary["potential_monthly_savings"], str)

    # top_priority block
    tp = agr["top_priority"]
    assert isinstance(tp["title"], str) and len(tp["title"]) > 0
    assert tp["priority"] in {"HIGH", "MEDIUM", "LOW"}
    assert isinstance(tp["estimated_impact"], str) and len(tp["estimated_impact"]) > 0

    # next_action and report_status
    assert isinstance(agr["next_action"], str) and len(agr["next_action"]) > 0
    assert agr["report_status"] == "complete"


def test_review_schema_validation(client, sample_architecture_with_issues):
    response = client.post("/api/v1/review", json=sample_architecture_with_issues)
    assert response.status_code == 200

    data = response.json()
    assert "project_name" in data
    assert "intelligence_summary" in data
    assert "architecture_overview" in data
    assert "score_breakdown" in data
    assert "cost_analysis" in data
    assert "latency_analysis" in data
    assert "recommendations" in data
    assert "optimization_roadmap" in data
    assert "critical_risks" in data
    assert "findings_summary" in data
    assert "audit_report" in data
    assert "agent_response" in data
    assert "report_metadata" in data

    # report_metadata contract
    rm = data["report_metadata"]
    assert isinstance(rm["report_id"], str) and len(rm["report_id"]) > 0
    assert isinstance(rm["generated_at"], str) and "T" in rm["generated_at"]
    assert isinstance(rm["analysis_duration_ms"], int) and rm["analysis_duration_ms"] >= 0
    assert rm["architectiq_version"] == "1.0.0"
    assert rm["environment"] == "Production"
    assert rm["analyzers_executed"] == 8

    for rec in data["recommendations"]:
        assert "priority" in rec
        assert "title" in rec
        assert "reason" in rec
        assert "difficulty" in rec
        assert "implementation_time" in rec


def test_review_empty_payload(client):
    response = client.post("/api/v1/review", json={})
    assert response.status_code == 422


def test_review_missing_project_name(client, sample_architecture):
    payload = sample_architecture.copy()
    del payload["project_name"]
    response = client.post("/api/v1/review", json=payload)
    assert response.status_code == 422


def test_review_invalid_component_type(client, sample_architecture):
    payload = sample_architecture.copy()
    payload["components"] = [{"type": 123, "provider": "openai"}]
    response = client.post("/api/v1/review", json=payload)
    assert response.status_code == 422


def test_review_negative_tokens(client, sample_architecture):
    payload = sample_architecture.copy()
    payload["average_prompt_tokens"] = -100
    response = client.post("/api/v1/review", json=payload)
    assert response.status_code == 422
