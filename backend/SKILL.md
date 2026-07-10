# ArchitectIQ

## Overview

ArchitectIQ is a REST API and web platform that performs automated architecture reviews of AI systems.

Given a description of an AI stack (LLM, embedding model, vector database, framework, traffic profile, and production controls), the system produces a structured audit report containing:

- A numeric architecture health score and letter grade
- Production readiness assessment
- Dimension-level analysis across cost, latency, security, reliability, scalability, observability, and RAG quality
- Prioritised optimization recommendations with estimated savings, latency impact, implementation difficulty, and time
- A phased optimization roadmap
- A compact AI-agent-consumable JSON summary

The platform is designed to be consumed directly by AI agents, developers, and engineering teams.

---

## Core Features

- **Architecture Health Scoring** — Composite score (0–100) across eight dimensions. Letter grade (A–F) derived from the score.
- **Cost Estimation** — Monthly token cost, embedding cost, vector database cost, infrastructure cost, and potential savings from caching or model switching.
- **Latency Analysis** — P50/P95/P99 latency estimates, TTFT (time to first token), bottleneck identification.
- **Security Analysis** — Checks for authentication, rate limiting, input validation, prompt injection protection.
- **Reliability Analysis** — Checks for retry strategies, circuit breakers, fallback LLMs, health endpoints.
- **Scalability Analysis** — Concurrent user capacity, vector index scalability, horizontal scaling readiness.
- **Observability Analysis** — Logging, monitoring, tracing, metrics coverage.
- **RAG Quality Analysis** — Embedding model suitability, retrieval strategy, context window utilisation, chunking assessment.
- **Recommendation Engine** — Rule-based engine generating prioritised recommendations per dimension. Each recommendation includes priority, category, reason, expected monthly saving, latency improvement, primary benefit, secondary benefit, impact level, difficulty, and implementation time.
- **Optimization Roadmap** — Recommendations grouped into phased plans: Quick Wins, Performance Improvements, Production Hardening.
- **Agent Response** — A compact top-level summary with architecture score, grade, production readiness, estimated cost, potential savings, top priority, and next action.

---

## Supported Architecture Components

### LLM Models
- OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
- Anthropic: claude-3-5-sonnet-20241022, claude-3-haiku-20240307
- Google: gemini-1.5-pro, gemini-1.5-flash
- Meta: llama-3.1-70b
- Mistral: mistral-large

### Embedding Models
- text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002
- bge-large, bge-m3, e5-large, nomic-embed-text

### Vector Databases
- Pinecone, Weaviate, Qdrant, Milvus, Chroma, pgvector, Redis

### Frameworks
- FastAPI, Flask, Django, Express, NestJS, Go, Rails

### Prompt Strategies
- few-shot, zero-shot, chain-of-thought, react, system-prompt

---

## Architecture Review Criteria

Each submitted architecture is evaluated across the following dimensions:

| Dimension     | Weight | Key Signals |
|---------------|--------|-------------|
| Cost          | High   | Token usage, model pricing, cache hit rate, savings potential |
| Latency       | High   | Model inference time, vector retrieval time, context window size |
| Security      | High   | Authentication, rate limiting, input validation, prompt injection protection |
| Reliability   | High   | Retry strategy, circuit breaker, fallback LLM, health endpoint |
| Scalability   | Medium | Concurrent users, vector DB scalability, horizontal scaling |
| Observability | Medium | Logging, monitoring, distributed tracing, metrics |
| RAG Quality   | Medium | Embedding model quality, retrieval strategy, reranking, hybrid search |
| Production    | High   | Composite of security + reliability + observability coverage |

Scores are aggregated into an overall architecture score. Production readiness is assessed separately as a percentage.

---

## Cost Estimation

The cost estimator calculates monthly infrastructure costs from the following inputs:

- `monthly_requests` — Total API calls per month
- `average_prompt_tokens` — Mean tokens in each prompt
- `average_completion_tokens` — Mean tokens in each completion
- `llm` — LLM model identifier (used to look up per-token pricing)
- `embedding_model` — Embedding model (used to look up per-token pricing)
- `vector_db` — Vector database (monthly base cost + per-query cost)
- `cache_enabled` — Whether semantic caching is active
- `rag_enabled` — Whether retrieval-augmented generation is used

**Outputs:**

- `llm_cost` — Monthly LLM token cost
- `embedding_cost` — Monthly embedding cost
- `vector_db_cost` — Monthly vector database cost
- `infrastructure_cost` — Estimated compute/hosting cost
- `total_cost` — Gross monthly cost
- `monthly_cost` — Net monthly cost after savings
- `savings_from_cache` — Estimated savings if semantic cache is enabled
- `savings_from_model_switch` — Estimated savings from switching to a cheaper equivalent model
- `total_savings` — Combined estimated savings
- `savings_percentage` — Percentage reduction achievable

---

## Optimization Engine

The recommendation engine applies rule-based logic against the submitted architecture.

### Recommendation Fields

| Field | Type | Description |
|-------|------|-------------|
| `priority` | string | HIGH / MEDIUM / LOW |
| `category` | string | Cost Optimization / Security / Reliability / Performance / Observability / RAG Optimization |
| `title` | string | Short recommendation title |
| `reason` | string | Explanation of why this recommendation applies |
| `expected_monthly_saving` | string | Estimated cost saving (e.g. "$1,200") or "$0" |
| `latency_improvement` | string | Estimated latency reduction (e.g. "35%") or "0%" |
| `primary_benefit` | string | Primary benefit category (e.g. "Security", "Cost", "Reliability") |
| `secondary_benefit` | string | Supporting benefit (e.g. "Compliance", "Availability") |
| `impact_level` | string | HIGH / MEDIUM / LOW |
| `difficulty` | string | Easy / Medium / Hard |
| `implementation_time` | string | Estimated implementation time |

### Recommendation Categories

- **Cost Optimization** — Caching, model switching, token reduction
- **Security** — Authentication, rate limiting, input validation, prompt injection protection
- **Reliability** — Retry logic, circuit breakers, fallback models, health checks
- **Performance** — Streaming, parallelism, context window tuning
- **Observability** — Logging, monitoring, distributed tracing, metrics
- **RAG Optimization** — Embedding model upgrades, reranking, hybrid search, chunking strategy

### Optimization Roadmap Phases

- **Phase 1 — Quick Wins** — Easy changes with high impact, implementable in hours
- **Phase 2 — Performance Improvements** — Medium-difficulty changes targeting latency and cost
- **Phase 3 — Production Hardening** — Reliability, security, and observability improvements

---

## Production Readiness

Production readiness is scored as a percentage based on the presence of the following controls:

| Control | Category |
|---------|----------|
| Authentication | Security |
| Rate Limiting | Security |
| Input Validation | Security |
| Prompt Injection Protection | Security |
| Retry Strategy | Reliability |
| Health Endpoint | Reliability |
| Logging | Observability |
| Monitoring | Observability |
| Tracing | Observability |
| Metrics | Observability |

A system with all controls enabled achieves 100% production readiness. Missing controls generate HIGH or MEDIUM priority recommendations.

---

## API Endpoints

### `GET /health`
Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### `POST /api/v1/review`
Runs a full architecture audit.

**Request body (selected fields):**
```json
{
  "project_name": "string",
  "llm": "gpt-4o",
  "embedding_model": "text-embedding-3-small",
  "vector_db": "pinecone",
  "framework": "FastAPI",
  "prompt_strategy": "few-shot",
  "monthly_requests": 100000,
  "average_prompt_tokens": 1400,
  "average_completion_tokens": 500,
  "context_window": 128000,
  "concurrent_users": 5000,
  "rag_enabled": true,
  "cache_enabled": false,
  "authentication": false,
  "rate_limiting": false,
  "retry_strategy": false,
  "logging": false,
  "monitoring": false,
  "tracing": false,
  "metrics": false,
  "health_endpoint": false,
  "prompt_injection_protection": false,
  "input_validation": false
}
```

**Response (top-level keys):**
```json
{
  "project_name": "string",
  "intelligence_summary": {},
  "architecture_overview": {},
  "score_breakdown": {},
  "cost_analysis": {},
  "latency_analysis": {},
  "rag_analysis": {},
  "security_analysis": {},
  "reliability_analysis": {},
  "scalability_analysis": {},
  "observability_analysis": {},
  "recommendations": [],
  "optimization_roadmap": [],
  "agent_response": {},
  "report_metadata": {}
}
```

---

### `POST /api/v1/estimate`
Returns monthly cost estimation only, without full audit.

**Request:** Same schema as `/api/v1/review`.

**Response:**
```json
{
  "llm_cost": 0.0,
  "embedding_cost": 0.0,
  "vector_db_cost": 0.0,
  "infrastructure_cost": 0.0,
  "total_cost": 0.0,
  "monthly_cost": 0.0,
  "savings_from_cache": 0.0,
  "savings_from_model_switch": 0.0,
  "total_savings": 0.0,
  "savings_percentage": 0.0
}
```

---

### `POST /api/v1/recommend`
Generates optimization recommendations without running the full audit.

**Request:** Same schema as `/api/v1/review`.

**Response:**
```json
{
  "recommendations": []
}
```

---

### `GET /skill.md`
Returns this document. Hidden from OpenAPI schema. Media type: `text/markdown`.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI 0.115 |
| Runtime | Python 3.12 |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Frontend | React 19 + TypeScript + Vite |
| Styling | TailwindCSS v4 |
| Backend Hosting | Render |
| Frontend Hosting | Vercel |

---

## Example Use Cases

- **AI Agent Decision Support** — An AI agent submits an architecture configuration and uses the JSON response to decide whether to recommend infrastructure changes.
- **Cost Audit** — A developer submits their current stack to estimate monthly LLM and infrastructure costs before scaling.
- **Production Readiness Gate** — A CI/CD pipeline submits an architecture spec and fails the build if production readiness falls below a threshold.
- **Architecture Comparison** — Compare two architecture configurations (e.g. gpt-4o vs gpt-4o-mini) by submitting both and comparing scores and costs.
- **Startup Stack Review** — A startup evaluates their RAG pipeline for security, reliability, and cost before going to production.

---

## Limitations

- Cost estimates are based on publicly available model pricing and may not reflect negotiated enterprise rates.
- Latency estimates are statistical approximations; actual latency depends on network, load, and provider availability.
- The recommendation engine is rule-based, not ML-based. It does not learn from historical data.
- Architecture inputs are self-reported; the system cannot inspect live infrastructure.
- RAG quality analysis is limited to the inputs provided; chunk size, document quality, and retrieval relevance are not directly measurable.
- Concurrent user capacity estimates assume uniform request distribution.

---

## Repository

- **Frontend:** https://architectiq-liard.vercel.app
- **Backend API:** https://architectiq.onrender.com
- **API Docs:** https://architectiq.onrender.com/docs
- **Author:** Shreya Dubey — https://github.com/shreyad2806
