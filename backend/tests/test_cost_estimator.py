"""Comprehensive tests for DetailedCostEstimator and CostAnalyzer.

Covers:
  - All 6 line items are present and non-negative
  - Larger traffic produces proportionally higher costs
  - More expensive models produce higher LLM cost
  - Cheaper models (gpt-4o-mini, llama3) produce lower LLM cost
  - RAG disabled zeroes out embedding and vector DB costs
  - Cache enabled reduces estimated_savings (savings_from_cache > 0)
  - Higher concurrency increases infrastructure cost
  - Larger context window increases storage cost
  - Savings never exceed gross total
  - monthly_cost = total_before_savings - estimated_savings (floored at 0)
  - Different payloads produce different totals
  - CostAnalyzer backward-compat keys are present
  - breakdown dict has all required keys
"""

import pytest

from app.schemas import ReviewRequest
from app.services.cost_analyzer import (
    CostAnalyzer,
    CostBreakdown,
    DetailedCostEstimator,
    _CACHE_HIT_RATE,
    _get_model_pricing,
    _get_vdb_base,
    PRICING_TABLE,
)


# ---------------------------------------------------------------------------
# Request factory
# ---------------------------------------------------------------------------

def _req(**kwargs) -> ReviewRequest:
    defaults = dict(
        project_name="TestProject",
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
# Five representative payloads (the request asks for ≥5)
# ---------------------------------------------------------------------------

PAYLOADS = {
    "low_traffic_mini": _req(
        llm="gpt-4o-mini", monthly_requests=10_000,
        average_prompt_tokens=500, average_completion_tokens=150,
        concurrent_users=50, rag_enabled=False,
    ),
    "medium_traffic_4o": _req(
        llm="gpt-4o", monthly_requests=100_000,
        average_prompt_tokens=1_000, average_completion_tokens=400,
        concurrent_users=500, rag_enabled=True,
    ),
    "high_traffic_4o": _req(
        llm="gpt-4o", monthly_requests=1_000_000,
        average_prompt_tokens=1_200, average_completion_tokens=500,
        concurrent_users=5_000, rag_enabled=True,
    ),
    "claude_large_context": _req(
        llm="claude-sonnet", monthly_requests=50_000,
        average_prompt_tokens=3_000, average_completion_tokens=800,
        context_window=100_000, concurrent_users=200, rag_enabled=True,
    ),
    "llama3_self_hosted": _req(
        llm="llama3", monthly_requests=500_000,
        average_prompt_tokens=800, average_completion_tokens=300,
        concurrent_users=1_000, rag_enabled=False, cache_enabled=True,
    ),
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _est(payload_key: str) -> CostBreakdown:
    return DetailedCostEstimator().estimate(PAYLOADS[payload_key])


# ---------------------------------------------------------------------------
# CostBreakdown structure
# ---------------------------------------------------------------------------

class TestCostBreakdownStructure:
    def test_all_line_items_non_negative(self):
        for key in PAYLOADS:
            bd = _est(key)
            assert bd.llm_cost            >= 0, key
            assert bd.embedding_cost      >= 0, key
            assert bd.vector_db_cost      >= 0, key
            assert bd.storage_cost        >= 0, key
            assert bd.infrastructure_cost >= 0, key
            assert bd.monthly_cost        >= 0, key

    def test_total_before_savings_equals_sum_of_parts(self):
        for key in PAYLOADS:
            bd = _est(key)
            expected = round(
                bd.llm_cost + bd.embedding_cost + bd.vector_db_cost
                + bd.storage_cost + bd.infrastructure_cost, 2
            )
            assert abs(bd.total_before_savings - expected) < 0.02, (
                f"{key}: total_before_savings={bd.total_before_savings}, sum={expected}"
            )

    def test_monthly_cost_equals_gross_minus_savings(self):
        for key in PAYLOADS:
            bd = _est(key)
            expected = max(round(bd.total_before_savings - bd.estimated_savings, 2), 0.0)
            assert abs(bd.monthly_cost - expected) < 0.02, key

    def test_savings_never_exceed_gross(self):
        for key in PAYLOADS:
            bd = _est(key)
            assert bd.estimated_savings <= bd.total_before_savings + 0.01, key

    def test_estimated_savings_equals_cache_plus_model_switch(self):
        for key in PAYLOADS:
            bd = _est(key)
            expected = round(bd.savings_from_cache + bd.savings_from_model_switch, 2)
            assert abs(bd.estimated_savings - expected) < 0.02, key

    def test_to_dict_has_all_required_keys(self):
        required = {
            "monthly_cost", "llm_cost", "embedding_cost", "vector_db_cost",
            "storage_cost", "infrastructure_cost", "total_before_savings",
            "estimated_savings", "savings_from_cache", "savings_from_model_switch",
            "estimated_monthly_tokens",
        }
        bd = _est("medium_traffic_4o")
        assert required.issubset(bd.to_dict().keys())


# ---------------------------------------------------------------------------
# Payload 1 — low_traffic_mini: verify cheap model + low traffic = low cost
# ---------------------------------------------------------------------------

class TestLowTrafficMini:
    def test_llm_cost_is_low(self):
        bd = _est("low_traffic_mini")
        # 10k req * 500 prompt * $0.15/1M = $0.75 input; 10k * 150 * $0.60/1M = $0.90 output = $1.65
        assert bd.llm_cost == pytest.approx(1.65, abs=0.01)

    def test_no_rag_means_zero_embedding_and_vdb(self):
        bd = _est("low_traffic_mini")
        assert bd.embedding_cost == 0.0
        assert bd.vector_db_cost == 0.0

    def test_no_model_switch_savings_for_mini(self):
        """gpt-4o-mini is already the baseline — no model-switch saving."""
        bd = _est("low_traffic_mini")
        assert bd.savings_from_model_switch == 0.0


# ---------------------------------------------------------------------------
# Payload 2 — medium_traffic_4o
# ---------------------------------------------------------------------------

class TestMediumTraffic4o:
    def test_llm_cost_matches_formula(self):
        bd = _est("medium_traffic_4o")
        # 100k * 1000 prompt tokens = 100M input; 100k * 400 output = 40M output
        expected = (100 * 2.50) + (40 * 10.00)   # $250 + $400 = $650
        assert bd.llm_cost == pytest.approx(expected, abs=0.01)

    def test_rag_adds_embedding_cost(self):
        bd = _est("medium_traffic_4o")
        # text-embedding-3-small $0.02/1M * 100M input tokens = $2
        assert bd.embedding_cost == pytest.approx(2.0, abs=0.05)

    def test_pinecone_base_cost_included(self):
        bd = _est("medium_traffic_4o")
        # pinecone base = $70; 100k req > 50k threshold → tier = 50*0.10 = $5
        assert bd.vector_db_cost == pytest.approx(75.0, abs=0.5)

    def test_model_switch_savings_positive(self):
        bd = _est("medium_traffic_4o")
        assert bd.savings_from_model_switch > 0

    def test_no_cache_savings_when_disabled(self):
        bd = _est("medium_traffic_4o")
        assert bd.savings_from_cache == 0.0


# ---------------------------------------------------------------------------
# Payload 3 — high_traffic_4o: scales logically from medium
# ---------------------------------------------------------------------------

class TestHighTraffic4o:
    def test_llm_cost_10x_medium(self):
        """1M requests is 10× medium (100k). LLM cost should scale linearly."""
        bd_med  = _est("medium_traffic_4o")
        bd_high = _est("high_traffic_4o")
        # prompt tokens differ slightly (1200 vs 1000) so allow ±15%
        ratio = bd_high.llm_cost / bd_med.llm_cost
        assert 8.0 < ratio < 15.0, f"Unexpected ratio: {ratio}"

    def test_total_cost_higher_than_medium(self):
        assert _est("high_traffic_4o").total_before_savings > _est("medium_traffic_4o").total_before_savings

    def test_higher_concurrency_increases_infra_cost(self):
        bd_med  = _est("medium_traffic_4o")   # concurrent_users=500
        bd_high = _est("high_traffic_4o")     # concurrent_users=5000
        assert bd_high.infrastructure_cost > bd_med.infrastructure_cost


# ---------------------------------------------------------------------------
# Payload 4 — claude_large_context: expensive model + large context
# ---------------------------------------------------------------------------

class TestClaudeLargeContext:
    def test_claude_llm_cost_higher_than_gpt4o_same_traffic(self):
        """claude-sonnet is more expensive per token than gpt-4o."""
        req_claude = _req(llm="claude-sonnet", monthly_requests=50_000,
                          average_prompt_tokens=1_000, average_completion_tokens=400)
        req_4o     = _req(llm="gpt-4o",        monthly_requests=50_000,
                          average_prompt_tokens=1_000, average_completion_tokens=400)
        bd_claude = DetailedCostEstimator().estimate(req_claude)
        bd_4o     = DetailedCostEstimator().estimate(req_4o)
        assert bd_claude.llm_cost > bd_4o.llm_cost

    def test_larger_context_increases_storage_cost(self):
        """Use extreme context sizes so the difference exceeds rounding precision."""
        bd_small = DetailedCostEstimator().estimate(_req(context_window=1_000))
        bd_large = DetailedCostEstimator().estimate(_req(context_window=1_000_000))
        assert bd_large.storage_cost > bd_small.storage_cost


# ---------------------------------------------------------------------------
# Payload 5 — llama3_self_hosted: free LLM, cache enabled
# ---------------------------------------------------------------------------

class TestLlama3SelfHosted:
    def test_llm_cost_is_zero(self):
        assert _est("llama3_self_hosted").llm_cost == 0.0

    def test_no_rag_means_no_embedding_or_vdb(self):
        bd = _est("llama3_self_hosted")
        assert bd.embedding_cost == 0.0
        assert bd.vector_db_cost == 0.0

    def test_cache_has_no_effect_when_llm_free(self):
        """savings_from_cache = llm_cost * hit_rate → 0 when llm_cost = 0."""
        bd = _est("llama3_self_hosted")
        assert bd.savings_from_cache == 0.0

    def test_no_model_switch_saving_for_llama3(self):
        """llama3 is already cheaper than gpt-4o-mini baseline."""
        bd = _est("llama3_self_hosted")
        assert bd.savings_from_model_switch == 0.0


# ---------------------------------------------------------------------------
# Cache reduces costs
# ---------------------------------------------------------------------------

class TestCacheReducesCosts:
    def test_cache_enabled_adds_savings(self):
        req_no_cache  = _req(llm="gpt-4o", cache_enabled=False)
        req_with_cache = _req(llm="gpt-4o", cache_enabled=True)
        bd_no    = DetailedCostEstimator().estimate(req_no_cache)
        bd_cache = DetailedCostEstimator().estimate(req_with_cache)
        assert bd_cache.savings_from_cache > 0

    def test_cache_savings_equals_hit_rate_times_llm_cost(self):
        req = _req(llm="gpt-4o", cache_enabled=True)
        bd  = DetailedCostEstimator().estimate(req)
        expected = round(bd.llm_cost * _CACHE_HIT_RATE, 2)
        assert abs(bd.savings_from_cache - expected) < 0.02

    def test_monthly_cost_lower_with_cache(self):
        req_no    = _req(llm="gpt-4o", cache_enabled=False)
        req_cache = _req(llm="gpt-4o", cache_enabled=True)
        bd_no    = DetailedCostEstimator().estimate(req_no)
        bd_cache = DetailedCostEstimator().estimate(req_cache)
        assert bd_cache.monthly_cost < bd_no.monthly_cost


# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------

class TestModelComparison:
    def test_gpt4o_more_expensive_than_mini(self):
        bd_4o   = DetailedCostEstimator().estimate(_req(llm="gpt-4o"))
        bd_mini = DetailedCostEstimator().estimate(_req(llm="gpt-4o-mini"))
        assert bd_4o.llm_cost > bd_mini.llm_cost

    def test_claude_more_expensive_than_gpt4o(self):
        bd_claude = DetailedCostEstimator().estimate(_req(llm="claude-sonnet"))
        bd_4o     = DetailedCostEstimator().estimate(_req(llm="gpt-4o"))
        assert bd_claude.llm_cost > bd_4o.llm_cost

    def test_different_models_produce_different_totals(self):
        totals = {
            k: DetailedCostEstimator().estimate(_req(llm=k)).total_before_savings
            for k in ("gpt-4o", "gpt-4o-mini", "claude-sonnet")
        }
        assert len(set(totals.values())) == 3

    def test_traffic_scaling_is_linear_for_llm(self):
        bd_1x = DetailedCostEstimator().estimate(_req(monthly_requests=100_000))
        bd_5x = DetailedCostEstimator().estimate(_req(monthly_requests=500_000))
        ratio = bd_5x.llm_cost / bd_1x.llm_cost
        assert abs(ratio - 5.0) < 0.01, f"Expected 5x ratio, got {ratio}"


# ---------------------------------------------------------------------------
# CostAnalyzer backward-compat
# ---------------------------------------------------------------------------

class TestCostAnalyzerBackwardCompat:
    def test_required_keys_present(self):
        result = CostAnalyzer().analyze(_req())
        for key in ("estimated_monthly_tokens", "estimated_monthly_cost",
                    "potential_monthly_savings", "findings", "breakdown"):
            assert key in result, f"Missing key: {key}"

    def test_breakdown_has_all_line_item_keys(self):
        bd = CostAnalyzer().analyze(_req())["breakdown"]
        for key in ("llm_cost", "embedding_cost", "vector_db_cost",
                    "storage_cost", "infrastructure_cost",
                    "total_before_savings", "estimated_savings",
                    "savings_from_cache", "savings_from_model_switch",
                    "estimated_monthly_tokens"):
            assert key in bd, f"Missing breakdown key: {key}"

    def test_findings_is_list(self):
        result = CostAnalyzer().analyze(_req())
        assert isinstance(result["findings"], list)

    def test_potential_savings_non_negative(self):
        for key in PAYLOADS:
            result = CostAnalyzer().analyze(PAYLOADS[key])
            assert result["potential_monthly_savings"] >= 0, key

    def test_gross_total_used_as_estimated_monthly_cost(self):
        """estimated_monthly_cost should equal total_before_savings (gross)."""
        result = CostAnalyzer().analyze(_req(llm="gpt-4o", cache_enabled=False))
        bd = result["breakdown"]
        assert result["estimated_monthly_cost"] == bd["total_before_savings"]

    def test_high_savings_finding_fires_for_expensive_model(self):
        result = CostAnalyzer().analyze(_req(
            llm="gpt-4o", monthly_requests=1_000_000,
            average_prompt_tokens=1_000, average_completion_tokens=500,
        ))
        titles = [f["title"] for f in result["findings"]]
        assert any("savings" in t.lower() or "expensive" in t.lower() for t in titles)

    def test_cache_finding_fires_when_llm_cost_high_and_cache_off(self):
        result = CostAnalyzer().analyze(_req(
            llm="gpt-4o", monthly_requests=500_000, cache_enabled=False,
        ))
        titles = [f["title"] for f in result["findings"]]
        assert any("cach" in t.lower() for t in titles)

    def test_no_cache_finding_when_cache_enabled(self):
        result = CostAnalyzer().analyze(_req(llm="gpt-4o", cache_enabled=True))
        titles = [f["title"] for f in result["findings"]]
        assert not any("Semantic Caching Not Enabled" in t for t in titles)


# ---------------------------------------------------------------------------
# Five payloads — verify cost scales logically
# ---------------------------------------------------------------------------

class TestFivePayloadScaling:
    def test_all_five_payloads_produce_valid_results(self):
        for key, req in PAYLOADS.items():
            result = CostAnalyzer().analyze(req)
            assert result["estimated_monthly_cost"] >= 0, key
            assert isinstance(result["breakdown"], dict), key

    def test_high_traffic_more_expensive_than_low_traffic(self):
        low  = CostAnalyzer().analyze(PAYLOADS["low_traffic_mini"])["estimated_monthly_cost"]
        high = CostAnalyzer().analyze(PAYLOADS["high_traffic_4o"])["estimated_monthly_cost"]
        assert high > low

    def test_all_five_totals_are_distinct(self):
        totals = [
            CostAnalyzer().analyze(req)["estimated_monthly_cost"]
            for req in PAYLOADS.values()
        ]
        assert len(set(totals)) == len(totals), f"Non-unique totals: {totals}"

    def test_expensive_model_payload_most_costly_llm(self):
        """claude-sonnet at 50k requests should have higher LLM cost than gpt-4o-mini at 10k."""
        llm_costs = {
            k: CostAnalyzer().analyze(PAYLOADS[k])["breakdown"]["llm_cost"]
            for k in PAYLOADS
        }
        assert llm_costs["claude_large_context"] > llm_costs["low_traffic_mini"]

    def test_recommendations_reduce_estimated_cost(self):
        """Enabling cache (a top recommendation) must lower monthly_cost."""
        req_before = _req(llm="gpt-4o", monthly_requests=200_000, cache_enabled=False)
        req_after  = _req(llm="gpt-4o", monthly_requests=200_000, cache_enabled=True)
        cost_before = CostAnalyzer().analyze(req_before)["breakdown"]["monthly_cost"]
        cost_after  = CostAnalyzer().analyze(req_after)["breakdown"]["monthly_cost"]
        assert cost_after < cost_before, (
            f"Cache should reduce cost: before={cost_before}, after={cost_after}"
        )
