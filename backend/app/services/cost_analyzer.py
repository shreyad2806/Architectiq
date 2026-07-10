"""CostAnalyzer service for estimating AI architecture costs.

Provides deterministic, itemised cost calculations for a given production AI
architecture review request.  Each cost line is computed independently so
callers can display a full breakdown or a single total.

Public API:
    CostAnalyzer().analyze(request)  →  dict   (backward-compatible)
    DetailedCostEstimator().estimate(request) → CostBreakdown (rich)
"""

from __future__ import annotations

import math

from app.schemas import ReviewRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(severity: str, title: str, description: str, impact: str) -> dict:
    return {"severity": severity, "title": title, "description": description, "impact": impact}


def _fmt(value: float) -> str:
    """Format a dollar value as a human-readable string."""
    if value >= 1_000:
        return f"${value:,.0f}"
    return f"${value:.2f}"


# ---------------------------------------------------------------------------
# LLM pricing table  ($ per 1 000 000 tokens)
# ---------------------------------------------------------------------------

PRICING_TABLE: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input_per_1m":  2.50,
        "output_per_1m": 10.00,
    },
    "gpt-4o-mini": {
        "input_per_1m":  0.15,
        "output_per_1m": 0.60,
    },
    "gpt-4.1": {
        "input_per_1m":  2.00,
        "output_per_1m": 8.00,
    },
    "gpt-4.1-mini": {
        "input_per_1m":  0.40,
        "output_per_1m": 1.60,
    },
    "claude-sonnet": {
        "input_per_1m":  3.00,
        "output_per_1m": 15.00,
    },
    "claude-sonnet-4": {
        "input_per_1m":  3.00,
        "output_per_1m": 15.00,
    },
    "claude-haiku": {
        "input_per_1m":  0.25,
        "output_per_1m": 1.25,
    },
    "gemini-2.5-pro": {
        "input_per_1m":  1.25,
        "output_per_1m": 10.00,
    },
    "gemini-2.5-flash": {
        "input_per_1m":  0.075,
        "output_per_1m": 0.30,
    },
    "llama3": {
        "input_per_1m":  0.00,
        "output_per_1m": 0.00,
    },
    "llama-3.1-70b": {
        "input_per_1m":  0.59,
        "output_per_1m": 0.79,
    },
    "mistral-large": {
        "input_per_1m":  3.00,
        "output_per_1m": 9.00,
    },
}

# Embedding model pricing ($ per 1 000 000 tokens)
_EMBEDDING_PRICING: dict[str, float] = {
    "text-embedding-3-small":  0.02,
    "text-embedding-3-large":  0.13,
    "text-embedding-ada-002":  0.10,
    "bge-large":               0.00,   # self-hosted
    "bge-m3":                  0.00,
    "e5-large":                0.00,
}

# Vector DB flat monthly base cost + per-million-vector tier
_VDB_BASE_MONTHLY: dict[str, float] = {
    "pinecone":  70.0,
    "weaviate":  25.0,
    "qdrant":    20.0,
    "milvus":    15.0,
    "chroma":     0.0,   # typically self-hosted / free OSS
    "faiss":      0.0,
    "pgvector":   5.0,
}

# Cheaper baseline model used to size savings from model switching
SAVINGS_BASELINE_MODEL = "gpt-4o-mini"

# Infrastructure overhead as a fraction of (llm + embedding) cost
_INFRA_OVERHEAD_RATE = 0.10   # 10 %

# Storage: cost per GB per month (approximate S3/GCS pricing)
_STORAGE_COST_PER_GB = 0.023

# Estimated vector storage footprint per million requests (GB)
_VECTOR_GB_PER_1M_REQUESTS = 0.5

# Cache hit-rate assumption when caching is enabled
_CACHE_HIT_RATE = 0.35   # 35 % of requests served from cache


def _get_model_pricing(model: str) -> dict[str, float]:
    """Return pricing for a supported LLM, falling back to gpt-4o rates."""
    return PRICING_TABLE.get(model.lower().strip(), PRICING_TABLE["gpt-4o"])


def _get_embedding_pricing(model: str) -> float:
    """Return per-1M-token price for an embedding model, falling back to ada-002."""
    return _EMBEDDING_PRICING.get(model.lower().strip(), _EMBEDDING_PRICING["text-embedding-ada-002"])


def _get_vdb_base(vdb: str) -> float:
    """Return estimated monthly base cost for a vector DB."""
    return _VDB_BASE_MONTHLY.get((vdb or "").lower().strip(), 20.0)


# ---------------------------------------------------------------------------
# Detailed Cost Estimator
# ---------------------------------------------------------------------------

class CostBreakdown:
    """All cost line items for one month of operation."""

    __slots__ = (
        "llm_cost", "embedding_cost", "vector_db_cost",
        "storage_cost", "infrastructure_cost",
        "total_before_savings", "estimated_savings",
        "monthly_cost", "estimated_monthly_tokens",
        "savings_from_cache", "savings_from_model_switch",
    )

    def __init__(
        self,
        llm_cost: float,
        embedding_cost: float,
        vector_db_cost: float,
        storage_cost: float,
        infrastructure_cost: float,
        estimated_monthly_tokens: int,
        savings_from_cache: float,
        savings_from_model_switch: float,
    ) -> None:
        self.llm_cost              = round(llm_cost, 2)
        self.embedding_cost        = round(embedding_cost, 2)
        self.vector_db_cost        = round(vector_db_cost, 2)
        self.storage_cost          = round(storage_cost, 2)
        self.infrastructure_cost   = round(infrastructure_cost, 2)
        self.total_before_savings  = round(
            llm_cost + embedding_cost + vector_db_cost
            + storage_cost + infrastructure_cost, 2
        )
        self.savings_from_cache       = round(savings_from_cache, 2)
        self.savings_from_model_switch = round(savings_from_model_switch, 2)
        # Cap combined savings at the gross total so monthly_cost >= 0
        # and estimated_savings never exceeds what was actually spent.
        raw_savings = round(savings_from_cache + savings_from_model_switch, 2)
        self.estimated_savings     = round(min(raw_savings, self.total_before_savings), 2)
        self.monthly_cost          = round(
            max(self.total_before_savings - self.estimated_savings, 0.0), 2
        )
        self.estimated_monthly_tokens = estimated_monthly_tokens

    def to_dict(self) -> dict:
        return {
            "monthly_cost":          self.monthly_cost,
            "llm_cost":              self.llm_cost,
            "embedding_cost":        self.embedding_cost,
            "vector_db_cost":        self.vector_db_cost,
            "storage_cost":          self.storage_cost,
            "infrastructure_cost":   self.infrastructure_cost,
            "total_before_savings":  self.total_before_savings,
            "estimated_savings":     self.estimated_savings,
            "savings_from_cache":    self.savings_from_cache,
            "savings_from_model_switch": self.savings_from_model_switch,
            "estimated_monthly_tokens": self.estimated_monthly_tokens,
        }


class DetailedCostEstimator:
    """Estimate all infrastructure cost line items for a given architecture."""

    def estimate(self, request: ReviewRequest) -> CostBreakdown:
        """Return a fully itemised CostBreakdown.

        Computation is deterministic: same inputs always produce same outputs.

        Edge-case guarantees:
        - None / missing fields fall back to safe defaults (never produce $0
          from a bad field alone).
        - monthly_requests == 0 is the ONLY valid path to a $0 total.
        - Unknown model names fall back to gpt-4o pricing (conservative).
        """
        # ── Safe field extraction ───────────────────────────────────────────
        monthly_req = max(int(request.monthly_requests or 0), 0)
        prompt_tok  = max(int(request.average_prompt_tokens or 0), 0)
        compl_tok   = max(int(request.average_completion_tokens or 0), 0)
        context_win = max(int(request.context_window or 8_000), 0)
        concurrent  = max(int(request.concurrent_users or 0), 0)
        llm_name    = (request.llm or "").strip() or "gpt-4o"
        embed_name  = (request.embedding_model or "").strip()
        vdb_name    = (request.vector_db or "").strip()
        rag_on      = bool(request.rag_enabled)
        cache_on    = bool(request.cache_enabled)

        total_input_tokens  = monthly_req * prompt_tok
        total_output_tokens = monthly_req * compl_tok
        estimated_monthly_tokens = total_input_tokens + total_output_tokens

        # ── 1. LLM inference cost ───────────────────────────────────────────
        pricing  = _get_model_pricing(llm_name)
        llm_cost = (
            (total_input_tokens  / 1_000_000) * pricing["input_per_1m"]
            + (total_output_tokens / 1_000_000) * pricing["output_per_1m"]
        )

        # ── 2. Embedding cost ───────────────────────────────────────────────
        # Charge embedding whenever RAG is on; each request embeds the prompt.
        emb_price      = _get_embedding_pricing(embed_name)
        embedding_cost = 0.0
        if rag_on and total_input_tokens > 0:
            embedding_cost = (total_input_tokens / 1_000_000) * emb_price

        # ── 3. Vector DB cost ───────────────────────────────────────────────
        vdb_base       = _get_vdb_base(vdb_name)
        vdb_query_tier = max(monthly_req - 50_000, 0) / 1_000 * 0.10
        vector_db_cost = (vdb_base + vdb_query_tier) if rag_on else 0.0

        # ── 4. Storage cost ─────────────────────────────────────────────────
        # Log storage: ~4 KB per 1 M tokens
        log_gb     = (estimated_monthly_tokens / 1_000_000) * 0.004
        # Vector index: grows with request volume (only when RAG is on)
        vec_gb     = (monthly_req / 1_000_000) * _VECTOR_GB_PER_1M_REQUESTS if rag_on else 0.0
        # Context window size drives additional stored-state footprint
        context_gb = (context_win / 1_000_000) * 0.1
        storage_cost = (log_gb + vec_gb + context_gb) * _STORAGE_COST_PER_GB

        # ── 5. Infrastructure overhead ──────────────────────────────────────
        # API gateway, load balancer, compute, monitoring SaaS.
        # Base = 10 % of (LLM + embed); premium = $5 per 100 concurrent users.
        concurrency_premium = math.ceil(max(concurrent, 1) / 100) * 5.0
        infrastructure_cost = (llm_cost + embedding_cost) * _INFRA_OVERHEAD_RATE + concurrency_premium

        # ── 6. Savings ──────────────────────────────────────────────────────
        savings_from_cache = llm_cost * _CACHE_HIT_RATE if cache_on else 0.0

        baseline_pricing  = _get_model_pricing(SAVINGS_BASELINE_MODEL)
        baseline_llm_cost = (
            (total_input_tokens  / 1_000_000) * baseline_pricing["input_per_1m"]
            + (total_output_tokens / 1_000_000) * baseline_pricing["output_per_1m"]
        )
        # Model-switch savings apply only to the non-cached share of traffic.
        # When cache is on, the cache already saves _CACHE_HIT_RATE of llm_cost;
        # the remaining (1 - _CACHE_HIT_RATE) fraction is what a cheaper model
        # would affect.  Without cache the full llm_cost is in scope.
        non_cached_fraction = (1.0 - _CACHE_HIT_RATE) if cache_on else 1.0
        savings_from_model_switch = max(
            (llm_cost - baseline_llm_cost) * non_cached_fraction, 0.0
        )

        return CostBreakdown(
            llm_cost=llm_cost,
            embedding_cost=embedding_cost,
            vector_db_cost=vector_db_cost,
            storage_cost=storage_cost,
            infrastructure_cost=infrastructure_cost,
            estimated_monthly_tokens=int(estimated_monthly_tokens),
            savings_from_cache=savings_from_cache,
            savings_from_model_switch=savings_from_model_switch,
        )


# ---------------------------------------------------------------------------
# CostAnalyzer — backward-compatible wrapper
# ---------------------------------------------------------------------------

class CostAnalyzer:
    """Backward-compatible analyzer. Delegates to DetailedCostEstimator."""

    def __init__(self) -> None:
        self._estimator = DetailedCostEstimator()

    def analyze(self, request: ReviewRequest) -> dict:
        """Return cost analysis dict with full breakdown and findings.

        Backward-compatible keys preserved:
          estimated_monthly_tokens, estimated_monthly_cost,
          potential_monthly_savings, findings

        New keys added:
          breakdown (dict with all 6 line items)
        """
        bd = self._estimator.estimate(request)
        pricing = _get_model_pricing(request.llm)
        findings: list[dict] = []

        # ── Findings ────────────────────────────────────────────────────────
        if pricing["input_per_1m"] >= 3.00 or pricing["output_per_1m"] >= 15.00:
            findings.append(_finding(
                "HIGH", "Very Expensive Model Selected",
                f"'{request.llm}' has high per-token pricing "
                f"(${pricing['input_per_1m']}/1M input, ${pricing['output_per_1m']}/1M output). "
                "Consider a cheaper alternative.",
                "High",
            ))
        elif pricing["input_per_1m"] >= 2.00 or pricing["output_per_1m"] >= 8.00:
            findings.append(_finding(
                "MEDIUM", "Moderately Expensive Model",
                f"'{request.llm}' has moderate per-token pricing. "
                "Evaluate if a cheaper model meets quality requirements.",
                "Medium",
            ))

        if request.average_prompt_tokens > 4_000:
            findings.append(_finding(
                "MEDIUM", "Large Prompt Size",
                f"Average prompt of {request.average_prompt_tokens} tokens is high. "
                "Large prompts significantly increase cost per request.",
                "Medium",
            ))
        elif request.average_prompt_tokens > 2_000:
            findings.append(_finding(
                "LOW", "Above-Average Prompt Size",
                f"Average prompt of {request.average_prompt_tokens} tokens is above average. "
                "Consider prompt compression.",
                "Low",
            ))

        if request.average_completion_tokens > 1_000:
            findings.append(_finding(
                "LOW", "Completion Tokens Above Average",
                f"Average completion of {request.average_completion_tokens} tokens is high. "
                "Output tokens are typically 4–10x more expensive than input.",
                "Low",
            ))

        if bd.savings_from_model_switch >= 500:
            findings.append(_finding(
                "HIGH", "High Savings Potential",
                f"Switching to a cheaper LLM could save ~{_fmt(bd.savings_from_model_switch)}/month. "
                "Evaluate model alternatives.",
                "High",
            ))
        elif bd.savings_from_model_switch >= 100:
            findings.append(_finding(
                "MEDIUM", "Moderate Savings Potential",
                f"Switching to a cheaper LLM could save ~{_fmt(bd.savings_from_model_switch)}/month.",
                "Medium",
            ))

        if not request.cache_enabled and bd.llm_cost > 100:
            findings.append(_finding(
                "HIGH", "Semantic Caching Not Enabled",
                f"Enabling semantic caching could reduce LLM costs by ~{_fmt(bd.llm_cost * _CACHE_HIT_RATE)}/month "
                f"({int(_CACHE_HIT_RATE * 100)}% estimated cache hit rate).",
                "High",
            ))

        return {
            # ── Backward-compatible keys ────────────────────────────────────
            "estimated_monthly_tokens":  bd.estimated_monthly_tokens,
            "estimated_monthly_cost":    bd.total_before_savings,  # gross cost (pre-savings)
            "potential_monthly_savings": bd.estimated_savings,
            "findings": findings,
            # ── New detailed breakdown ──────────────────────────────────────
            "breakdown": bd.to_dict(),
        }

    @staticmethod
    def _calculate_cost(
        input_tokens: int, output_tokens: int, pricing: dict[str, float]
    ) -> float:
        """Calculate cost from token counts and per-1M pricing."""
        input_cost  = (input_tokens  / 1_000_000) * pricing["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
        return input_cost + output_cost
