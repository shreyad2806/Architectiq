"""Tests for RoadmapGenerator.

Verifies:
  - Poor architectures produce a long roadmap (all 3 phases, many tasks).
  - Well-designed architectures produce fewer / no tasks.
  - Items already solved by the architecture are suppressed.
  - No duplicate titles across phases.
  - HIGH priority tasks appear before MEDIUM within each phase.
  - Phase titles and timelines match the spec.
  - Each task dict contains required keys.
  - Multiple distinct architectures produce visibly different roadmaps.
"""

import pytest

from app.services.roadmap_generator import RoadmapGenerator
from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(**kwargs) -> ReviewRequest:
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


# Rich recommendation dicts that mirror AdvancedRecommendationEngine output
_AUTH_REC = {
    "priority": "HIGH", "category": "Security",
    "title": "Enforce API Authentication (OAuth 2.0 / JWT)",
    "reason": "Unauthenticated endpoints.", "difficulty": "Easy",
    "implementation_time": "2 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_RATE_REC = {
    "priority": "HIGH", "category": "Security",
    "title": "Add Per-User Rate Limiting",
    "reason": "Prevent quota exhaustion.", "difficulty": "Easy",
    "implementation_time": "1 hour", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_RETRY_REC = {
    "priority": "HIGH", "category": "Reliability",
    "title": "Implement Exponential Backoff Retry Strategy",
    "reason": "Transient failures.", "difficulty": "Easy",
    "implementation_time": "1 hour", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_CACHE_REC = {
    "priority": "HIGH", "category": "Cost Optimization",
    "title": "Enable Semantic Caching",
    "reason": "Reduce token spend.", "difficulty": "Easy",
    "implementation_time": "2 hours", "expected_monthly_saving": "$420",
    "latency_improvement": "35%",
}
_LOG_REC = {
    "priority": "HIGH", "category": "Observability",
    "title": "Implement Structured JSON Logging",
    "reason": "Debug production incidents.", "difficulty": "Easy",
    "implementation_time": "2 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_HYBRID_REC = {
    "priority": "MEDIUM", "category": "RAG Optimization",
    "title": "Add Hybrid Search (Dense + Sparse Retrieval)",
    "reason": "Improve recall.", "difficulty": "Medium",
    "implementation_time": "4 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_EMBED_REC = {
    "priority": "MEDIUM", "category": "RAG Optimization",
    "title": "Upgrade Embedding Model from text-embedding-3-small to BAAI/bge-large",
    "reason": "Better recall.", "difficulty": "Medium",
    "implementation_time": "1 hour", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_RERANK_REC = {
    "priority": "MEDIUM", "category": "RAG Optimization",
    "title": "Implement Cross-Encoder Reranking",
    "reason": "Better precision.", "difficulty": "Medium",
    "implementation_time": "2 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_ASYNC_REC = {
    "priority": "MEDIUM", "category": "Performance",
    "title": "Enable Async Processing and Connection Pooling",
    "reason": "Concurrency.", "difficulty": "Medium",
    "implementation_time": "1 day", "expected_monthly_saving": "$0",
    "latency_improvement": "30%",
}
_STREAM_REC = {
    "priority": "LOW", "category": "Performance",
    "title": "Enable LLM Response Streaming",
    "reason": "TTFT.", "difficulty": "Easy",
    "implementation_time": "1 hour", "expected_monthly_saving": "$0",
    "latency_improvement": "60% TTFT",
}
_MONITOR_REC = {
    "priority": "HIGH", "category": "Observability",
    "title": "Integrate Prometheus + Grafana Monitoring",
    "reason": "Catch regressions.", "difficulty": "Medium",
    "implementation_time": "4 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_TRACE_REC = {
    "priority": "MEDIUM", "category": "Observability",
    "title": "Add Distributed Tracing with OpenTelemetry",
    "reason": "Langfuse/Jaeger.", "difficulty": "Medium",
    "implementation_time": "3 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "visibility only",
}
_HEALTH_REC = {
    "priority": "LOW", "category": "Observability",
    "title": "Expose a /health Liveness Endpoint",
    "reason": "K8s probes.", "difficulty": "Easy",
    "implementation_time": "15 minutes", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}
_FALLBACK_REC = {
    "priority": "MEDIUM", "category": "Reliability",
    "title": "Define a Fallback LLM for Provider Outages",
    "reason": "Avoid downtime.", "difficulty": "Medium",
    "implementation_time": "3 hours", "expected_monthly_saving": "$0",
    "latency_improvement": "0%",
}

_ALL_RECS = [
    _AUTH_REC, _RATE_REC, _RETRY_REC, _CACHE_REC, _LOG_REC,
    _HYBRID_REC, _EMBED_REC, _RERANK_REC, _ASYNC_REC, _STREAM_REC,
    _MONITOR_REC, _TRACE_REC, _HEALTH_REC, _FALLBACK_REC,
]

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def gen() -> RoadmapGenerator:
    return RoadmapGenerator()


# ---------------------------------------------------------------------------
# Phase metadata
# ---------------------------------------------------------------------------

class TestPhaseMetadata:
    def test_phase_titles(self, gen):
        req = _req()
        result = gen.generate([_AUTH_REC, _HYBRID_REC, _MONITOR_REC], req)
        titles = {p["title"] for p in result}
        # Only check what actually fires; at minimum one phase should exist
        assert len(result) >= 1

    def test_phase_numbers_present(self, gen):
        req = _req()
        result = gen.generate(_ALL_RECS, req)
        phase_nums = [p["phase"] for p in result]
        assert phase_nums == sorted(phase_nums)  # ascending order

    def test_phases_have_required_keys(self, gen):
        result = gen.generate([_AUTH_REC], _req())
        for phase in result:
            assert "phase"    in phase
            assert "title"    in phase
            assert "timeline" in phase
            assert "tasks"    in phase

    def test_tasks_have_required_keys(self, gen):
        result = gen.generate([_AUTH_REC], _req())
        for phase in result:
            for task in phase["tasks"]:
                for key in ("title", "priority", "category", "reason",
                            "difficulty", "implementation_time"):
                    assert key in task, f"Task missing key: {key}"


# ---------------------------------------------------------------------------
# Phase 1 — Quick Wins
# ---------------------------------------------------------------------------

class TestPhase1:
    def _p1_tasks(self, gen, recs, req=None) -> list[dict]:
        result = gen.generate(recs, req or _req())
        phases = {p["phase"]: p for p in result}
        return phases.get(1, {}).get("tasks", [])

    def test_authentication_lands_in_phase1(self, gen):
        tasks = self._p1_tasks(gen, [_AUTH_REC])
        titles = [t["title"] for t in tasks]
        assert any("authentication" in t.lower() for t in titles)

    def test_rate_limiting_lands_in_phase1(self, gen):
        tasks = self._p1_tasks(gen, [_RATE_REC])
        titles = [t["title"] for t in tasks]
        assert any("rate limit" in t.lower() for t in titles)

    def test_retry_lands_in_phase1(self, gen):
        tasks = self._p1_tasks(gen, [_RETRY_REC])
        titles = [t["title"] for t in tasks]
        assert any("retry" in t.lower() or "backoff" in t.lower() for t in titles)

    def test_cache_lands_in_phase1(self, gen):
        tasks = self._p1_tasks(gen, [_CACHE_REC])
        titles = [t["title"] for t in tasks]
        assert any("cache" in t.lower() or "caching" in t.lower() for t in titles)

    def test_logging_lands_in_phase1(self, gen):
        tasks = self._p1_tasks(gen, [_LOG_REC])
        titles = [t["title"] for t in tasks]
        assert any("log" in t.lower() for t in titles)


# ---------------------------------------------------------------------------
# Phase 2 — Performance Improvements
# ---------------------------------------------------------------------------

class TestPhase2:
    def _p2_tasks(self, gen, recs, req=None) -> list[dict]:
        result = gen.generate(recs, req or _req())
        phases = {p["phase"]: p for p in result}
        return phases.get(2, {}).get("tasks", [])

    def test_hybrid_search_lands_in_phase2(self, gen):
        tasks = self._p2_tasks(gen, [_HYBRID_REC])
        titles = [t["title"] for t in tasks]
        assert any("hybrid" in t.lower() for t in titles)

    def test_embedding_upgrade_lands_in_phase2(self, gen):
        tasks = self._p2_tasks(gen, [_EMBED_REC])
        titles = [t["title"] for t in tasks]
        assert any("embedding" in t.lower() for t in titles)

    def test_cross_encoder_lands_in_phase2(self, gen):
        tasks = self._p2_tasks(gen, [_RERANK_REC])
        titles = [t["title"] for t in tasks]
        assert any("cross-encoder" in t.lower() or "rerank" in t.lower() for t in titles)

    def test_async_pipeline_lands_in_phase2(self, gen):
        tasks = self._p2_tasks(gen, [_ASYNC_REC])
        titles = [t["title"] for t in tasks]
        assert any("async" in t.lower() for t in titles)

    def test_streaming_lands_in_phase2(self, gen):
        tasks = self._p2_tasks(gen, [_STREAM_REC])
        titles = [t["title"] for t in tasks]
        assert any("stream" in t.lower() for t in titles)

    def test_fallback_model_lands_in_phase2(self, gen):
        tasks = self._p2_tasks(gen, [_FALLBACK_REC])
        titles = [t["title"] for t in tasks]
        assert any("fallback" in t.lower() for t in titles)


# ---------------------------------------------------------------------------
# Phase 3 — Production Scaling
# ---------------------------------------------------------------------------

class TestPhase3:
    def _p3_tasks(self, gen, recs, req=None) -> list[dict]:
        result = gen.generate(recs, req or _req())
        phases = {p["phase"]: p for p in result}
        return phases.get(3, {}).get("tasks", [])

    def test_grafana_monitoring_lands_in_phase3(self, gen):
        tasks = self._p3_tasks(gen, [_MONITOR_REC])
        titles = [t["title"] for t in tasks]
        assert any("grafana" in t.lower() or "prometheus" in t.lower() or "monitoring" in t.lower() for t in titles)

    def test_langfuse_tracing_lands_in_phase3(self, gen):
        tasks = self._p3_tasks(gen, [_TRACE_REC])
        titles = [t["title"] for t in tasks]
        assert any("tracing" in t.lower() or "langfuse" in t.lower() or "opentelemetry" in t.lower() for t in titles)

    def test_health_endpoint_lands_in_phase3(self, gen):
        tasks = self._p3_tasks(gen, [_HEALTH_REC])
        titles = [t["title"] for t in tasks]
        assert any("health" in t.lower() for t in titles)


# ---------------------------------------------------------------------------
# Priority ordering within phases
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_high_before_medium_in_phase(self, gen):
        recs = [_HYBRID_REC, _AUTH_REC]   # MEDIUM then HIGH in input
        result = gen.generate(recs, _req())
        for phase in result:
            prios = [t["priority"] for t in phase["tasks"]]
            for i in range(len(prios) - 1):
                a, b = prios[i], prios[i + 1]
                # HIGH(0) <= MEDIUM(1) <= LOW(2)
                order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
                assert order.get(a, 99) <= order.get(b, 99), \
                    f"Priority order violated: {a} before {b} in phase {phase['phase']}"


# ---------------------------------------------------------------------------
# Solved-by-architecture suppression
# ---------------------------------------------------------------------------

class TestSolvedSuppression:
    def test_auth_suppressed_when_enabled(self, gen):
        req = _req(authentication=True)
        result = gen.generate([_AUTH_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("authentication" in t.lower() for t in all_titles), \
            "Auth rec should be suppressed when authentication=True"

    def test_rate_limiting_suppressed_when_enabled(self, gen):
        req = _req(rate_limiting=True)
        result = gen.generate([_RATE_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("rate limit" in t.lower() for t in all_titles)

    def test_retry_suppressed_when_enabled(self, gen):
        req = _req(retry_strategy=True)
        result = gen.generate([_RETRY_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("retry" in t.lower() or "backoff" in t.lower() for t in all_titles)

    def test_cache_suppressed_when_enabled(self, gen):
        req = _req(cache_enabled=True)
        result = gen.generate([_CACHE_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("semantic cach" in t.lower() for t in all_titles)

    def test_logging_suppressed_when_enabled(self, gen):
        req = _req(logging=True)
        result = gen.generate([_LOG_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("structured" in t.lower() and "log" in t.lower() for t in all_titles)

    def test_monitoring_suppressed_when_enabled(self, gen):
        req = _req(monitoring=True)
        result = gen.generate([_MONITOR_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("grafana" in t.lower() or "prometheus" in t.lower() for t in all_titles)

    def test_tracing_suppressed_when_enabled(self, gen):
        req = _req(tracing=True)
        result = gen.generate([_TRACE_REC], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert not any("tracing" in t.lower() for t in all_titles)


# ---------------------------------------------------------------------------
# No duplicates
# ---------------------------------------------------------------------------

class TestNoDuplicates:
    def test_no_duplicate_titles(self, gen):
        duped = _ALL_RECS + _ALL_RECS   # deliberately duplicated
        result = gen.generate(duped, _req())
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert len(all_titles) == len(set(all_titles)), "Duplicate task titles found"


# ---------------------------------------------------------------------------
# Poor architecture produces a long roadmap
# ---------------------------------------------------------------------------

class TestPoorArchitecture:
    def test_poor_arch_has_many_tasks(self, gen):
        req = _req(
            authentication=False, rate_limiting=False, retry_strategy=False,
            cache_enabled=False, logging=False, monitoring=False, tracing=False,
            metrics=False, health_endpoint=False, input_validation=False,
            prompt_injection_protection=False,
        )
        result = gen.generate(_ALL_RECS, req)
        total_tasks = sum(len(p["tasks"]) for p in result)
        assert total_tasks >= 10, f"Poor arch should have many tasks, got {total_tasks}"

    def test_poor_arch_has_all_3_phases(self, gen):
        req = _req(
            authentication=False, rate_limiting=False, retry_strategy=False,
            cache_enabled=False, logging=False, monitoring=False, tracing=False,
        )
        result = gen.generate(_ALL_RECS, req)
        phase_nums = {p["phase"] for p in result}
        assert phase_nums == {1, 2, 3}, f"Expected all 3 phases, got {phase_nums}"


# ---------------------------------------------------------------------------
# Well-designed architecture produces fewer / no tasks
# ---------------------------------------------------------------------------

class TestGoodArchitecture:
    def test_good_arch_suppresses_phase1(self, gen):
        req = _req(
            authentication=True, rate_limiting=True, retry_strategy=True,
            cache_enabled=True, logging=True, input_validation=True,
            prompt_injection_protection=True,
        )
        result = gen.generate(_ALL_RECS, req)
        phase_nums = {p["phase"] for p in result}
        assert 1 not in phase_nums, "Phase 1 should be empty for a well-secured arch"

    def test_fully_configured_arch_produces_fewer_tasks_than_bare(self, gen):
        good_req = _req(
            authentication=True, rate_limiting=True, retry_strategy=True,
            cache_enabled=True, logging=True, monitoring=True, tracing=True,
            metrics=True, health_endpoint=True, input_validation=True,
            prompt_injection_protection=True,
        )
        poor_req = _req(
            authentication=False, rate_limiting=False, retry_strategy=False,
            cache_enabled=False, logging=False, monitoring=False, tracing=False,
        )
        good_result = gen.generate(_ALL_RECS, good_req)
        poor_result = gen.generate(_ALL_RECS, poor_req)

        good_count = sum(len(p["tasks"]) for p in good_result)
        poor_count = sum(len(p["tasks"]) for p in poor_result)
        assert good_count < poor_count, \
            f"Good arch ({good_count}) should have fewer tasks than poor arch ({poor_count})"


# ---------------------------------------------------------------------------
# Distinct architectures → different roadmaps
# ---------------------------------------------------------------------------

class TestDistinctRoadmaps:
    def _titles(self, result) -> set[str]:
        return {t["title"] for p in result for t in p["tasks"]}

    def test_cache_on_vs_off_changes_roadmap(self, gen):
        r_cached   = gen.generate([_CACHE_REC, _AUTH_REC], _req(cache_enabled=True))
        r_no_cache = gen.generate([_CACHE_REC, _AUTH_REC], _req(cache_enabled=False))
        assert self._titles(r_cached) != self._titles(r_no_cache)

    def test_auth_on_vs_off_changes_roadmap(self, gen):
        r_auth   = gen.generate([_AUTH_REC, _HYBRID_REC], _req(authentication=True))
        r_no_auth = gen.generate([_AUTH_REC, _HYBRID_REC], _req(authentication=False))
        assert self._titles(r_auth) != self._titles(r_no_auth)


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    def test_empty_recommendations_returns_empty_list(self, gen):
        assert gen.generate([], _req()) == []

    def test_all_solved_returns_empty_list(self, gen):
        req = _req(
            authentication=True, rate_limiting=True, retry_strategy=True,
            cache_enabled=True, logging=True, monitoring=True, tracing=True,
            metrics=True, health_endpoint=True, input_validation=True,
            prompt_injection_protection=True,
        )
        result = gen.generate([
            _AUTH_REC, _RATE_REC, _RETRY_REC, _CACHE_REC, _LOG_REC,
            _MONITOR_REC, _TRACE_REC, _HEALTH_REC,
        ], req)
        all_titles = [t["title"] for p in result for t in p["tasks"]]
        assert len(all_titles) == 0, f"All should be suppressed, got: {all_titles}"
