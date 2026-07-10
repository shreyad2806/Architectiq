import pytest

from app.schemas import ReviewRequest
from app.services.recommendation_engine import (
    AdvancedRecommendationEngine,
    RecommendationEngine,
    Recommendation,
    _PRIORITY_ORDER,
    _DIFFICULTY_ORDER,
    _impl_time_minutes,
    _semantic_key,
    _deduplicate,
    _sort_recs,
)


def _make_request(**overrides) -> ReviewRequest:
    defaults = dict(
        project_name="TestArch",
        llm="gpt-4o",
        embedding_model="text-embedding-3-small",
        vector_db="Pinecone",
        framework="FastAPI",
        memory=True,
        rag_enabled=True,
        cache_enabled=True,
        prompt_strategy="few-shot",
        monthly_requests=100_000,
        average_prompt_tokens=1_400,
        average_completion_tokens=500,
        context_window=128_000,
        concurrent_users=5_000,
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
    )
    defaults.update(overrides)
    return ReviewRequest(**defaults)


# ---------------------------------------------------------------------------
# RecommendationEngine (legacy) tests
# ---------------------------------------------------------------------------

def test_no_security_recs_for_fully_featured_arch():
    request = _make_request()
    recs = RecommendationEngine().generate(request)
    titles = {r["title"] for r in recs}
    assert "Enforce API Authentication (OAuth 2.0 / JWT)" not in titles
    assert "Add Per-User Rate Limiting" not in titles
    assert "Implement Exponential Backoff Retry Strategy" not in titles
    assert "Enable Semantic Caching" not in titles


def test_bare_arch_generates_many_recs():
    request = _make_request(
        authentication=False,
        rate_limiting=False,
        retry_strategy=False,
        cache_enabled=False,
        memory=False,
        rag_enabled=False,
        observability=False,
        logging=False,
        monitoring=False,
        tracing=False,
        metrics=False,
        health_endpoint=False,
        prompt_injection_protection=False,
        input_validation=False,
    )
    recs = RecommendationEngine().generate(request)
    assert len(recs) >= 8


def test_sorted_by_priority():
    request = _make_request(
        authentication=False,
        rate_limiting=False,
        logging=False,
        metrics=False,
    )
    recs = RecommendationEngine().generate(request)
    priorities = [r["priority"] for r in recs]
    order_values = [_PRIORITY_ORDER[p] for p in priorities]
    assert order_values == sorted(order_values), "Recommendations not sorted by priority"


def test_required_fields_present():
    request = _make_request(authentication=False)
    recs = RecommendationEngine().generate(request)
    assert len(recs) > 0
    for rec in recs:
        assert "priority" in rec
        assert "title" in rec
        assert "description" in rec
        assert "estimated_monthly_saving" in rec
        assert "estimated_latency_improvement" in rec
        assert "estimated_score_improvement" in rec


def test_priority_values_valid():
    request = _make_request(authentication=False, cache_enabled=False, metrics=False)
    recs = RecommendationEngine().generate(request)
    for rec in recs:
        assert rec["priority"] in ("HIGH", "MEDIUM", "LOW")


def test_cache_rec_present_when_disabled():
    request = _make_request(cache_enabled=False)
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert "Enable Semantic Caching" in titles


def test_model_switch_rec_for_expensive_model_high_traffic():
    request = _make_request(llm="gpt-4o", monthly_requests=1_000_000)
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert any("GPT-4o Mini" in t for t in titles)


def test_no_duplicate_titles():
    request = _make_request(
        authentication=False,
        cache_enabled=False,
        retry_strategy=False,
    )
    recs = RecommendationEngine().generate(request)
    titles = [r["title"] for r in recs]
    assert len(titles) == len(set(titles)), "Duplicate recommendation titles found"


# ---------------------------------------------------------------------------
# AdvancedRecommendationEngine tests
# ---------------------------------------------------------------------------

def test_advanced_output_shape():
    request = _make_request(authentication=False, cache_enabled=False)
    result = AdvancedRecommendationEngine().generate(request)
    assert "executive_summary" in result
    assert "total_estimated_monthly_savings" in result
    assert "estimated_latency_improvement" in result
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


def test_advanced_recommendation_rich_fields():
    request = _make_request(authentication=False)
    result = AdvancedRecommendationEngine().generate(request)
    for rec in result["recommendations"]:
        assert "priority" in rec
        assert "category" in rec
        assert "title" in rec
        assert "reason" in rec
        assert "expected_monthly_saving" in rec
        assert "latency_improvement" in rec
        assert "quality_improvement" in rec
        assert "difficulty" in rec
        assert "implementation_time" in rec


def test_advanced_category_values():
    request = _make_request(
        authentication=False, cache_enabled=False, logging=False,
        retry_strategy=False, rag_enabled=False,
    )
    result = AdvancedRecommendationEngine().generate(request)
    valid_categories = {
        "Cost Optimization", "RAG Optimization", "Performance",
        "Reliability", "Security", "Observability",
    }
    for rec in result["recommendations"]:
        assert rec["category"] in valid_categories, f"Unknown category: {rec['category']}"


def test_advanced_sorted_by_priority():
    request = _make_request(
        authentication=False, rate_limiting=False, cache_enabled=False,
        logging=False, metrics=False,
    )
    result = AdvancedRecommendationEngine().generate(request)
    priorities = [r["priority"] for r in result["recommendations"]]
    order_values = [_PRIORITY_ORDER[p] for p in priorities]
    assert order_values == sorted(order_values)


def test_advanced_no_duplicate_titles():
    request = _make_request(
        authentication=False, cache_enabled=False, retry_strategy=False,
        logging=False, monitoring=False,
    )
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert len(titles) == len(set(titles))


def test_advanced_executive_summary_mentions_project():
    request = _make_request(project_name="Acme RAG System", authentication=False)
    result = AdvancedRecommendationEngine().generate(request)
    assert "Acme RAG System" in result["executive_summary"]


def test_advanced_savings_string_format():
    request = _make_request(cache_enabled=False, llm="gpt-4o", monthly_requests=500_000)
    result = AdvancedRecommendationEngine().generate(request)
    assert result["total_estimated_monthly_savings"].startswith("$")


def test_advanced_latency_improvement_string_format():
    request = _make_request(cache_enabled=False)
    result = AdvancedRecommendationEngine().generate(request)
    assert result["estimated_latency_improvement"].endswith("%")


def test_advanced_no_recs_not_needed():
    """For a best-practice architecture, security/reliability recs must not fire."""
    request = _make_request(
        authentication=True, rate_limiting=True, retry_strategy=True,
        prompt_injection_protection=True, input_validation=True,
        logging=True, monitoring=True, tracing=True, metrics=True,
        health_endpoint=True, cache_enabled=True,
        llm="gpt-4o-mini",
        rag_enabled=False,
        vector_db="",
        context_window=4_000,
        monthly_requests=10_000,
    )
    result = AdvancedRecommendationEngine().generate(request)
    titles = {r["title"] for r in result["recommendations"]}
    assert "Enforce API Authentication (OAuth 2.0 / JWT)" not in titles
    assert "Add Per-User Rate Limiting" not in titles
    assert "Enable Semantic Caching" not in titles


def test_advanced_context_window_rec_fires():
    request = _make_request(context_window=16_000)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert "Reduce Context Window Size" in titles


def test_advanced_vdb_migration_rec():
    request = _make_request(vector_db="chroma", rag_enabled=True)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert any("chroma" in t.lower() for t in titles)


def test_advanced_hybrid_search_rec_when_rag():
    request = _make_request(rag_enabled=True)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    assert "Add Hybrid Search (Dense + Sparse Retrieval)" in titles


def test_advanced_model_routing_for_very_high_traffic():
    request = _make_request(llm="gpt-4o", monthly_requests=600_000)
    result = AdvancedRecommendationEngine().generate(request)
    titles = [r["title"] for r in result["recommendations"]]
    # Semantic dedup collapses "Switch from gpt-4o …" and "Implement Intelligent
    # Model Routing" into one rec (same group); assert the concept is present.
    assert any(
        "gpt-4o mini" in t.lower() or "model routing" in t.lower()
        for t in titles
    ), f"No model optimisation recommendation found in: {titles}"


# ---------------------------------------------------------------------------
# _impl_time_minutes unit tests
# ---------------------------------------------------------------------------

def test_impl_time_minutes():
    assert _impl_time_minutes("15 minutes") == 15
    assert _impl_time_minutes("30 min")     == 30
    assert _impl_time_minutes("2 hours")    == 120
    assert _impl_time_minutes("4 hours")    == 240
    assert _impl_time_minutes("1 day")      == 480
    assert _impl_time_minutes("3 days")     == 1440
    assert _impl_time_minutes("1 week")     == 2400
    assert _impl_time_minutes("2 weeks")    == 4800
    assert _impl_time_minutes("varies")     == 9999
    assert _impl_time_minutes("")           == 9999


def test_impl_time_minutes_ordering():
    assert _impl_time_minutes("30 minutes") < _impl_time_minutes("2 hours")
    assert _impl_time_minutes("2 hours")    < _impl_time_minutes("1 day")
    assert _impl_time_minutes("1 day")      < _impl_time_minutes("1 week")
    assert _impl_time_minutes("1 week")     < _impl_time_minutes("varies")


# ---------------------------------------------------------------------------
# Difficulty ordering
# ---------------------------------------------------------------------------

def test_difficulty_order_values():
    assert _DIFFICULTY_ORDER["easy"]   == 0
    assert _DIFFICULTY_ORDER["medium"] == 1
    assert _DIFFICULTY_ORDER["hard"]   == 2


# ---------------------------------------------------------------------------
# _sort_recs comprehensive tests
# ---------------------------------------------------------------------------

def _rec(priority="HIGH", saving=0.0, latency=0.0, difficulty="Medium",
         impl_time="varies", title="T", category="Security") -> Recommendation:
    return Recommendation(
        priority=priority, category=category, title=title, reason="",
        difficulty=difficulty, implementation_time=impl_time,
        estimated_monthly_saving=saving,
        estimated_latency_improvement=latency,
    )


class TestSortRecs:
    def test_high_before_medium_before_low(self):
        recs = [
            _rec(priority="LOW",    title="C"),
            _rec(priority="HIGH",   title="A"),
            _rec(priority="MEDIUM", title="B"),
        ]
        sorted_recs = _sort_recs(recs)
        assert [r.priority for r in sorted_recs] == ["HIGH", "MEDIUM", "LOW"]

    def test_higher_saving_first_within_same_priority(self):
        recs = [
            _rec(priority="HIGH", saving=100.0, title="cheap"),
            _rec(priority="HIGH", saving=900.0, title="expensive"),
        ]
        sorted_recs = _sort_recs(recs)
        assert sorted_recs[0].title == "expensive"
        assert sorted_recs[1].title == "cheap"

    def test_higher_latency_improvement_first(self):
        recs = [
            _rec(priority="HIGH", saving=0.0, latency=20.0,  title="low_lat"),
            _rec(priority="HIGH", saving=0.0, latency=80.0,  title="high_lat"),
        ]
        sorted_recs = _sort_recs(recs)
        assert sorted_recs[0].title == "high_lat"

    def test_easy_before_medium_before_hard(self):
        recs = [
            _rec(priority="MEDIUM", difficulty="Hard",   title="hard"),
            _rec(priority="MEDIUM", difficulty="Easy",   title="easy"),
            _rec(priority="MEDIUM", difficulty="Medium", title="medium"),
        ]
        sorted_recs = _sort_recs(recs)
        difficulties = [r.difficulty for r in sorted_recs]
        assert difficulties == ["Easy", "Medium", "Hard"]

    def test_faster_impl_time_first(self):
        recs = [
            _rec(priority="LOW", impl_time="1 day",      title="slow"),
            _rec(priority="LOW", impl_time="30 minutes", title="fast"),
        ]
        sorted_recs = _sort_recs(recs)
        assert sorted_recs[0].title == "fast"

    def test_priority_trumps_saving(self):
        """A HIGH rec with zero saving must appear before MEDIUM with $10k saving."""
        recs = [
            _rec(priority="MEDIUM", saving=10_000.0, title="rich_medium"),
            _rec(priority="HIGH",   saving=0.0,      title="poor_high"),
        ]
        sorted_recs = _sort_recs(recs)
        assert sorted_recs[0].title == "poor_high"

    def test_composite_sort_cache_before_embedding(self):
        """Cache rec (HIGH, $780) should precede embedding upgrade (MEDIUM, $0)."""
        cache = _rec(priority="HIGH",   saving=780.0, difficulty="Easy",
                     impl_time="2 hours",  title="Enable Semantic Caching")
        embed = _rec(priority="MEDIUM", saving=0.0,   difficulty="Medium",
                     impl_time="1 hour",   title="Upgrade Embedding Model")
        sorted_recs = _sort_recs([embed, cache])
        assert sorted_recs[0].title == "Enable Semantic Caching"


# ---------------------------------------------------------------------------
# Semantic deduplication tests
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_exact_title_dedup(self):
        recs = [
            _rec(title="Enable Semantic Caching", priority="HIGH"),
            _rec(title="Enable Semantic Caching", priority="HIGH"),
        ]
        assert len(_deduplicate(recs)) == 1

    def test_semantic_dedup_cache_group(self):
        """Two recs matching the cache group keep only the first."""
        r1 = _rec(title="Enable Semantic Caching",     priority="HIGH")
        r2 = _rec(title="Deploy Redis as Response Cache", priority="HIGH")
        result = _deduplicate([r1, r2])
        assert len(result) == 1
        assert result[0].title == "Enable Semantic Caching"

    def test_semantic_dedup_model_group(self):
        """Model-switch and model-routing are the same concept."""
        r1 = _rec(title="Switch from gpt-4o to GPT-4o Mini",   priority="HIGH")
        r2 = _rec(title="Implement Intelligent Model Routing",  priority="HIGH")
        result = _deduplicate([r1, r2])
        assert len(result) == 1

    def test_semantic_dedup_retry_group(self):
        r1 = _rec(title="Implement Exponential Backoff Retry Strategy", priority="HIGH")
        r2 = _rec(title="Add Retry with Backoff",                       priority="MEDIUM")
        result = _deduplicate([r1, r2])
        assert len(result) == 1

    def test_different_groups_not_deduped(self):
        r1 = _rec(title="Enable Semantic Caching",   priority="HIGH")
        r2 = _rec(title="Enforce API Authentication", priority="HIGH")
        r3 = _rec(title="Add Hybrid Search",          priority="MEDIUM")
        result = _deduplicate([r1, r2, r3])
        assert len(result) == 3

    def test_no_dedup_needed_passes_through(self):
        recs = [
            _rec(title="Auth",          priority="HIGH"),
            _rec(title="Rate Limiting",  priority="HIGH"),
            _rec(title="Hybrid Search",  priority="MEDIUM"),
        ]
        assert len(_deduplicate(recs)) == 3


# ---------------------------------------------------------------------------
# _semantic_key tests
# ---------------------------------------------------------------------------

def test_semantic_key_cache():
    assert _semantic_key("Enable Semantic Caching") == "semantic cach"

def test_semantic_key_redis():
    assert _semantic_key("Deploy Redis as Response Cache") == "semantic cach"

def test_semantic_key_retry():
    assert _semantic_key("Implement Exponential Backoff Retry Strategy") == "retry"

def test_semantic_key_auth():
    assert _semantic_key("Enforce API Authentication (OAuth 2.0 / JWT)") == "authentication"

def test_semantic_key_hybrid():
    assert _semantic_key("Add Hybrid Search (Dense + Sparse Retrieval)") == "hybrid search"

def test_semantic_key_unknown():
    assert _semantic_key("Some completely novel recommendation") is None


# ---------------------------------------------------------------------------
# impact field tests
# ---------------------------------------------------------------------------

class TestImpactField:
    def test_rich_dict_has_impact(self):
        request = _make_request(authentication=False)
        result = AdvancedRecommendationEngine().generate(request)
        for rec in result["recommendations"]:
            assert "impact" in rec, f"Missing impact on: {rec['title']}"

    def test_impact_is_non_empty_string(self):
        request = _make_request(authentication=False, cache_enabled=False)
        result = AdvancedRecommendationEngine().generate(request)
        for rec in result["recommendations"]:
            assert isinstance(rec["impact"], str)
            assert len(rec["impact"]) > 0

    def test_high_priority_impact_label(self):
        r = _rec(priority="HIGH", saving=0.0, latency=0.0, title="Auth")
        assert r._impact().startswith("High")

    def test_critical_impact_for_high_saving(self):
        r = _rec(priority="HIGH", saving=600.0, title="Cache")
        assert "Critical" in r._impact()

    def test_critical_impact_for_high_latency(self):
        r = _rec(priority="HIGH", latency=85.0, title="Cache")
        assert "Critical" in r._impact()

    def test_medium_impact_with_saving(self):
        r = _rec(priority="MEDIUM", saving=250.0, title="Embed")
        assert "Medium" in r._impact()
        assert "cost" in r._impact()

    def test_low_priority_impact_label(self):
        r = _rec(priority="LOW", title="Health")
        assert "Low" in r._impact()


# ---------------------------------------------------------------------------
# End-to-end ranking tests across architectures
# ---------------------------------------------------------------------------

class TestEndToEndRanking:
    def test_high_value_rec_appears_first(self):
        """Enable Semantic Caching (HIGH, large saving) must be first when cache is off."""
        request = _make_request(
            cache_enabled=False,
            authentication=True, rate_limiting=True, retry_strategy=True,
            logging=True, monitoring=True, tracing=True,
        )
        result = AdvancedRecommendationEngine().generate(request)
        recs = result["recommendations"]
        assert recs[0]["priority"] == "HIGH"
        assert "cach" in recs[0]["title"].lower() or recs[0]["expected_monthly_saving"] != "$0"

    def test_priority_order_maintained_full_arch(self):
        """Across all recommendations, no MEDIUM appears before any HIGH."""
        request = _make_request(
            authentication=False, rate_limiting=False, cache_enabled=False,
            logging=False, monitoring=False, retry_strategy=False,
        )
        result = AdvancedRecommendationEngine().generate(request)
        priorities = [r["priority"] for r in result["recommendations"]]
        order_vals = [_PRIORITY_ORDER[p] for p in priorities]
        assert order_vals == sorted(order_vals), f"Priority order violated: {priorities}"

    def test_different_architectures_produce_different_ordering(self):
        """Two different architectures must not produce identical rec lists."""
        req_a = _make_request(cache_enabled=False, authentication=False, llm="gpt-4o")
        req_b = _make_request(cache_enabled=True,  authentication=True,  llm="gpt-4o-mini")
        recs_a = AdvancedRecommendationEngine().generate(req_a)["recommendations"]
        recs_b = AdvancedRecommendationEngine().generate(req_b)["recommendations"]
        titles_a = [r["title"] for r in recs_a]
        titles_b = [r["title"] for r in recs_b]
        assert titles_a != titles_b

    def test_no_duplicates_in_full_output(self):
        request = _make_request(
            authentication=False, cache_enabled=False, retry_strategy=False,
            logging=False, monitoring=False, rag_enabled=True,
            vector_db="chroma", context_window=32_000,
        )
        result = AdvancedRecommendationEngine().generate(request)
        titles = [r["title"] for r in result["recommendations"]]
        assert len(titles) == len(set(titles)), f"Duplicate titles: {titles}"

    def test_frontend_must_not_sort_data_is_presorted(self):
        """Verify the backend output is already sorted — frontend should render as-is."""
        request = _make_request(
            authentication=False, rate_limiting=False, cache_enabled=False,
            retry_strategy=False, logging=False,
        )
        result = AdvancedRecommendationEngine().generate(request)
        recs = result["recommendations"]
        order_vals = [_PRIORITY_ORDER[r["priority"]] for r in recs]
        assert order_vals == sorted(order_vals), "Output is not pre-sorted by priority"
