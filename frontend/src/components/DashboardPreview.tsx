const metrics = [
  {
    label: 'Architecture Score',
    value: '87',
    suffix: '/100',
    note: 'Strong — 3 optimizations available',
    accent: 'text-white',
  },
  {
    label: 'Monthly AI Cost',
    value: '$24.8K',
    suffix: '',
    note: 'Across 6 model endpoints',
    accent: 'text-white',
  },
  {
    label: 'Potential Savings',
    value: '$9.1K',
    suffix: '',
    note: '↓ 36.7% reduction possible',
    accent: 'text-emerald-400',
  },
  {
    label: 'Production Readiness',
    value: '92',
    suffix: '/100',
    note: 'Ready with minor gaps',
    accent: 'text-white',
  },
]

const findings = [
  {
    level: 'HIGH',
    badge: 'bg-red-500/10 text-red-400 border-red-500/20',
    bold: 'Switch inference tier',
    text: ' for embedding endpoint — projected to cut monthly spend by $2.3K with no latency impact.',
  },
  {
    level: 'HIGH',
    badge: 'bg-red-500/10 text-red-400 border-red-500/20',
    bold: 'Add retry + circuit breaker',
    text: ' around the vector store client — current failure mode has no fallback path.',
  },
  {
    level: 'MED',
    badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    bold: 'Batch small requests',
    text: ' to the rescoring model — reduces per-call overhead under peak load.',
  },
  {
    level: 'LOW',
    badge: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    bold: 'Cache repeated prompts',
    text: ' at the gateway layer — estimated 11% reduction in redundant token spend.',
  },
]

export default function DashboardPreview() {
  return (
    <section className="bg-[#05070d] pb-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="rounded-2xl border border-white/10 bg-[#090c14] shadow-2xl shadow-black/40">
          {/* Terminal header */}
          <div className="flex items-center justify-between border-b border-white/5 px-5 py-3.5">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
              </div>
              <span className="font-mono text-[12px] text-slate-500">
                audit / production-cluster-v3 / report.json
              </span>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/[0.06] px-3 py-1 font-mono text-[11px] text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Audit Complete
            </span>
          </div>

          <div className="p-5 lg:p-6">
            {/* Metric cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {metrics.map((m) => (
                <div
                  key={m.label}
                  className="rounded-xl border border-white/[0.07] bg-[#0c0f19] p-5"
                >
                  <p className="font-mono text-[10px] uppercase tracking-widest text-[#8b7ff0]">
                    {m.label}
                  </p>
                  <p className="mt-3">
                    <span className={`text-3xl font-bold tracking-tight ${m.accent}`}>
                      {m.value}
                    </span>
                    {m.suffix && (
                      <span className="ml-0.5 text-sm text-slate-500">{m.suffix}</span>
                    )}
                  </p>
                  <div className="mt-3 h-px w-full bg-white/[0.07]" />
                  <p className="mt-3 text-[12px] text-slate-500">{m.note}</p>
                </div>
              ))}
            </div>

            {/* Recommendations */}
            <div className="mt-5 rounded-xl border border-white/[0.07] bg-[#0c0f19]">
              <div className="flex items-center justify-between border-b border-white/5 px-5 py-3.5">
                <span className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
                  Top Recommendations
                </span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-slate-600">
                  4 Findings
                </span>
              </div>
              <ul className="divide-y divide-white/5">
                {findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-4 px-5 py-4">
                    <span
                      className={`mt-0.5 shrink-0 rounded border px-2 py-0.5 font-mono text-[10px] font-medium ${f.badge}`}
                    >
                      {f.level}
                    </span>
                    <p className="text-[13px] leading-relaxed text-slate-400">
                      <span className="font-semibold text-slate-200">{f.bold}</span>
                      {f.text}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
