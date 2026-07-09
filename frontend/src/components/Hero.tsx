export default function Hero() {
  return (
    <section id="product" className="bg-[#05070d]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="max-w-4xl pt-20 pb-16 lg:pt-28">
          {/* Status badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/[0.06] px-3.5 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="font-mono text-[11px] uppercase tracking-widest text-emerald-400">
              System status: cost review online
            </span>
          </div>

          {/* Heading */}
          <h1 className="mt-7 text-6xl font-bold leading-[1.05] tracking-tight text-white lg:text-7xl">
            Review Your AI
            <br />
            Architecture{' '}
            <span className="text-[#7c6cf5]">Before</span>
            <br />
            <span className="text-[#7c6cf5]">You Deploy.</span>
          </h1>

          {/* Subtitle */}
          <p className="mt-7 max-w-xl text-[15px] leading-relaxed text-slate-400">
            ArchitectIQ audits AI systems for production readiness — surfacing cost
            inefficiencies, latency bottlenecks, reliability gaps, and scalability
            limits before they reach your users.
          </p>

          {/* CTAs */}
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <a
              href="/review"
              className="rounded-lg bg-[#6d5ce7] px-5 py-2.5 text-[13px] font-medium text-white transition-colors hover:bg-[#5b4bd5]"
            >
              Analyze Architecture
            </a>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-white/10 bg-white/[0.03] px-5 py-2.5 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07]"
            >
              View API Docs
            </a>
          </div>

          {/* Stats */}
          <div className="mt-14 flex flex-wrap items-center gap-x-8 gap-y-3 font-mono text-[12px] text-slate-500">
            <span>
              <span className="text-slate-200">4.2k+</span> architectures reviewed
            </span>
            <span>
              <span className="text-slate-200">$18.6M</span> in est. savings identified
            </span>
            <span>
              <span className="text-slate-200">&lt;90s</span> average audit time
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
