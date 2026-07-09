import { Box, ExternalLink, Download } from 'lucide-react'
import Footer from '../components/Footer'

const ENDPOINTS = [
  {
    method: 'POST',
    path: '/api/v1/review',
    methodColor: 'text-emerald-400',
    desc: 'Run a full architecture audit — returns scores, findings, and a ranked optimization roadmap.',
    body: '{ project_name, llm, embedding_model, vector_db, framework, monthly_requests, … }',
  },
  {
    method: 'POST',
    path: '/api/v1/estimate',
    methodColor: 'text-emerald-400',
    desc: 'Estimate monthly token usage, inference cost, and latency for a given AI configuration.',
    body: '{ llm, monthly_requests, average_prompt_tokens, average_completion_tokens, … }',
  },
  {
    method: 'POST',
    path: '/api/v1/recommend',
    methodColor: 'text-emerald-400',
    desc: 'Generate prioritized, rule-based recommendations without running the full review pipeline.',
    body: '{ llm, rag_enabled, cache_enabled, authentication, rate_limiting, … }',
  },
  {
    method: 'GET',
    path: '/health',
    methodColor: 'text-sky-400',
    desc: 'Service liveness check — returns status, version, and uptime.',
    body: null,
  },
]

export default function Docs() {
  return (
    <div className="min-h-screen bg-[#05070d] antialiased">
      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-white/5 bg-[#05070d]/90 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <a href="/" className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#6d5ce7]">
                <Box className="h-4 w-4 text-white" />
              </span>
              <span className="text-[15px] font-semibold tracking-tight text-white">
                ArchitectIQ
              </span>
            </a>
            <nav className="hidden items-center gap-8 md:flex">
              {[['/', 'Product'], ['/review', 'Analyze'], ['/docs', 'Docs']].map(([href, label]) => (
                <a key={label} href={href} className="text-[13px] text-slate-400 transition-colors hover:text-white">
                  {label}
                </a>
              ))}
            </nav>
            <a
              href="/review"
              className="rounded-lg bg-[#6d5ce7] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#5b4bd5]"
            >
              Analyze Architecture
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-14 lg:px-8">

        {/* ── Hero card ─────────────────────────────────────────────── */}
        <div className="rounded-2xl border border-[#6d5ce7]/20 bg-gradient-to-b from-[#6d5ce7]/[0.10] to-[#6d5ce7]/[0.02] px-8 py-14 lg:px-12">
          <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
            API Reference
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-tight text-white lg:text-5xl">
            ArchitectIQ API
          </h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-slate-400">
            A deterministic REST API that audits AI architectures, estimates infrastructure
            costs, and generates ranked optimization recommendations — designed for both
            human engineers and autonomous AI agents.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 font-mono text-[12px] text-slate-500">
            <span><span className="text-slate-300">Base URL</span> · http://localhost:8000</span>
            <span className="text-slate-700">·</span>
            <span><span className="text-slate-300">4</span> endpoints</span>
            <span className="text-slate-700">·</span>
            <span><span className="text-slate-300">JSON</span> request &amp; response</span>
            <span className="text-slate-700">·</span>
            <span><span className="text-slate-300">No auth</span> required</span>
          </div>

          {/* CTA buttons */}
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-[#6d5ce7] px-5 py-2.5 text-[13px] font-medium text-white transition-colors hover:bg-[#5b4bd5]"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Swagger
            </a>
            <a
              href="http://localhost:8000/openapi.json"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-5 py-2.5 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07]"
            >
              <Download className="h-3.5 w-3.5" />
              Download OpenAPI
            </a>
          </div>
        </div>

        {/* ── Endpoint table ─────────────────────────────────────────── */}
        <div className="mt-14">
          <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
            Endpoints
          </p>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-white">
            API Reference
          </h2>
          <p className="mt-3 max-w-lg text-[14px] leading-relaxed text-slate-400">
            All POST endpoints accept a JSON body and return a structured JSON response.
            The GET /health endpoint requires no body.
          </p>

          <div className="mt-8 overflow-hidden rounded-xl border border-white/[0.07] bg-[#090c14]">
            {/* Terminal bar */}
            <div className="flex items-center gap-2 border-b border-white/[0.07] bg-[#0d1017] px-5 py-3">
              <span className="h-3 w-3 rounded-full bg-red-500/70" />
              <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
              <span className="h-3 w-3 rounded-full bg-emerald-500/70" />
              <span className="ml-3 font-mono text-[11px] text-slate-500">
                architectiq · api reference · v1
              </span>
            </div>

            <div className="divide-y divide-white/[0.05]">
              {ENDPOINTS.map((ep) => (
                <div key={ep.path} className="px-6 py-6 transition-colors hover:bg-white/[0.02]">
                  <div className="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:gap-4">
                    <span className={`shrink-0 font-mono text-[12px] font-bold uppercase w-12 ${ep.methodColor}`}>
                      {ep.method}
                    </span>
                    <span className="shrink-0 font-mono text-[13px] text-white sm:w-52">
                      {ep.path}
                    </span>
                    <span className="text-[13px] leading-relaxed text-slate-400">
                      {ep.desc}
                    </span>
                  </div>
                  {ep.body && (
                    <div className="mt-4 ml-0 sm:ml-[208px]">
                      <p className="font-mono text-[10px] uppercase tracking-widest text-slate-600 mb-2">
                        Request Body
                      </p>
                      <code
                        className="block rounded-lg border border-white/[0.06] bg-[#0c0f19] px-4 py-3 font-mono text-[11px] leading-relaxed text-slate-400"
                        style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
                      >
                        {ep.body}
                      </code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Quick-start snippet ────────────────────────────────────── */}
        <div className="mt-14">
          <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
            Quick Start
          </p>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-white">
            Make your first request
          </h2>
          <p className="mt-3 max-w-lg text-[14px] leading-relaxed text-slate-400">
            Send a single POST to /api/v1/review and receive a complete architecture
            audit in under 90 seconds.
          </p>

          <div className="mt-8 overflow-hidden rounded-xl border border-white/[0.07] bg-[#090c14]">
            <div className="flex items-center gap-2 border-b border-white/[0.07] bg-[#0d1017] px-5 py-3">
              <span className="h-3 w-3 rounded-full bg-red-500/70" />
              <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
              <span className="h-3 w-3 rounded-full bg-emerald-500/70" />
              <span className="ml-3 font-mono text-[11px] text-slate-500">curl · example</span>
            </div>
            <pre
              className="overflow-x-auto p-6 text-[12px] leading-relaxed text-slate-300"
              style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
            >
              <code>{`curl -X POST http://localhost:8000/api/v1/review \\
  -H "Content-Type: application/json" \\
  -d '{
    "project_name": "MyAIApp",
    "llm": "gpt-4o",
    "embedding_model": "text-embedding-3-small",
    "vector_db": "Pinecone",
    "framework": "FastAPI",
    "monthly_requests": 100000,
    "average_prompt_tokens": 1400,
    "average_completion_tokens": 500,
    "context_window": 128000,
    "concurrent_users": 5000,
    "prompt_strategy": "few-shot"
  }'`}</code>
            </pre>
          </div>
        </div>

      </main>

      <Footer />
    </div>
  )
}
