const CARDS = [
  { label: 'REST API',                desc: 'Standard HTTP/JSON interface' },
  { label: 'JSON Responses',          desc: 'Structured, parseable output' },
  { label: 'OpenAPI',                 desc: 'Auto-generated schema at /docs' },
  { label: 'FastAPI',                 desc: 'Async, production-grade backend' },
  { label: 'Machine-readable Reports', desc: 'Designed for downstream pipelines' },
  { label: 'SKILL.md Compatible',     desc: 'Aligns with AI agent skill specs' },
  { label: 'Production Ready',        desc: 'CORS, error handling, logging' },
  { label: 'Easy Integration',        desc: 'One POST request, full audit' },
]

export default function AgentReady() {
  return (
    <section className="bg-[#05070d] py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
          API-First Design
        </p>
        <h2 className="mt-4 max-w-2xl text-3xl font-bold tracking-tight text-white lg:text-4xl">
          Built for AI Agents
        </h2>
        <p className="mt-4 max-w-md text-[14px] leading-relaxed text-slate-400">
          ArchitectIQ is designed to be consumed by autonomous AI systems through
          a simple REST API.
        </p>

        <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {CARDS.map((c) => (
            <div
              key={c.label}
              className="rounded-xl border border-white/[0.07] bg-[#090c14] p-5 transition-colors hover:border-white/[0.14]"
            >
              <span className="inline-flex items-center justify-center rounded-lg border border-[#6d5ce7]/20 bg-[#6d5ce7]/10 px-2.5 py-1">
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#8b7ff0]">
                  ✓
                </span>
              </span>
              <h3 className="mt-4 text-[14px] font-semibold text-white">{c.label}</h3>
              <p className="mt-2 text-[12px] leading-relaxed text-slate-400">{c.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-10">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded-lg border border-white/10 bg-white/[0.03] px-5 py-2.5 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07]"
          >
            View API Documentation
          </a>
        </div>
      </div>
    </section>
  )
}
