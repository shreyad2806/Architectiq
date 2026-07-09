const steps = [
  {
    step: 'STEP 1',
    title: 'Submit Architecture',
    description:
      'Upload your system diagram, config, or repo — model endpoints, orchestration logic, and infra topology included.',
    snippet: (
      <>
        <span className="text-emerald-400">POST</span>{' '}
        <span className="text-slate-300">/v1/architectures</span>
      </>
    ),
  },
  {
    step: 'STEP 2',
    title: 'AI Reviews System',
    description:
      "ArchitectIQ's audit engine traces data flow, cost model, and stress-tests reliability paths against known failure patterns.",
    snippet: (
      <>
        <span className="text-[#8b7ff0]">status:</span>{' '}
        <span className="text-slate-300">analyzing...</span>
      </>
    ),
  },
  {
    step: 'STEP 3',
    title: 'Receive Optimization Report',
    description:
      'Get a ranked report with scores, savings estimates, and specific fixes — ready to hand to your team or CI pipeline.',
    snippet: (
      <>
        <span className="text-sky-400">GET</span>{' '}
        <span className="text-slate-300">/v1/reports/{'{id}'}</span>
      </>
    ),
  },
]

export default function Process() {
  return (
    <section id="docs" className="bg-[#05070d] py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
          Process
        </p>
        <h2 className="mt-4 max-w-2xl text-3xl font-bold tracking-tight text-white lg:text-4xl">
          From architecture to optimization report in three steps
        </h2>
        <p className="mt-4 max-w-md text-[14px] leading-relaxed text-slate-400">
          Point ArchitectIQ at your system definition — the audit runs end to end
          without manual setup.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
          {steps.map((s) => (
            <div
              key={s.step}
              className="flex flex-col rounded-xl border border-white/[0.07] bg-[#090c14] p-6 transition-colors hover:border-white/[0.14]"
            >
              <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                {s.step}
              </p>
              <h3 className="mt-4 text-[15px] font-semibold text-white">{s.title}</h3>
              <p className="mt-3 flex-1 text-[13px] leading-relaxed text-slate-400">
                {s.description}
              </p>
              <div className="mt-6 rounded-lg border border-white/[0.07] bg-[#0c0f19] px-4 py-2.5 font-mono text-[12px]">
                {s.snippet}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
