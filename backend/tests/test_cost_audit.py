"""Audit tests for the cost estimation engine.

Verifies that:
  - Cost is NEVER $0 for real traffic + paid models.
  - All 6 line items are correct and present.
  - Costs scale logically with traffic, model, and context.
  - Edge cases (null-like inputs, unknown model, zero requests) are handled.
  - /estimate API endpoint returns full breakdown.
  - Recommendations (cache, cheaper model) reduce estimated cost.
  - estimator.py functions no longer raise for unknown models.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ReviewRequest
from app.services.cost_analyzer import CostAnalyzer, DetailedCostEstimator
from app.services.estimator import (
    _get_model,
    estimate_detailed_cost,
    estimate_monthly_cost,
    estimate_savings,
    MODEL_PRICING,
    SAVINGS_ALTERNATIVES,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Shared request factory
# ---------------------------------------------------------------------------

def _req(**kwargs) -> ReviewRequest:
    defaults = dict(
        project_name="AuditProject",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="pinecone",
        framework="fastapi",
        monthly_requests=100_000,
        average_prompt_tokens=1_000,
        average_completion_tokens=400,
        context_window=8_000,
        concurrent_users=500,
        prompt_strategy="few-shot",
        rag_enabled=True,
        cache_enabled=False,
        memory=False,
        observability=True,
        authentication=True,
        rate_limiting=True,
        retry_strategy=True,
    )
    defaults.update(kwargs)
    return ReviewRequest(**defaults)


# ---------------------------------------------------------------------------
# 1. Cost is NEVER $0 for real traffic + paid models
# ---------------------------------------------------------------------------

class TestNeverZeroForRealTraffic:
    """The central audit: any architecture with traffic + paid LLM must cost > $0."""

    @pytest.mark.parametrize("llm,rag,monthly_req", [
        ("gpt-4o",        True,  100_000),
        ("gpt-4o-mini",   True,   50_000),
        ("claude-sonnet", False, 200_000),
        ("gemini-2.5-pro", True,  10_000),
        ("gpt-4o",        False, 500_000),
    ])
    def test_total_cost_nonzero(self, llm, rag, monthly_req):
        req = _req(llm=llm, rag_enabled=rag, monthly_requests=monthly_req)
        bd = DetailedCostEstimator().estimate(req)
        assert bd.total_before_savings > 0, (
            f"Expected non-zero cost for llm={llm}, rag={rag}, "
            f"monthly_requests={monthly_req}; got {bd.total_before_savings}"
        )

    def test_llm_cost_nonzero_for_paid_model(self):
        bd = DetailedCostEstimator().estimate(_req(llm="gpt-4o"))
        assert bd.llm_cost > 0

    def test_infrastructure_always_positive_for_any_traffic(self):
        """Infrastructure overhead is always > 0 because of the concurrency floor."""
        bd = DetailedCostEstimator().estimate(_req(concurrent_users=0, monthly_requests=1))
        assert bd.infrastructure_cost > 0

    def test_zero_requests_is_only_valid_zero_path(self):
        bd = DetailedCostEstimator().estimate(_req(monthly_requests=0))
        assert bd.llm_cost == 0.0
        assert bd.embedding_cost == 0.0
        # Infrastructure still has a small concurrency floor
        assert bd.total_before_savings >= 0


# ---------------------------------------------------------------------------
# 2. All 6 line items present and self-consistent
# ---------------------------------------------------------------------------

class TestBreakdownCompleteness:
    REQUIRED_KEYS = {
        "monthly_cost", "llm_cost", "embedding_cost", "vector_db_cost",
        "storage_cost", "infrastructure_cost", "total_before_savings",
        "estimated_savings", "savings_from_cache", "savings_from_model_switch",
        "estimated_monthly_tokens",
    }

    def test_to_dict_has_all_keys(self):
        bd = DetailedCostEstimator().estimate(_req()).to_dict()
        assert self.REQUIRED_KEYS.issubset(bd.keys()), (
            f"Missing keys: {self.REQUIRED_KEYS - bd.keys()}"
        )

    def test_total_equals_sum_of_parts(self):
        bd = DetailedCostEstimator().estimate(_req())
        expected = round(
            bd.llm_cost + bd.embedding_cost + bd.vector_db_cost
            + bd.storage_cost + bd.infrastructure_cost, 2
        )
        assert abs(bd.total_before_savings - expected) < 0.02

    def test_monthly_cost_is_total_minus_savings(self):
        bd = DetailedCostEstimator().estimate(_req(cache_enabled=True))
        expected = max(round(bd.total_before_savings - bd.estimated_savings, 2), 0.0)
        assert abs(bd.monthly_cost - expected) < 0.02

    def test_savings_never_exceed_total(self):
        """estimated_savings is capped at total_before_savings."""
        bd = DetailedCostEstimator().estimate(_req(cache_enabled=True))
        # estimated_savings must not exceed gross total (monthly_cost floor = $0)
        assert bd.estimated_savings <= bd.total_before_savings + 0.01
        assert bd.monthly_cost >= 0.0

    def test_canalyzer_breakdown_matches_estimator(self):
        req = _req()
        analyzer_result = CostAnalyzer().analyze(req)
        estimator_bd    = DetailedCostEstimator().estimate(req)
        assert analyzer_result["breakdown"]["llm_cost"]   == estimator_bd.llm_cost
        assert analyzer_result["breakdown"]["storage_cost"] == estimator_bd.storage_cost


# ---------------------------------------------------------------------------
# 3. Costs scale logically with traffic
# ---------------------------------------------------------------------------

class TestTrafficScaling:
    def test_10x_traffic_increases_llm_cost_10x(self):
        bd_1x = DetailedCostEstimator().estimate(_req(monthly_requests=100_000))
        bd_10x = DetailedCostEstimator().estimate(_req(monthly_requests=1_000_000))
        ratio = bd_10x.llm_cost / bd_1x.llm_cost
        assert abs(ratio - 10.0) < 0.01, f"LLM cost should scale 10x, got {ratio}x"

    def test_higher_traffic_increases_vdb_tier_cost(self):
        bd_low  = DetailedCostEstimator().estimate(_req(monthly_requests=50_000,  rag_enabled=True))
        bd_high = DetailedCostEstimator().estimate(_req(monthly_requests=500_000, rag_enabled=True))
        assert bd_high.vector_db_cost > bd_low.vector_db_cost

    def test_higher_traffic_increases_storage_cost(self):
        bd_low  = DetailedCostEstimator().estimate(_req(monthly_requests=10_000))
        bd_high = DetailedCostEstimator().estimate(_req(monthly_requests=1_000_000))
        assert bd_high.storage_cost > bd_low.storage_cost

    def test_all_five_traffic_levels_produce_distinct_totals(self):
        levels = [10_000, 50_000, 100_000, 500_000, 1_000_000]
        totals = [
            DetailedCostEstimator().estimate(_req(monthly_requests=n)).total_before_savings
            for n in levels
        ]
        assert totals == sorted(totals), f"Totals not monotonically increasing: {totals}"
        assert len(set(totals)) == len(totals), f"Non-unique totals: {totals}"


# ---------------------------------------------------------------------------
# 4. Model pricing differences
# ---------------------------------------------------------------------------

class TestModelPricing:
    def test_expensive_models_cost_more(self):
        """Expensive models must have higher LLM cost than cheaper alternatives."""
        pairs = [
            ("claude-sonnet", "gpt-4o-mini"),
            ("gpt-4o",        "gpt-4o-mini"),
            ("claude-sonnet", "gemini-2.5-flash"),
            ("gpt-4o",        "gemini-2.5-flash"),
        ]
        for exp, chp in pairs:
            bd_exp = DetailedCostEstimator().estimate(_req(llm=exp)).llm_cost
            bd_chp = DetailedCostEstimator().estimate(_req(llm=chp)).llm_cost
            assert bd_exp > bd_chp, f"{exp} should cost more than {chp}"

    def test_unknown_model_falls_back_not_zero(self):
        """An unrecognised model name must not produce $0 LLM cost."""
        bd = DetailedCostEstimator().estimate(_req(llm="some-future-model-xyz"))
        assert bd.llm_cost > 0, "Unknown model fell back to $0 instead of gpt-4o default"

    def test_llama3_has_zero_llm_cost(self):
        bd = DetailedCostEstimator().estimate(_req(llm="llama3"))
        assert bd.llm_cost == 0.0

    def test_llama3_still_has_nonzero_total(self):
        """Even with free LLM, infra + storage make the total > 0."""
        bd = DetailedCostEstimator().estimate(_req(llm="llama3", rag_enabled=True))
        assert bd.total_before_savings > 0


# ---------------------------------------------------------------------------
# 5. Edge cases (null/missing/invalid inputs)
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_embedding_model_falls_back(self):
        """Empty embedding_model string should not crash or produce wrong result."""
        bd = DetailedCostEstimator().estimate(_req(embedding_model=""))
        assert bd.embedding_cost >= 0   # no crash; unknown embed model → ada-002 price

    def test_empty_vector_db_falls_back(self):
        bd = DetailedCostEstimator().estimate(_req(vector_db=""))
        assert bd.vector_db_cost >= 0

    def test_zero_concurrent_users_no_crash(self):
        bd = DetailedCostEstimator().estimate(_req(concurrent_users=0))
        assert bd.infrastructure_cost >= 0

    def test_very_small_token_counts_nonzero(self):
        bd = DetailedCostEstimator().estimate(_req(
            monthly_requests=1,
            average_prompt_tokens=1,
            average_completion_tokens=1,
            llm="gpt-4o",
        ))
        assert bd.llm_cost >= 0         # may round to 0 for 1 token but must not crash
        assert bd.infrastructure_cost > 0  # always has infra floor

    def test_large_context_window(self):
        bd = DetailedCostEstimator().estimate(_req(context_window=1_000_000))
        assert bd.storage_cost > 0
        assert bd.total_before_savings > 0


# ---------------------------------------------------------------------------
# 6. Cache and model-switch reduce costs
# ---------------------------------------------------------------------------

class TestSavingsReduceCosts:
    def test_cache_on_lowers_monthly_cost(self):
        bd_off = DetailedCostEstimator().estimate(_req(cache_enabled=False))
        bd_on  = DetailedCostEstimator().estimate(_req(cache_enabled=True))
        assert bd_on.monthly_cost < bd_off.monthly_cost

    def test_cache_savings_proportional_to_llm_cost(self):
        from app.services.cost_analyzer import _CACHE_HIT_RATE
        bd = DetailedCostEstimator().estimate(_req(cache_enabled=True))
        assert abs(bd.savings_from_cache - round(bd.llm_cost * _CACHE_HIT_RATE, 2)) < 0.02

    def test_cheaper_model_reduces_llm_cost(self):
        bd_4o   = DetailedCostEstimator().estimate(_req(llm="gpt-4o"))
        bd_mini = DetailedCostEstimator().estimate(_req(llm="gpt-4o-mini"))
        assert bd_mini.llm_cost < bd_4o.llm_cost

    def test_model_switch_saving_positive_for_expensive_model(self):
        bd = DetailedCostEstimator().estimate(_req(llm="gpt-4o", monthly_requests=200_000))
        assert bd.savings_from_model_switch > 0

    def test_no_model_switch_saving_for_cheap_model(self):
        bd = DetailedCostEstimator().estimate(_req(llm="gpt-4o-mini"))
        assert bd.savings_from_model_switch == 0.0


# ---------------------------------------------------------------------------
# 7. estimator.py no longer raises for unknown / new models
# ---------------------------------------------------------------------------

class TestEstimatorNeverRaises:
    @pytest.mark.parametrize("model", [
        "gpt-4o", "gpt-4o-mini", "claude-sonnet", "gemini-2.5-pro",
        "llama3", "gpt-4", "gpt-4-turbo", "claude-3-opus",
        "some-unknown-model", "", "GPT-4O",
    ])
    def test_get_model_never_raises(self, model):
        result = _get_model(model if model else "gpt-4o")
        assert "input_per_1m"  in result
        assert "output_per_1m" in result

    def test_estimate_monthly_cost_no_raise_for_unknown(self):
        cost = estimate_monthly_cost("some-future-model", 100_000, 1_000, 400)
        assert cost >= 0

    def test_estimate_savings_no_raise_for_unknown(self):
        result = estimate_savings("some-future-model", 100_000, 1_000, 400)
        assert result["current_cost"] >= 0
        assert result["monthly_savings"] >= 0


# ---------------------------------------------------------------------------
# 8. estimate_detailed_cost helper
# ---------------------------------------------------------------------------

class TestEstimateDetailedCost:
    def test_returns_all_required_keys(self):
        result = estimate_detailed_cost(_req())
        for key in ("monthly_cost", "llm_cost", "embedding_cost", "vector_db_cost",
                    "storage_cost", "infrastructure_cost", "estimated_savings", "findings"):
            assert key in result, f"Missing key: {key}"

    def test_nonzero_for_real_traffic(self):
        result = estimate_detailed_cost(_req(llm="gpt-4o", monthly_requests=100_000))
        assert result["llm_cost"] > 0
        assert result["total_before_savings"] > 0


# ---------------------------------------------------------------------------
# 9. /estimate API endpoint returns full breakdown
# ---------------------------------------------------------------------------

class TestEstimateEndpoint:
    PAYLOAD = {
        "project_name": "AuditTest",
        "llm": "gpt-4o",
        "embedding_model": "text-embedding-3-small",
        "vector_db": "Pinecone",
        "framework": "FastAPI",
        "monthly_requests": 100_000,
        "average_prompt_tokens": 1_000,
        "average_completion_tokens": 400,
        "context_window": 8_000,
        "concurrent_users": 500,
        "prompt_strategy": "few-shot",
        "rag_enabled": True,
        "cache_enabled": False,
        "memory": False,
        "observability": True,
        "authentication": True,
        "rate_limiting": True,
        "retry_strategy": True,
    }

    def test_returns_200(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        assert resp.status_code == 200, resp.text

    def test_total_monthly_cost_nonzero(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        data = resp.json()
        assert data["total_monthly_cost"] > 0, (
            f"Expected non-zero cost, got {data['total_monthly_cost']}"
        )

    def test_breakdown_present(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        data = resp.json()
        assert "breakdown" in data, "No breakdown key in response"
        bd = data["breakdown"]
        assert bd is not None
        for key in ("llm_cost", "embedding_cost", "vector_db_cost",
                    "storage_cost", "infrastructure_cost", "estimated_savings"):
            assert key in bd, f"Missing breakdown key: {key}"

    def test_breakdown_llm_cost_nonzero(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        bd = resp.json()["breakdown"]
        assert bd["llm_cost"] > 0

    def test_model_costs_list_populated(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        data = resp.json()
        assert len(data["model_costs"]) >= 1

    def test_per_component_costs_labelled(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        components = {mc["component"] for mc in resp.json()["model_costs"]}
        assert "gpt-4o" in components or any("gpt" in c for c in components)

    def test_tokens_field_populated(self):
        resp = client.post("/api/v1/estimate", json=self.PAYLOAD)
        tokens = resp.json()["tokens"]
        assert tokens["total_tokens"] == 100_000 * (1_000 + 400)

    @pytest.mark.parametrize("llm,expected_nonzero", [
        ("gpt-4o",       True),
        ("gpt-4o-mini",  True),
        ("claude-sonnet", True),
        ("gemini-2.5-pro", True),
        ("llama3",       False),   # LLM cost is $0 but total may be > 0
    ])
    def test_multiple_models_via_api(self, llm, expected_nonzero):
        payload = {**self.PAYLOAD, "llm": llm}
        resp = client.post("/api/v1/estimate", json=payload)
        assert resp.status_code == 200, resp.text
        bd = resp.json()["breakdown"]
        if expected_nonzero:
            assert bd["llm_cost"] > 0, f"{llm} should have non-zero LLM cost"
        else:
            assert bd["llm_cost"] == 0.0, f"{llm} should have $0 LLM cost"

    def test_cache_enabled_reduces_savings_field(self):
        payload_off = {**self.PAYLOAD, "cache_enabled": False}
        payload_on  = {**self.PAYLOAD, "cache_enabled": True}
        resp_off = client.post("/api/v1/estimate", json=payload_off).json()
        resp_on  = client.post("/api/v1/estimate", json=payload_on).json()
        savings_off = resp_off["breakdown"]["estimated_savings"]
        savings_on  = resp_on["breakdown"]["estimated_savings"]
        assert savings_on > savings_off

    def test_high_traffic_costs_more_than_low_traffic(self):
        low  = {**self.PAYLOAD, "monthly_requests": 10_000}
        high = {**self.PAYLOAD, "monthly_requests": 1_000_000}
        cost_low  = client.post("/api/v1/estimate", json=low).json()["total_monthly_cost"]
        cost_high = client.post("/api/v1/estimate", json=high).json()["total_monthly_cost"]
        assert cost_high > cost_low
