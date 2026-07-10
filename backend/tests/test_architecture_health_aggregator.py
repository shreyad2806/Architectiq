"""Tests for ArchitectureHealthAggregator.

Verifies that:
  - Good architectures produce health scores > 80.
  - Poor architectures produce significantly lower scores.
  - Multiple distinct payloads generate visibly different scores.
  - All returned values are integers clamped to [0, 100].
  - Insight captions are non-empty strings.
"""

import pytest

from app.services.architecture_health_aggregator import ArchitectureHealthAggregator
from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(**kwargs) -> ReviewRequest:
    """Build a minimal valid ReviewRequest with overridable defaults."""
    defaults = {
        "project_name":              "TestArch",
        "llm":                       "gpt-4o",
        "embedding_model":           "text-embedding-3-small",
        "vector_db":                 "pinecone",
        "framework":                 "fastapi",
        "monthly_requests":          100_000,
        "average_prompt_tokens":     1_000,
        "average_completion_tokens": 500,
        "context_window":            8_000,
        "concurrent_users":          1_000,
        "prompt_strategy":           "few-shot",
    }
    defaults.update(kwargs)
    return ReviewRequest(**defaults)


def _cost_result(cost: float = 500.0, savings: float = 100.0) -> dict:
    return {
        "estimated_monthly_cost":    cost,
        "potential_monthly_savings": savings,
        "estimated_monthly_tokens":  50_000_000,
        "findings": [],
    }


def _latency_result(latency_ms: float = 450.0) -> dict:
    return {
        "estimated_latency_ms": latency_ms,
        "latency_rating": "Moderate",
        "findings": [],
    }


def _reliability_result(score: int = 90) -> dict:
    return {
        "reliability_score":   score,
        "risk_level":          "Low",
        "findings":            [],
        "structured_findings": [],
    }


def _scalability_result(score: int = 80) -> dict:
    return {
        "scalability_score": score,
        "expected_capacity": "Mid-scale (1k–10k concurrent users)",
        "recommendations":   [],
        "findings":          [],
    }


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def aggregator() -> ArchitectureHealthAggregator:
    return ArchitectureHealthAggregator()


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------

class TestReturnShape:
    def test_returns_all_four_score_keys(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(), _latency_result(),
            _reliability_result(), _scalability_result(),
        )
        for key in ("cost_efficiency", "latency", "reliability", "scalability"):
            assert key in result, f"Missing key: {key}"

    def test_returns_all_four_insight_keys(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(), _latency_result(),
            _reliability_result(), _scalability_result(),
        )
        for key in ("cost_efficiency_insight", "latency_insight",
                    "reliability_insight", "scalability_insight"):
            assert key in result, f"Missing key: {key}"

    def test_scores_are_integers(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(), _latency_result(),
            _reliability_result(), _scalability_result(),
        )
        for key in ("cost_efficiency", "latency", "reliability", "scalability"):
            assert isinstance(result[key], int), f"{key} must be int"

    def test_scores_clamped_0_100(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(), _latency_result(),
            _reliability_result(), _scalability_result(),
        )
        for key in ("cost_efficiency", "latency", "reliability", "scalability"):
            assert 0 <= result[key] <= 100, f"{key}={result[key]} out of [0,100]"

    def test_insights_are_non_empty_strings(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(), _latency_result(),
            _reliability_result(), _scalability_result(),
        )
        for key in ("cost_efficiency_insight", "latency_insight",
                    "reliability_insight", "scalability_insight"):
            assert isinstance(result[key], str) and len(result[key]) > 0


# ---------------------------------------------------------------------------
# Good architecture — scores should be high (> 80)
# ---------------------------------------------------------------------------

class TestGoodArchitecture:
    """A well-configured architecture should produce health scores above 80."""

    @pytest.fixture
    def good_req(self):
        return _req(
            cache_enabled=True,
            retry_strategy=True,
            authentication=True,
            rate_limiting=True,
            monitoring=True,
            logging=True,
            tracing=True,
            metrics=True,
            health_endpoint=True,
            observability=True,
            rag_enabled=False,
            embedding_model="text-embedding-3-small",
            framework="fastapi",
            vector_db="pinecone",
            concurrent_users=5_000,
            monthly_requests=500_000,
        )

    def test_cost_efficiency_high(self, aggregator, good_req):
        result = aggregator.aggregate(
            good_req,
            _cost_result(cost=800.0, savings=200.0),
            _latency_result(450.0),
            _reliability_result(100),
            _scalability_result(85),
        )
        assert result["cost_efficiency"] > 80, result["cost_efficiency"]

    def test_latency_high(self, aggregator, good_req):
        result = aggregator.aggregate(
            good_req,
            _cost_result(),
            _latency_result(300.0),
            _reliability_result(100),
            _scalability_result(85),
        )
        assert result["latency"] > 80, result["latency"]

    def test_reliability_high(self, aggregator, good_req):
        result = aggregator.aggregate(
            good_req,
            _cost_result(),
            _latency_result(),
            _reliability_result(90),
            _scalability_result(85),
        )
        assert result["reliability"] > 80, result["reliability"]

    def test_scalability_high(self, aggregator, good_req):
        result = aggregator.aggregate(
            good_req,
            _cost_result(),
            _latency_result(),
            _reliability_result(90),
            _scalability_result(90),
        )
        assert result["scalability"] > 80, result["scalability"]


# ---------------------------------------------------------------------------
# Poor architecture — scores should be significantly lower
# ---------------------------------------------------------------------------

class TestPoorArchitecture:
    """A poorly-configured architecture should produce health scores below 60."""

    @pytest.fixture
    def poor_req(self):
        return _req(
            cache_enabled=False,
            retry_strategy=False,
            authentication=False,
            rate_limiting=False,
            monitoring=False,
            logging=False,
            tracing=False,
            metrics=False,
            health_endpoint=False,
            observability=False,
            rag_enabled=True,
            framework="rails",
            vector_db="sqlite-vss",
            concurrent_users=500,
            monthly_requests=50_000,
        )

    def test_reliability_low(self, aggregator, poor_req):
        result = aggregator.aggregate(
            poor_req,
            _cost_result(cost=5_000.0, savings=0.0),
            _latency_result(2_500.0),
            _reliability_result(0),
            _scalability_result(15),
        )
        assert result["reliability"] < 60, result["reliability"]

    def test_latency_low(self, aggregator, poor_req):
        result = aggregator.aggregate(
            poor_req,
            _cost_result(),
            _latency_result(2_500.0),
            _reliability_result(0),
            _scalability_result(15),
        )
        assert result["latency"] < 60, result["latency"]

    def test_scalability_low(self, aggregator, poor_req):
        result = aggregator.aggregate(
            poor_req,
            _cost_result(),
            _latency_result(),
            _reliability_result(0),
            _scalability_result(15),
        )
        assert result["scalability"] < 60, result["scalability"]

    def test_cost_efficiency_low_for_expensive_setup(self, aggregator, poor_req):
        result = aggregator.aggregate(
            poor_req,
            _cost_result(cost=30_000.0, savings=0.0),
            _latency_result(),
            _reliability_result(0),
            _scalability_result(15),
        )
        assert result["cost_efficiency"] < 60, result["cost_efficiency"]


# ---------------------------------------------------------------------------
# Distinct payloads produce visibly different scores
# ---------------------------------------------------------------------------

class TestDistinctPayloads:
    """Different architecture configurations must produce meaningfully different scores."""

    def test_cache_on_vs_off_cost_efficiency(self, aggregator):
        req_cached   = _req(cache_enabled=True)
        req_nocache  = _req(cache_enabled=False)

        r_cached  = aggregator.aggregate(req_cached,  _cost_result(), _latency_result(), _reliability_result(), _scalability_result())
        r_nocache = aggregator.aggregate(req_nocache, _cost_result(), _latency_result(), _reliability_result(), _scalability_result())

        assert r_cached["cost_efficiency"] > r_nocache["cost_efficiency"]

    def test_cache_on_vs_off_latency(self, aggregator):
        req_cached  = _req(cache_enabled=True)
        req_nocache = _req(cache_enabled=False)

        r_cached  = aggregator.aggregate(req_cached,  _cost_result(), _latency_result(), _reliability_result(), _scalability_result())
        r_nocache = aggregator.aggregate(req_nocache, _cost_result(), _latency_result(), _reliability_result(), _scalability_result())

        assert r_cached["latency"] > r_nocache["latency"]

    def test_low_vs_high_latency_ms(self, aggregator):
        req = _req()
        r_fast = aggregator.aggregate(req, _cost_result(), _latency_result(200.0),   _reliability_result(), _scalability_result())
        r_slow = aggregator.aggregate(req, _cost_result(), _latency_result(2_800.0), _reliability_result(), _scalability_result())

        assert r_fast["latency"] > r_slow["latency"]
        assert r_fast["latency"] - r_slow["latency"] >= 20

    def test_full_reliability_vs_bare(self, aggregator):
        req_full = _req(retry_strategy=True, authentication=True, rate_limiting=True,
                        monitoring=True, logging=True, tracing=True, health_endpoint=True)
        req_bare = _req(retry_strategy=False, authentication=False, rate_limiting=False,
                        monitoring=False, logging=False, tracing=False, health_endpoint=False)

        r_full = aggregator.aggregate(req_full, _cost_result(), _latency_result(), _reliability_result(100), _scalability_result())
        r_bare = aggregator.aggregate(req_bare, _cost_result(), _latency_result(), _reliability_result(15),  _scalability_result())

        assert r_full["reliability"] > r_bare["reliability"]
        assert r_full["reliability"] - r_bare["reliability"] >= 30

    def test_high_cost_vs_low_cost(self, aggregator):
        req = _req()
        r_cheap     = aggregator.aggregate(req, _cost_result(cost=200.0,    savings=50.0),  _latency_result(), _reliability_result(), _scalability_result())
        r_expensive = aggregator.aggregate(req, _cost_result(cost=40_000.0, savings=100.0), _latency_result(), _reliability_result(), _scalability_result())

        assert r_cheap["cost_efficiency"] > r_expensive["cost_efficiency"]
        assert r_cheap["cost_efficiency"] - r_expensive["cost_efficiency"] >= 20

    def test_fastapi_vs_rails_scalability(self, aggregator):
        req_fast  = _req(framework="fastapi",  monitoring=True, metrics=True)
        req_rails = _req(framework="rails",    monitoring=False, metrics=False)

        r_fast  = aggregator.aggregate(req_fast,  _cost_result(), _latency_result(), _reliability_result(), _scalability_result(80))
        r_rails = aggregator.aggregate(req_rails, _cost_result(), _latency_result(), _reliability_result(), _scalability_result(30))

        assert r_fast["scalability"] > r_rails["scalability"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_cost(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(cost=0.0, savings=0.0),
            _latency_result(), _reliability_result(), _scalability_result(),
        )
        assert 0 <= result["cost_efficiency"] <= 100

    def test_very_high_cost(self, aggregator):
        # Base cost component clamps to 0; a cheap embedding model still adds
        # up to +5 bonus, so the floor is 0–5, not strictly 0.
        result = aggregator.aggregate(
            _req(), _cost_result(cost=999_999.0, savings=0.0),
            _latency_result(), _reliability_result(), _scalability_result(),
        )
        assert result["cost_efficiency"] <= 5

    def test_zero_latency_ms(self, aggregator):
        result = aggregator.aggregate(
            _req(), _cost_result(), _latency_result(0.0),
            _reliability_result(), _scalability_result(),
        )
        assert 0 <= result["latency"] <= 100

    def test_reliability_base_zero_with_no_bonuses(self, aggregator):
        result = aggregator.aggregate(
            _req(monitoring=False, logging=False, tracing=False, health_endpoint=False),
            _cost_result(), _latency_result(), _reliability_result(0), _scalability_result(),
        )
        assert result["reliability"] == 0

    def test_full_bonuses_capped_at_100(self, aggregator):
        req = _req(
            cache_enabled=True, retry_strategy=True, authentication=True,
            rate_limiting=True, monitoring=True, logging=True, tracing=True,
            metrics=True, health_endpoint=True, observability=True,
        )
        result = aggregator.aggregate(
            req,
            _cost_result(cost=0.0, savings=0.0),
            _latency_result(0.0),
            _reliability_result(100),
            _scalability_result(100),
        )
        for key in ("cost_efficiency", "latency", "reliability", "scalability"):
            assert result[key] <= 100, f"{key} exceeded 100: {result[key]}"
