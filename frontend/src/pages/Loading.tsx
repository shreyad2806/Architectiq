import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Box, Check, Loader2, Clock } from 'lucide-react'

// ─── Step definitions ─────────────────────────────────────────────────────

const STEPS = [
  { id: 'architecture', label: 'Architecture Analysis' },
  { id: 'cost',         label: 'Cost Estimation' },
  { id: 'security',     label: 'Security Review' },
  { id: 'latency',      label: 'Latency Analysis' },
  { id: 'recs',         label: 'Recommendation Engine' },
  { id: 'report',       label: 'Executive Report' },
]

type StepStatus = 'queued' | 'running' | 'complete'

// Each step gets a proportional slice of 4 000 ms total.
// Step durations (ms) — sum = 4 000.
const STEP_DURATIONS = [800, 600, 700, 600, 700, 600]
const TOTAL_MS = STEP_DURATIONS.reduce((a, b) => a + b, 0) // 4 000

// ─── Status badge ─────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: StepStatus }) {
  if (status === 'complete') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-500/30">
        <Check className="h-3.5 w-3.5 text-emerald-400" />
      </span>
    )
  }
  if (status === 'running') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#6d5ce7]/20 border border-[#6d5ce7]/40">
        <Loader2 className="h-3.5 w-3.5 text-[#8b7ff0] animate-spin" />
      </span>
    )
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03]">
      <Clock className="h-3 w-3 text-slate-600" />
    </span>
  )
}

function statusLabel(s: StepStatus) {
  if (s === 'complete') return <span className="text-emerald-400">Complete</span>
  if (s === 'running')  return <span className="text-[#8b7ff0]">Running</span>
  return <span className="text-slate-600">Queued</span>
}

// ─── Loading page ─────────────────────────────────────────────────────────

export default function Loading() {
  const location = useLocation()
  const navigate  = useNavigate()
  const state     = location.state as { request?: unknown; response?: unknown } | null

  const [statuses, setStatuses] = useState<StepStatus[]>(
    STEPS.map(() => 'queued')
  )
  const [progress, setProgress] = useState(0)
  const doneRef = useRef(false)

  useEffect(() => {
    if (doneRef.current) return
    doneRef.current = true

    // If there is no response in state at all, redirect back to /review.
    if (!state?.response) {
      navigate('/review', { replace: true })
      return
    }

    let elapsed = 0

    STEPS.forEach((_, idx) => {
      const stepStart = STEP_DURATIONS.slice(0, idx).reduce((a, b) => a + b, 0)
      const stepEnd   = stepStart + STEP_DURATIONS[idx]

      // Mark step as "running" at its start time.
      setTimeout(() => {
        setStatuses(prev => {
          const next = [...prev]
          next[idx] = 'running'
          return next
        })
      }, stepStart)

      // Mark step as "complete" at its end time.
      setTimeout(() => {
        setStatuses(prev => {
          const next = [...prev]
          next[idx] = 'complete'
          return next
        })
      }, stepEnd)
    })

    // Smooth progress bar: tick every 40 ms.
    const TICK = 40
    const interval = setInterval(() => {
      elapsed += TICK
      const pct = Math.min(Math.round((elapsed / TOTAL_MS) * 100), 100)
      setProgress(pct)
      if (elapsed >= TOTAL_MS) {
        clearInterval(interval)
      }
    }, TICK)

    // After all steps complete, navigate to /report.
    setTimeout(() => {
      navigate('/report', {
        state: { request: state.request, response: state.response },
      })
    }, TOTAL_MS + 200)

    return () => clearInterval(interval)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-[#05070d] antialiased flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/5 bg-[#05070d]/90 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex h-16 items-center">
            <a href="/" className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#6d5ce7]">
                <Box className="h-4 w-4 text-white" />
              </span>
              <span className="text-[15px] font-semibold tracking-tight text-white">
                ArchitectIQ
              </span>
            </a>
          </div>
        </div>
      </header>

      {/* Centered card */}
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="w-full max-w-md">

          {/* Title */}
          <div className="mb-8 text-center">
            <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
              Audit in progress
            </p>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-white">
              Analyzing Your Architecture
            </h1>
            <p className="mt-2 text-[13px] text-slate-400">
              Running{' '}
              {statuses.filter(s => s === 'complete').length} of {STEPS.length} checks…
            </p>
          </div>

          {/* Step list */}
          <div className="rounded-xl border border-white/[0.07] bg-[#090c14] divide-y divide-white/[0.05]">
            {STEPS.map((step, idx) => (
              <div
                key={step.id}
                className="flex items-center gap-4 px-5 py-4"
              >
                <StatusBadge status={statuses[idx]} />
                <span
                  className={`flex-1 text-[13px] font-medium transition-colors ${
                    statuses[idx] === 'complete'
                      ? 'text-white'
                      : statuses[idx] === 'running'
                      ? 'text-slate-200'
                      : 'text-slate-500'
                  }`}
                >
                  {step.label}
                </span>
                <span className="font-mono text-[11px]">
                  {statusLabel(statuses[idx])}
                </span>
              </div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between font-mono text-[11px] text-slate-500">
              <span>Progress</span>
              <span className="text-slate-300">{progress}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-[#6d5ce7] transition-all duration-75 ease-linear"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Foot note */}
          <p className="mt-5 text-center font-mono text-[11px] text-slate-600">
            deterministic · no LLM calls · ~4s
          </p>
        </div>
      </div>
    </div>
  )
}
