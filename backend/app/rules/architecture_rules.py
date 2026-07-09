from dataclasses import dataclass
from typing import Any


class Severity:
    """Severity levels for architecture findings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category:
    """Category tags for grouping findings."""

    COST = "cost"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    OBSERVABILITY = "observability"


@dataclass
class RuleFinding:
    """A single finding produced by an architecture rule."""

    rule_id: str
    title: str
    description: str
    severity: str
    category: str
    estimated_monthly_savings: float | None = None
    estimated_latency_improvement_ms: float | None = None
    implementation_effort: str = "low"


# Thresholds
LARGE_PROMPT_THRESHOLD = 3000
HIGH_OUTPUT_THRESHOLD = 1000
LARGE_TRAFFIC_THRESHOLD = 1_000_000
HIGH_TRAFFIC_THRESHOLD = 100_000

EXPENSIVE_MODELS = {
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "claude-3-opus",
    "claude-3.5-sonnet",
    "claude-3.5-sonnet-4k",
    "gemini-1.5-pro",
}

CHEAPER_ALTERNATIVES = {
    "gpt-4": "gpt-3.5-turbo or gpt-4o-mini",
    "gpt-4-turbo": "gpt-4o-mini",
    "gpt-4o": "gpt-4o-mini",
    "claude-3-opus": "claude-3.5-haiku",
    "claude-3.5-sonnet": "claude-3.5-haiku",
    "gemini-1.5-pro": "gemini-1.5-flash",
}


def _find_components(architecture: dict[str, Any], component_type: str) -> list[dict[str, Any]]:
    """Return components matching the given type."""
    components = architecture.get("components", []) or []
    return [c for c in components if c.get("type") == component_type]


def _has_component(architecture: dict[str, Any], component_type: str) -> bool:
    """Check whether at least one component of the given type exists."""
    return len(_find_components(architecture, component_type)) > 0


def _has_component_attribute(architecture: dict[str, Any], component_type: str, attribute: str) -> bool:
    """Check whether any component of the given type has a specific attribute set."""
    components = _find_components(architecture, component_type)
    return any(c.get(attribute) for c in components)


def check_large_prompts(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag architectures with large input or output token averages."""
    findings: list[RuleFinding] = []
    input_tokens = architecture.get("average_input_tokens", 1000)
    output_tokens = architecture.get("average_output_tokens", 250)

    if input_tokens > LARGE_PROMPT_THRESHOLD:
        findings.append(
            RuleFinding(
                rule_id="large-prompts-input",
                title="Large prompt context detected",
                description=(
                    f"Average input tokens ({input_tokens}) exceed the "
                    f"{LARGE_PROMPT_THRESHOLD} threshold. Consider summarizing history, "
                    "using retrieval, or chunking inputs to reduce cost and latency."
                ),
                severity=Severity.HIGH,
                category=Category.COST,
                implementation_effort="medium",
            )
        )

    if output_tokens > HIGH_OUTPUT_THRESHOLD:
        findings.append(
            RuleFinding(
                rule_id="large-prompts-output",
                title="Large output generation detected",
                description=(
                    f"Average output tokens ({output_tokens}) exceed the "
                    f"{HIGH_OUTPUT_THRESHOLD} threshold. Long outputs increase cost and latency."
                ),
                severity=Severity.MEDIUM,
                category=Category.PERFORMANCE,
                implementation_effort="low",
            )
        )

    return findings


def check_missing_retry(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag missing retry logic around model or external service calls."""
    if _has_component_attribute(architecture, "llm", "retry"):
        return []

    if _has_component_attribute(architecture, "gateway", "retry"):
        return []

    return [
        RuleFinding(
            rule_id="missing-retry",
            title="Missing retry policy",
            description=(
                "No retry or circuit-breaker configuration was detected on LLM or gateway "
                "components. Add exponential backoff and circuit breakers to prevent cascading failures."
            ),
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            implementation_effort="low",
        )
    ]


def check_missing_caching(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag architectures that lack a caching layer for repeated prompts."""
    if _has_component(architecture, "cache"):
        return []

    if _has_component(architecture, "gateway"):
        return []

    return [
        RuleFinding(
            rule_id="missing-caching",
            title="Missing response cache",
            description=(
                "No caching layer found. Repeated identical prompts increase cost and latency. "
                "Consider adding a Redis or similar cache at the gateway."
            ),
            severity=Severity.MEDIUM,
            category=Category.COST,
            implementation_effort="low",
        )
    ]


def check_no_observability(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag architectures without observability components."""
    has_tracing = _has_component(architecture, "tracing")
    has_logging = _has_component(architecture, "logging")
    has_telemetry = _has_component(architecture, "telemetry")

    if has_tracing or has_telemetry:
        return []

    return [
        RuleFinding(
            rule_id="no-observability",
            title="Missing observability",
            description=(
                "No tracing or telemetry component found. Add distributed tracing (e.g., OpenTelemetry) "
                "and structured logging to debug latency and failure paths in production."
            ),
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            implementation_effort="low",
        )
    ]


def check_no_monitoring(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag architectures without monitoring or alerting."""
    has_monitoring = _has_component(architecture, "monitoring")
    has_alerting = _has_component(architecture, "alerting")

    if has_monitoring or has_alerting:
        return []

    return [
        RuleFinding(
            rule_id="no-monitoring",
            title="Missing monitoring and alerting",
            description=(
                "No monitoring or alerting component found. Add dashboards and alerts for "
                "error rates, latency p99, and cost spikes before production launch."
            ),
            severity=Severity.HIGH,
            category=Category.OBSERVABILITY,
            implementation_effort="low",
        )
    ]


def check_large_monthly_traffic(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag very high monthly request volumes that need scale planning."""
    traffic = architecture.get("estimated_requests_per_month")
    if traffic is None:
        return []

    findings: list[RuleFinding] = []
    if traffic > LARGE_TRAFFIC_THRESHOLD:
        findings.append(
            RuleFinding(
                rule_id="large-traffic",
                title="Very large monthly traffic volume",
                description=(
                    f"Estimated {traffic:,} requests per month. Validate rate limits, autoscaling, "
                    "and cost budgets across all providers."
                ),
                severity=Severity.HIGH,
                category=Category.PERFORMANCE,
                implementation_effort="medium",
            )
        )
    elif traffic > HIGH_TRAFFIC_THRESHOLD:
        findings.append(
            RuleFinding(
                rule_id="high-traffic",
                title="High monthly traffic volume",
                description=(
                    f"Estimated {traffic:,} requests per month. Confirm autoscaling, quotas, "
                    "and load testing for the expected load."
                ),
                severity=Severity.MEDIUM,
                category=Category.PERFORMANCE,
                implementation_effort="low",
            )
        )

    return findings


def check_expensive_models(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag expensive model usage and suggest cheaper alternatives."""
    llm_components = _find_components(architecture, "llm")
    findings: list[RuleFinding] = []

    for component in llm_components:
        model = (component.get("model") or "").lower()
        if model not in EXPENSIVE_MODELS:
            continue

        alternative = CHEAPER_ALTERNATIVES.get(model, "a smaller model")
        findings.append(
            RuleFinding(
                rule_id=f"expensive-model-{model}",
                title=f"Expensive model: {model}",
                description=(
                    f"'{model}' is a high-cost model. For many use cases, {alternative} can "
                    "reduce cost significantly with minimal quality loss."
                ),
                severity=Severity.HIGH,
                category=Category.COST,
                estimated_monthly_savings=None,
                implementation_effort="low",
            )
        )

    return findings


def check_vector_db_bottlenecks(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Flag vector database components that may become bottlenecks."""
    vector_stores = _find_components(architecture, "vector_store")
    if not vector_stores:
        return []

    findings: list[RuleFinding] = []
    traffic = architecture.get("estimated_requests_per_month", 0) or 0

    for store in vector_stores:
        provider = store.get("provider", "unknown")
        has_replicas = store.get("replicas") or store.get("replication")
        has_index_optimization = store.get("index_optimized") or store.get("metadata_filtering")

        if traffic > HIGH_TRAFFIC_THRESHOLD and not has_replicas:
            findings.append(
                RuleFinding(
                    rule_id=f"vector-db-replicas-{provider}",
                    title=f"Vector DB missing replicas: {provider}",
                    description=(
                        f"High traffic and no replication configured for {provider}. "
                        "Enable replicas to avoid query latency spikes and downtime."
                    ),
                    severity=Severity.HIGH,
                    category=Category.RELIABILITY,
                    implementation_effort="medium",
                )
            )

        if not has_index_optimization:
            findings.append(
                RuleFinding(
                    rule_id=f"vector-db-index-{provider}",
                    title=f"Vector DB index can be optimized: {provider}",
                    description=(
                        f"{provider} vector store does not show metadata filtering or index optimization. "
                        "Add filters and choose the right index type for query patterns."
                    ),
                    severity=Severity.MEDIUM,
                    category=Category.PERFORMANCE,
                    implementation_effort="medium",
                )
            )

    return findings


# Registry of all architecture rules. Add new rules here to include them in analysis.
RULES: list[Any] = [
    check_large_prompts,
    check_missing_retry,
    check_missing_caching,
    check_no_observability,
    check_no_monitoring,
    check_large_monthly_traffic,
    check_expensive_models,
    check_vector_db_bottlenecks,
]


def analyze_architecture(architecture: dict[str, Any]) -> list[RuleFinding]:
    """Run all registered rules against an architecture and return findings."""
    findings: list[RuleFinding] = []
    for rule in RULES:
        findings.extend(rule(architecture))
    return findings
