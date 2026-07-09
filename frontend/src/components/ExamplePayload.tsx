const REQUEST = `{
  "project_name": "TalentLens",
  "llm": "gpt-4o",
  "embedding_model": "text-embedding-3-small",
  "vector_db": "Pinecone",
  "framework": "FastAPI",
  "rag_enabled": true,
  "cache_enabled": false,
  "monthly_requests": 100000,
  "average_prompt_tokens": 1400,
  "average_completion_tokens": 500,
  "context_window": 128000,
  "concurrent_users": 5000,
  "authentication": true,
  "rate_limiting": true,
  "retry_strategy": false,
  "logging": true,
  "monitoring": false,
  "tracing": false
}`

const RESPONSE = `{
  "intelligence_summary": {
    "overall_verdict": "Production Ready with Improvements",
    "architecture_score": 74,
    "ai_maturity_level": {
      "level": 3,
      "title": "Scaling"
    },
    "critical_risks": [
      "Semantic caching is not enabled",
      "Retry strategy is absent"
    ],
    "top_priorities": [
      "Enable Semantic Caching",
      "Implement Retry Strategy",
      "Reduce Context Window Size"
    ],
    "estimated_monthly_savings": "$868",
    "estimated_latency_improvement": "35%"
  },
  "architecture_overview": {
    "overall_score": 74,
    "architecture_grade": "B-",
    "production_readiness": 72
  },
  "optimization_roadmap": [
    {
      "phase": 1,
      "title": "Immediate Wins",
      "timeline": "Today",
      "tasks": [
        "Enable Semantic Caching",
        "Implement Retry Strategy"
      ]
    },
    {
      "phase": 2,
      "title": "Production Hardening",
      "timeline": "This Week",
      "tasks": [
        "Reduce Context Window Size",
        "Enable Monitoring"
      ]
    }
  ]
}`

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-white/[0.07] bg-[#090c14]">
      <div className="flex items-center gap-2 border-b border-white/[0.07] bg-[#0d1017] px-5 py-3">
        <span className="h-3 w-3 rounded-full bg-red-500/70" />
        <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
        <span className="h-3 w-3 rounded-full bg-emerald-500/70" />
        <span className="ml-3 font-mono text-[11px] text-slate-500">{title}</span>
      </div>
      <pre className="overflow-x-auto p-5 text-[12px] leading-relaxed text-slate-300"
           style={{ fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace" }}>
        <code>{code}</code>
      </pre>
    </div>
  )
}

export default function ExamplePayload() {
  return (
    <section className="bg-[#05070d] py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
          Example
        </p>
        <h2 className="mt-4 max-w-2xl text-3xl font-bold tracking-tight text-white lg:text-4xl">
          Request &amp; Response
        </h2>
        <p className="mt-4 max-w-md text-[14px] leading-relaxed text-slate-400">
          Send one POST request. Get back a complete architecture audit with
          scores, risks, recommendations, and a phased roadmap.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <CodeBlock title="POST /api/v1/review · request.json" code={REQUEST} />
          <CodeBlock title="200 OK · response.json" code={RESPONSE} />
        </div>
      </div>
    </section>
  )
}
