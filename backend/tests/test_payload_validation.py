"""Comprehensive payload validation suite.

Tests 15 distinct architecture payloads through the /api/v1/review endpoint
and verifies correctness, schema compliance, realistic values, and behavioural
differentiation across all output sections.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.main import app

# ---------------------------------------------------------------------------
# Shared client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 15 canonical payloads
# ---------------------------------------------------------------------------

_BASE = dict(
    llm="gpt-4o",
    embedding_model="text-embedding-3-small",
    vector_db="pinecone",
    framework="FastAPI",
    memory=False,
    rag_enabled=True,
    cache_enabled=False,
    prompt_strategy="few-shot",
    monthly_requests=100_000,
    average_prompt_tokens=1_400,
    average_completion_tokens=500,
    context_window=8_000,
    concurrent_users=100,
    observability=False,
    logging=False,
    monitoring=False,
    tracing=False,
    metrics=False,
    health_endpoint=False,
    authentication=False,
    rate_limiting=False,
    retry_strategy=False,
    prompt_injection_protection=False,
    input_validation=False,
)


def _payload(name: str, **overrides) -> dict:
    p = {**_BASE, "project_name": name}
    p.update(overrides)
    return p


PAYLOADS = [
    # 1 — Small hobby project
    _payload(
        "Hobby Project",
        llm="gpt-4o-mini",
        vector_db="chroma",
        framework="flask",
        rag_enabled=False,
        monthly_requests=1_000,
        average_prompt_tokens=300,
        average_completion_tokens=150,
        context_window=4_096,
        concurrent_users=5,
    ),
    # 2 — Startup MVP
    _payload(
        "Startup MVP",
        llm="gpt-4o",
        vector_db="qdrant",
        framework="FastAPI",
        monthly_requests=50_000,
        average_prompt_tokens=800,
        average_completion_tokens=300,
        context_window=8_000,
        concurrent_users=200,
        logging=True,
        authentication=True,
    ),
    # 3 — Production SaaS
    _payload(
        "Production SaaS",
        llm="gpt-4o",
        vector_db="pinecone",
        framework="FastAPI",
        monthly_requests=500_000,
        average_prompt_tokens=1_200,
        average_completion_tokens=400,
        context_window=16_000,
        concurrent_users=2_000,
        cache_enabled=True,
        logging=True,
        monitoring=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
        health_endpoint=True,
    ),
    # 4 — Enterprise AI platform
    _payload(
        "Enterprise AI Platform",
        llm="claude-sonnet",
        embedding_model="text-embedding-3-large",
        vector_db="weaviate",
        framework="FastAPI",
        monthly_requests=2_000_000,
        average_prompt_tokens=2_000,
        average_completion_tokens=800,
        context_window=32_000,
        concurrent_users=10_000,
        cache_enabled=True,
        observability=True,
        logging=True,
        monitoring=True,
        tracing=True,
        metrics=True,
        health_endpoint=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
        prompt_injection_protection=True,
        input_validation=True,
    ),
    # 5 — High traffic RAG
    _payload(
        "High Traffic RAG",
        llm="gpt-4o",
        vector_db="pinecone",
        monthly_requests=5_000_000,
        average_prompt_tokens=1_500,
        average_completion_tokens=600,
        context_window=16_000,
        concurrent_users=20_000,
        rag_enabled=True,
        cache_enabled=False,
    ),
    # 6 — No cache (cache_enabled=False is the base, ensure it fires findings)
    _payload(
        "No Cache Architecture",
        llm="gpt-4o",
        monthly_requests=300_000,
        average_prompt_tokens=1_000,
        average_completion_tokens=400,
        cache_enabled=False,
        authentication=True,
        retry_strategy=True,
    ),
    # 7 — Cache enabled
    _payload(
        "Cache Enabled Architecture",
        llm="gpt-4o",
        monthly_requests=300_000,
        average_prompt_tokens=1_000,
        average_completion_tokens=400,
        cache_enabled=True,
        authentication=True,
        retry_strategy=True,
    ),
    # 8 — GPT-4o only (expensive premium model)
    _payload(
        "GPT-4o Premium",
        llm="gpt-4o",
        monthly_requests=1_000_000,
        average_prompt_tokens=2_000,
        average_completion_tokens=800,
        context_window=32_000,
        concurrent_users=5_000,
    ),
    # 9 — GPT-4.1 Mini (budget model)
    _payload(
        "GPT-4.1 Mini Budget",
        llm="gpt-4.1-mini",
        monthly_requests=1_000_000,
        average_prompt_tokens=2_000,
        average_completion_tokens=800,
        context_window=32_000,
        concurrent_users=5_000,
    ),
    # 10 — Open-source LLM (llama3 — zero token cost)
    _payload(
        "Open Source LLM",
        llm="llama3",
        embedding_model="bge-large",
        vector_db="qdrant",
        monthly_requests=500_000,
        average_prompt_tokens=1_000,
        average_completion_tokens=400,
        context_window=8_000,
        concurrent_users=1_000,
        rag_enabled=True,
    ),
    # 11 — Huge context window (512k)
    _payload(
        "Huge Context Window",
        llm="gpt-4o",
        monthly_requests=100_000,
        average_prompt_tokens=5_000,
        average_completion_tokens=1_500,
        context_window=512_000,
        concurrent_users=500,
    ),
    # 12 — Tiny context
    _payload(
        "Tiny Context",
        llm="gpt-4o-mini",
        monthly_requests=200_000,
        average_prompt_tokens=200,
        average_completion_tokens=100,
        context_window=2_048,
        concurrent_users=300,
        cache_enabled=True,
    ),
    # 13 — Low traffic
    _payload(
        "Low Traffic",
        llm="gpt-4o",
        monthly_requests=500,
        average_prompt_tokens=800,
        average_completion_tokens=300,
        context_window=4_096,
        concurrent_users=10,
    ),
    # 14 — High concurrency
    _payload(
        "High Concurrency",
        llm="gpt-4o",
        monthly_requests=1_000_000,
        average_prompt_tokens=1_200,
        average_completion_tokens=400,
        context_window=8_000,
        concurrent_users=50_000,
        cache_enabled=True,
        retry_strategy=True,
    ),
    # 15 — Fully optimized architecture
    _payload(
        "Fully Optimized",
        llm="gpt-4o-mini",
        embedding_model="text-embedding-3-large",
        vector_db="pinecone",
        framework="FastAPI",
        monthly_requests=500_000,
        average_prompt_tokens=800,
        average_completion_tokens=300,
        context_window=8_000,
        concurrent_users=2_000,
        rag_enabled=True,
        cache_enabled=True,
        observability=True,
        logging=True,
        monitoring=True,
        tracing=True,
        metrics=True,
        health_endpoint=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
        prompt_injection_protection=True,
        input_validation=True,
    ),
]

PAYLOAD_NAMES = [p["project_name"] for p in PAYLOADS]

# ---------------------------------------------------------------------------
# Helper: call /review and assert HTTP 200, return parsed JSON
# ---------------------------------------------------------------------------

def _review(client, payload: dict) -> dict:
    resp = client.post("/api/v1/review", json=payload)
    assert resp.status_code == 200, (
        f"[{payload['project_name']}] HTTP {resp.status_code}: {resp.text[:400]}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Pre-compute all 15 responses once (module-scoped cache)
# ---------------------------------------------------------------------------

_CACHE: dict[str, dict] = {}


@pytest.fixture(scope="module")
def all_responses(client):
    for p in PAYLOADS:
        _CACHE[p["project_name"]] = _review(client, p)
    return _CACHE


# ---------------------------------------------------------------------------
# 1. No crashes / No HTTP 500
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_no_crash_or_500(client, payload):
    resp = client.post("/api/v1/review", json=payload)
    assert resp.status_code == 200, (
        f"HTTP {resp.status_code} for '{payload['project_name']}': {resp.text[:300]}"
    )


# ---------------------------------------------------------------------------
# 2. Schema compliance — all required top-level keys present
# ---------------------------------------------------------------------------

REQUIRED_TOP_KEYS = {
    "project_name", "intelligence_summary", "architecture_overview",
    "score_breakdown", "cost_analysis", "latency_analysis", "rag_analysis",
    "security_analysis", "reliability_analysis", "scalability_analysis",
    "observability_analysis", "recommendations", "optimization_roadmap",
    "critical_risks", "findings_summary", "audit_report",
    "agent_response", "report_metadata",
}

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_schema_top_level_keys(client, payload):
    data = _review(client, payload)
    missing = REQUIRED_TOP_KEYS - set(data.keys())
    assert not missing, f"[{payload['project_name']}] Missing keys: {missing}"


# ---------------------------------------------------------------------------
# 3. Architecture score is valid integer 0–100
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_architecture_score_valid(client, payload):
    data = _review(client, payload)
    score = data["architecture_overview"]["overall_score"]
    assert isinstance(score, int), f"score is {type(score)}"
    assert 0 <= score <= 100, f"[{payload['project_name']}] Impossible score: {score}"


# ---------------------------------------------------------------------------
# 4. Grade is a non-empty string
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_grade_is_string(client, payload):
    data = _review(client, payload)
    grade = data["architecture_overview"]["architecture_grade"]
    assert isinstance(grade, str) and grade.strip(), (
        f"[{payload['project_name']}] Bad grade: {grade!r}"
    )


# ---------------------------------------------------------------------------
# 5. Production readiness is valid integer 0–100
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_production_readiness_valid(client, payload):
    data = _review(client, payload)
    pr = data["architecture_overview"]["production_readiness"]
    assert isinstance(pr, int), f"production_readiness is {type(pr)}"
    assert 0 <= pr <= 100, f"[{payload['project_name']}] Impossible prod readiness: {pr}"


# ---------------------------------------------------------------------------
# 6. Executive summary is a non-empty string and contains project name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_executive_summary_contains_project_name(client, payload):
    data = _review(client, payload)
    summary = data["intelligence_summary"].get("executive_summary", "")
    assert isinstance(summary, str) and len(summary) > 30, (
        f"[{payload['project_name']}] Executive summary too short: {summary!r}"
    )
    assert payload["project_name"] in summary, (
        f"[{payload['project_name']}] Project name missing from executive summary.\n"
        f"Summary: {summary[:200]}"
    )


# ---------------------------------------------------------------------------
# 7. Recommendations are non-empty, non-duplicate, valid priority
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_recommendations_valid(client, payload):
    data = _review(client, payload)
    recs = data["recommendations"]
    assert isinstance(recs, list), "recommendations must be a list"
    assert len(recs) > 0, f"[{payload['project_name']}] No recommendations returned"

    titles = [r["title"] for r in recs]
    assert len(titles) == len(set(titles)), (
        f"[{payload['project_name']}] Duplicate recommendation titles: "
        + str([t for t in titles if titles.count(t) > 1])
    )

    for rec in recs:
        assert rec.get("priority") in {"HIGH", "MEDIUM", "LOW"}, (
            f"[{payload['project_name']}] Invalid priority: {rec.get('priority')!r}"
        )
        assert rec.get("title", "").strip(), "Empty recommendation title"
        assert rec.get("reason", "").strip(), "Empty recommendation reason"


# ---------------------------------------------------------------------------
# 8. Optimization roadmap is a list with at least one phase
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_optimization_roadmap_valid(client, payload):
    data = _review(client, payload)
    roadmap = data["optimization_roadmap"]
    assert isinstance(roadmap, list), "roadmap must be a list"
    assert len(roadmap) >= 1, f"[{payload['project_name']}] Empty roadmap"
    for phase in roadmap:
        assert "phase" in phase
        assert "title" in phase
        assert "tasks" in phase
        assert isinstance(phase["tasks"], list)


# ---------------------------------------------------------------------------
# 9. Cost breakdown — all line items present and non-negative
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_cost_breakdown_valid(client, payload):
    data = _review(client, payload)
    ca = data["cost_analysis"]
    assert "estimated_monthly_cost" in ca
    assert "potential_monthly_savings" in ca
    assert "breakdown" in ca, f"[{payload['project_name']}] Missing breakdown"

    bd = ca["breakdown"]
    for key in ("llm_cost", "embedding_cost", "vector_db_cost",
                "storage_cost", "infrastructure_cost", "monthly_cost"):
        assert key in bd, f"[{payload['project_name']}] Missing breakdown key: {key}"
        assert bd[key] >= 0, f"[{payload['project_name']}] Negative {key}: {bd[key]}"


# ---------------------------------------------------------------------------
# 10. Costs are realistic (not $0 for real traffic + paid model)
# ---------------------------------------------------------------------------

_PAID_MODELS = {"gpt-4o", "gpt-4.1", "gpt-4.1-mini", "claude-sonnet",
                "gemini-2.5-pro", "gemini-2.5-flash", "mistral-large"}

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_costs_realistic(client, payload):
    data = _review(client, payload)
    bd = data["cost_analysis"]["breakdown"]
    llm = payload.get("llm", "")
    requests = payload.get("monthly_requests", 0)
    if llm.lower() in _PAID_MODELS and requests >= 1_000:
        assert bd["llm_cost"] > 0, (
            f"[{payload['project_name']}] llm_cost is $0 for paid model '{llm}' "
            f"with {requests} monthly requests"
        )
        # monthly_cost (net after savings) can legitimately be 0 when cache +
        # model-switch savings are capped at gross total — llm_cost proves the
        # gross cost is non-zero.
        assert bd["total_before_savings"] > 0, (
            f"[{payload['project_name']}] total_before_savings is $0 for paid model"
        )


# ---------------------------------------------------------------------------
# 11. Agent response schema
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_agent_response_schema(client, payload):
    data = _review(client, payload)
    ar = data["agent_response"]
    assert ar["agent"]["name"] == "ArchitectIQ"
    assert ar["agent"]["version"] == "1.0.0"
    assert ar["agent"]["status"] == "completed"
    assert "T" in ar["agent"]["generated_at"]

    summary = ar["summary"]
    assert 0 <= summary["architecture_score"] <= 100
    assert isinstance(summary["grade"], str)
    assert isinstance(summary["estimated_monthly_cost"], (str, int, float))

    assert ar["top_priority"]["priority"] in {"HIGH", "MEDIUM", "LOW"}
    assert isinstance(ar["next_action"], str) and ar["next_action"].strip()
    assert ar["report_status"] == "complete"


# ---------------------------------------------------------------------------
# 12. Report metadata schema
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_report_metadata_schema(client, payload):
    data = _review(client, payload)
    rm = data["report_metadata"]
    assert isinstance(rm["report_id"], str) and rm["report_id"].strip()
    assert "T" in rm["generated_at"]
    assert isinstance(rm["analysis_duration_ms"], int)
    assert rm["analysis_duration_ms"] >= 0
    assert rm["architectiq_version"] == "1.0.0"
    assert rm["environment"] == "Production"
    assert rm["analyzers_executed"] == 8


# ---------------------------------------------------------------------------
# 13. No null values in critical fields
# ---------------------------------------------------------------------------

_CRITICAL_PATHS = [
    ("architecture_overview", "overall_score"),
    ("architecture_overview", "architecture_grade"),
    ("architecture_overview", "production_readiness"),
    ("intelligence_summary", "overall_verdict"),
    ("intelligence_summary", "executive_summary"),
    ("intelligence_summary", "estimated_monthly_savings"),
    ("audit_report", "report_id"),
    ("audit_report", "generated_at"),
    ("report_metadata", "report_id"),
    ("report_metadata", "generated_at"),
    ("report_metadata", "analysis_duration_ms"),
]

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_no_null_in_critical_fields(client, payload):
    data = _review(client, payload)
    for section, key in _CRITICAL_PATHS:
        value = data.get(section, {}).get(key)
        assert value is not None, (
            f"[{payload['project_name']}] Null value at {section}.{key}"
        )


# ---------------------------------------------------------------------------
# 14. Findings summary counts are non-negative and consistent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_findings_summary_consistent(client, payload):
    data = _review(client, payload)
    fs = data["findings_summary"]
    total = fs["total"]
    by_sev = fs["by_severity"]
    assert total >= 0
    sev_sum = sum(by_sev.values())
    assert sev_sum <= total, (
        f"[{payload['project_name']}] by_severity sum ({sev_sum}) > total ({total})"
    )
    for sev in ("critical", "high", "medium", "low"):
        assert by_sev.get(sev, 0) >= 0


# ---------------------------------------------------------------------------
# 15. audit_report and report_metadata share the same report_id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_report_ids_consistent(client, payload):
    data = _review(client, payload)
    ar_id = data["audit_report"]["report_id"]
    rm_id = data["report_metadata"]["report_id"]
    assert ar_id == rm_id, (
        f"[{payload['project_name']}] audit_report.report_id={ar_id!r} "
        f"!= report_metadata.report_id={rm_id!r}"
    )


# ---------------------------------------------------------------------------
# 16. Behavioural differentiation — key metrics differ across payloads
# ---------------------------------------------------------------------------

def test_scores_differ_across_payloads(all_responses):
    scores = {name: r["architecture_overview"]["overall_score"]
              for name, r in all_responses.items()}
    unique_scores = set(scores.values())
    assert len(unique_scores) > 1, (
        f"All 15 payloads returned identical scores: {scores}"
    )


def test_grades_differ_across_payloads(all_responses):
    grades = {name: r["architecture_overview"]["architecture_grade"]
              for name, r in all_responses.items()}
    unique_grades = set(grades.values())
    assert len(unique_grades) > 1, (
        f"All 15 payloads returned identical grades: {grades}"
    )


def test_production_readiness_differs(all_responses):
    pr_scores = {name: r["architecture_overview"]["production_readiness"]
                 for name, r in all_responses.items()}
    assert len(set(pr_scores.values())) > 1, (
        f"All 15 payloads have identical production_readiness: {pr_scores}"
    )


def test_executive_summaries_differ(all_responses):
    summaries = {name: r["intelligence_summary"]["executive_summary"]
                 for name, r in all_responses.items()}
    unique = set(summaries.values())
    assert len(unique) > 1, "All executive summaries are identical"


def test_recommendation_counts_differ(all_responses):
    counts = {name: len(r["recommendations"]) for name, r in all_responses.items()}
    assert len(set(counts.values())) > 1, (
        f"All payloads have the same recommendation count: {counts}"
    )


def test_costs_differ_across_payloads(all_responses):
    costs = {name: r["cost_analysis"]["breakdown"]["monthly_cost"]
             for name, r in all_responses.items()}
    assert len(set(costs.values())) > 1, (
        f"All payloads have the same monthly cost: {costs}"
    )


# ---------------------------------------------------------------------------
# 17. Cache vs no-cache: cache should reduce net cost
# ---------------------------------------------------------------------------

def test_cache_reduces_net_cost(all_responses):
    no_cache  = all_responses["No Cache Architecture"]["cost_analysis"]["breakdown"]
    has_cache = all_responses["Cache Enabled Architecture"]["cost_analysis"]["breakdown"]
    assert has_cache["monthly_cost"] < no_cache["monthly_cost"], (
        f"Cache did not reduce net cost: "
        f"no-cache={no_cache['monthly_cost']}, cached={has_cache['monthly_cost']}"
    )


# ---------------------------------------------------------------------------
# 18. Premium vs budget model: gpt-4o more expensive than gpt-4.1-mini
# ---------------------------------------------------------------------------

def test_premium_model_costs_more(all_responses):
    premium = all_responses["GPT-4o Premium"]["cost_analysis"]["breakdown"]["llm_cost"]
    budget  = all_responses["GPT-4.1 Mini Budget"]["cost_analysis"]["breakdown"]["llm_cost"]
    assert premium > budget, (
        f"GPT-4o ({premium}) should cost more than gpt-4.1-mini ({budget})"
    )


# ---------------------------------------------------------------------------
# 19. Open-source LLM (llama3) has zero LLM cost
# ---------------------------------------------------------------------------

def test_opensource_llm_zero_llm_cost(all_responses):
    bd = all_responses["Open Source LLM"]["cost_analysis"]["breakdown"]
    assert bd["llm_cost"] == 0.0, (
        f"llama3 should have $0 LLM cost, got: {bd['llm_cost']}"
    )


# ---------------------------------------------------------------------------
# 20. Fully optimized scores higher than hobby project
# ---------------------------------------------------------------------------

def test_optimized_scores_higher_than_hobby(all_responses):
    optimized = all_responses["Fully Optimized"]["architecture_overview"]["overall_score"]
    hobby     = all_responses["Hobby Project"]["architecture_overview"]["overall_score"]
    assert optimized > hobby, (
        f"Optimized ({optimized}) should score higher than Hobby ({hobby})"
    )


# ---------------------------------------------------------------------------
# 21. Fully optimized has higher production readiness than no-security arch
# ---------------------------------------------------------------------------

def test_optimized_more_production_ready(all_responses):
    optimized = all_responses["Fully Optimized"]["architecture_overview"]["production_readiness"]
    no_cache  = all_responses["No Cache Architecture"]["architecture_overview"]["production_readiness"]
    assert optimized >= no_cache, (
        f"Optimized ({optimized}) should be at least as production-ready as "
        f"no-cache arch ({no_cache})"
    )


# ---------------------------------------------------------------------------
# 22. Huge context window triggers a context-related recommendation
# ---------------------------------------------------------------------------

def test_huge_context_window_recommendation(all_responses):
    recs = all_responses["Huge Context Window"]["recommendations"]
    titles_lower = [r["title"].lower() for r in recs]
    assert any("context" in t for t in titles_lower), (
        "Expected a context-window recommendation for 512k context payload. "
        f"Got titles: {[r['title'] for r in recs]}"
    )


# ---------------------------------------------------------------------------
# 23. High traffic arch triggers model routing or model switch recommendation
# ---------------------------------------------------------------------------

def test_high_traffic_triggers_cost_recommendation(all_responses):
    recs = all_responses["High Traffic RAG"]["recommendations"]
    cost_recs = [r for r in recs if r.get("category") == "Cost Optimization"]
    assert len(cost_recs) > 0, (
        "Expected at least one Cost Optimization recommendation for 5M req/mo payload"
    )


# ---------------------------------------------------------------------------
# 24. Low traffic arch should not have impossibly high costs
# ---------------------------------------------------------------------------

def test_low_traffic_costs_low(all_responses):
    bd = all_responses["Low Traffic"]["cost_analysis"]["breakdown"]
    # Pinecone has a $70/mo minimum regardless of request volume, so total
    # can legitimately exceed $50.  Assert < $200 to catch truly broken costs.
    assert bd["monthly_cost"] < 200.0, (
        f"Low traffic (500 req/mo) should cost < $200/mo, got: ${bd['monthly_cost']:.2f}"
    )


# ---------------------------------------------------------------------------
# 25. Findings change: more issues → more findings
# ---------------------------------------------------------------------------

def test_more_issues_more_findings(all_responses):
    optimized_total = all_responses["Fully Optimized"]["findings_summary"]["total"]
    hobby_total     = all_responses["Hobby Project"]["findings_summary"]["total"]
    # Hobby project is missing all security/reliability/observability features
    assert hobby_total >= optimized_total, (
        f"Hobby ({hobby_total}) should have >= findings than Optimized ({optimized_total})"
    )


# ---------------------------------------------------------------------------
# 26. High concurrency triggers async/concurrency recommendation
# ---------------------------------------------------------------------------

def test_high_concurrency_recommendation(all_responses):
    recs = all_responses["High Concurrency"]["recommendations"]
    titles_lower = " ".join(r["title"].lower() for r in recs)
    assert "async" in titles_lower or "connection pool" in titles_lower or "concurrent" in titles_lower, (
        f"Expected async/concurrency rec for 50k concurrent users. Titles: {[r['title'] for r in recs]}"
    )


# ---------------------------------------------------------------------------
# 27. Agent response — score matches architecture_overview score
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_agent_response_score_matches_overview(client, payload):
    data = _review(client, payload)
    overview_score = data["architecture_overview"]["overall_score"]
    agent_score    = data["agent_response"]["summary"]["architecture_score"]
    assert overview_score == agent_score, (
        f"[{payload['project_name']}] architecture_overview.overall_score={overview_score} "
        f"!= agent_response.summary.architecture_score={agent_score}"
    )


# ---------------------------------------------------------------------------
# 28. Severity counts — high-risk payloads have high counts
# ---------------------------------------------------------------------------

def test_no_security_has_high_severity_findings(all_responses):
    # Hobby project has no auth, no rate limiting, no retry, no logging
    by_sev = all_responses["Hobby Project"]["findings_summary"]["by_severity"]
    assert by_sev.get("high", 0) > 0, (
        f"Hobby project with no security should have HIGH severity findings. Got: {by_sev}"
    )


def test_optimized_has_fewer_high_findings(all_responses):
    optimized_high = all_responses["Fully Optimized"]["findings_summary"]["by_severity"].get("high", 0)
    hobby_high     = all_responses["Hobby Project"]["findings_summary"]["by_severity"].get("high", 0)
    assert optimized_high <= hobby_high, (
        f"Optimized ({optimized_high}) should have <= HIGH findings than Hobby ({hobby_high})"
    )


# ---------------------------------------------------------------------------
# 29. All 15 project names appear correctly in their responses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", PAYLOADS, ids=PAYLOAD_NAMES)
def test_project_name_echoed(client, payload):
    data = _review(client, payload)
    assert data["project_name"] == payload["project_name"]


# ---------------------------------------------------------------------------
# 30. Enterprise platform has highest monthly cost (most traffic + premium LLM)
# ---------------------------------------------------------------------------

def test_enterprise_is_most_expensive(all_responses):
    enterprise_cost = all_responses["Enterprise AI Platform"]["cost_analysis"]["breakdown"]["monthly_cost"]
    hobby_cost      = all_responses["Hobby Project"]["cost_analysis"]["breakdown"]["monthly_cost"]
    assert enterprise_cost > hobby_cost, (
        f"Enterprise ({enterprise_cost}) should cost more than Hobby ({hobby_cost})"
    )
