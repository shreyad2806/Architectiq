import { Network, CircleDollarSign, Activity, ShieldCheck } from 'lucide-react'

const features = [
  {
    icon: Network,
    iconClass: 'text-[#8b7ff0] bg-[#6d5ce7]/10 border-[#6d5ce7]/20',
    title: 'Architecture Audit',
    description:
      'Static and behavioral analysis of your model pipeline, orchestration layer, and data flow — mapped against production-grade design patterns.',
  },
  {
    icon: CircleDollarSign,
    iconClass: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
    title: 'AI Cost Intelligence',
    description:
      'Token-level cost modeling across providers and model tiers, with concrete recommendations ranked by projected monthly savings.',
  },
  {
    icon: Activity,
    iconClass: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    title: 'Performance Analysis',
    description:
      'Latency profiling across the full request path — identifying cold starts, serial calls, and retry storms before they hit users.',
  },
  {
    icon: ShieldCheck,
    iconClass: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    title: 'Production Readiness',
    description:
      'Checks failover paths, rate-limit handling, observability coverage, and scaling headroom against a production launch checklist.',
  },
]

export default function Features() {
  return (
    <section id="how-it-works" className="bg-[#05070d] py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
          Capabilities
        </p>
        <h2 className="mt-4 max-w-2xl text-3xl font-bold tracking-tight text-white lg:text-4xl">
          Everything you need to ship AI systems with confidence
        </h2>
        <p className="mt-4 max-w-md text-[14px] leading-relaxed text-slate-400">
          Four audit dimensions, one report — built for engineers shipping LLM and
          agent-based systems to production.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-white/[0.07] bg-[#090c14] p-6 transition-colors hover:border-white/[0.14]"
            >
              <span
                className={`inline-flex h-10 w-10 items-center justify-center rounded-lg border ${f.iconClass}`}
              >
                <f.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-5 text-[15px] font-semibold text-white">{f.title}</h3>
              <p className="mt-3 text-[13px] leading-relaxed text-slate-400">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
