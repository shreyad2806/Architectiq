export default function CTA() {
  return (
    <section id="analyze" className="bg-[#05070d] py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="rounded-2xl border border-[#6d5ce7]/25 bg-gradient-to-b from-[#6d5ce7]/[0.12] to-[#6d5ce7]/[0.03] px-6 py-16 text-center lg:py-20">
          <h2 className="text-3xl font-bold tracking-tight text-white lg:text-4xl">
            Know your architecture's cost before it ships.
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-[14px] leading-relaxed text-slate-400">
            Run your first audit in under two minutes — no infrastructure changes
            required.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#analyze"
              className="rounded-lg bg-[#6d5ce7] px-5 py-2.5 text-[13px] font-medium text-white transition-colors hover:bg-[#5b4bd5]"
            >
              Analyze Architecture
            </a>
            <a
              href="#docs"
              className="rounded-lg border border-white/10 bg-white/[0.03] px-5 py-2.5 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07]"
            >
              View API Docs
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
