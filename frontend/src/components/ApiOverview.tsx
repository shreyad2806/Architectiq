const ENDPOINTS = [
  {
    method: 'POST',
    path: '/api/v1/review',
    methodColor: 'text-emerald-400',
    desc: 'Run a full architecture audit — returns scores, findings, and a ranked optimization roadmap.',
  },
  {
    method: 'POST',
    path: '/api/v1/estimate',
    methodColor: 'text-emerald-400',
    desc: 'Estimate monthly token usage, inference cost, and latency for a given AI configuration.',
  },
  {
    method: 'POST',
    path: '/api/v1/recommend',
    methodColor: 'text-emerald-400',
    desc: 'Generate prioritized, rule-based recommendations without running the full review pipeline.',
  },
  {
    method: 'GET',
    path: '/health',
    methodColor: 'text-sky-400',
    desc: 'Service liveness check — returns status, version, and uptime.',
  },
]

export default function ApiOverview() {
  return (
    <section id="docs" className="bg-[#05070d] py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
          Endpoints
        </p>
        <h2 className="mt-4 max-w-2xl text-3xl font-bold tracking-tight text-white lg:text-4xl">
          API Overview
        </h2>
        <p className="mt-4 max-w-md text-[14px] leading-relaxed text-slate-400">
          Four endpoints. Zero configuration. Start reviewing architectures with
          a single HTTP request.
        </p>

        <div className="mt-10 overflow-hidden rounded-xl border border-white/[0.07] bg-[#090c14]">
          {/* Terminal title bar */}
          <div className="flex items-center gap-2 border-b border-white/[0.07] bg-[#0d1017] px-5 py-3">
            <span className="h-3 w-3 rounded-full bg-red-500/70" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
            <span className="h-3 w-3 rounded-full bg-emerald-500/70" />
            <span className="ml-3 font-mono text-[11px] text-slate-500">
              architectiq · API
            </span>
          </div>

          <div className="divide-y divide-white/[0.05]">
            {ENDPOINTS.map((ep) => (
              <div
                key={ep.path}
                className="flex flex-col gap-1.5 px-6 py-5 transition-colors hover:bg-white/[0.02] sm:flex-row sm:items-start sm:gap-4"
              >
                <span
                  className={`shrink-0 font-mono text-[12px] font-bold uppercase w-12 ${ep.methodColor}`}
                >
                  {ep.method}
                </span>
                <span className="shrink-0 font-mono text-[13px] text-white sm:w-52">
                  {ep.path}
                </span>
                <span className="text-[13px] leading-relaxed text-slate-400">
                  {ep.desc}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
