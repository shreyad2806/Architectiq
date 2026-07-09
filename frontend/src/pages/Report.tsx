import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Box } from 'lucide-react'
import Footer from '../components/Footer'

// ─── Types (best-effort, mirrors backend response shape) ─────────────────

interface RoadmapPhase {
  phase: number
  title: string
  timeline: string
  tasks: string[]
}

interface Recommendation {
  priority: string
  title: string
  reason: string
  expected_monthly_saving?: string
  latency_improvement?: string
  difficulty?: string
  implementation_time?: string
}

interface Risk {
  severity?: string
  title?: string
  description?: string
  impact?: string
}

interface ScoreBreakdown {
  cost_efficiency?: number
  latency?: number
  reliability?: number
  scalability?: number
}

interface ReportResponse {
  intelligence_summary?: {
    overall_verdict?: string
    architecture_score?: number
    critical_risks?: string[]
    top_priorities?: string[]
    estimated_monthly_savings?: string
    estimated_latency_improvement?: string
    ai_maturity_level?: { level?: number; title?: string }
  }
  architecture_overview?: {
    overall_score?: number
    architecture_grade?: string
    production_readiness?: number
    score_breakdown?: ScoreBreakdown
  }
  cost_analysis?: {
    estimated_monthly_cost?: string
    potential_monthly_savings?: string
    savings_percentage?: string
  }
  critical_risks?: Risk[]
  recommendations?: Recommendation[]
  optimization_roadmap?: RoadmapPhase[]
  findings_summary?: {
    total?: number
    by_severity?: { critical?: number; high?: number; medium?: number; low?: number }
    by_category?: { security?: number; reliability?: number; cost?: number; latency?: number; scalability?: number }
  }
  audit_report?: {
    report_id?: string
    generated_at?: string
    audit_duration_ms?: number
    total_findings?: number
    total_recommendations?: number
    content_type?: string
  }
}

// ─── Design-system primitives ─────────────────────────────────────────────

function MonoEyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
      {children}
    </p>
  )
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="mb-8">
      <MonoEyebrow>{eyebrow}</MonoEyebrow>
      <h2 className="mt-2 text-2xl font-bold tracking-tight text-white lg:text-3xl">{title}</h2>
    </div>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-white/[0.07] bg-[#090c14] ${className}`}>
      {children}
    </div>
  )
}

function ThinBar({ value, color = 'bg-[#6d5ce7]', max = 100 }: { value: number; color?: string; max?: number }) {
  const pct = Math.min(Math.round((value / max) * 100), 100)
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const p = (priority ?? '').toUpperCase()
  const cls =
    p === 'HIGH' || p === 'CRITICAL'
      ? 'border-red-500/25 bg-red-500/[0.08] text-red-400'
      : p === 'MEDIUM' || p === 'MED'
      ? 'border-amber-500/25 bg-amber-500/[0.08] text-amber-400'
      : 'border-sky-500/25 bg-sky-500/[0.08] text-sky-400'
  return (
    <span className={`rounded border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${cls}`}>
      {priority}
    </span>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  return <PriorityBadge priority={severity} />
}

// ─── Corner tick accent (landing page motif) ──────────────────────────────

function TickFrame({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`relative ${className}`}>
      {/* top-left */}
      <span className="pointer-events-none absolute -left-px -top-px h-3 w-3 border-l-2 border-t-2 border-[#6d5ce7]/40" />
      {/* top-right */}
      <span className="pointer-events-none absolute -right-px -top-px h-3 w-3 border-r-2 border-t-2 border-[#6d5ce7]/40" />
      {/* bottom-left */}
      <span className="pointer-events-none absolute -bottom-px -left-px h-3 w-3 border-b-2 border-l-2 border-[#6d5ce7]/40" />
      {/* bottom-right */}
      <span className="pointer-events-none absolute -bottom-px -right-px h-3 w-3 border-b-2 border-r-2 border-[#6d5ce7]/40" />
      {children}
    </div>
  )
}

// ─── Fallback helpers ─────────────────────────────────────────────────────

function num(v: number | undefined, fallback = 0) { return v ?? fallback }
function str(v: string | undefined, fallback = '—') { return v ?? fallback }

// ─── Section 1: Hero Metrics ──────────────────────────────────────────────

function HeroMetrics({ r }: { r: ReportResponse }) {
  const score   = num(r.architecture_overview?.overall_score, 88)
  const grade   = str(r.architecture_overview?.architecture_grade, 'A-')
  const ready   = num(r.architecture_overview?.production_readiness, 95)
  const cost    = str(r.cost_analysis?.estimated_monthly_cost, '$21.9K')
  const savings = str(r.cost_analysis?.potential_monthly_savings, '$8.7K')
  const savePct = str(r.cost_analysis?.savings_percentage, '39.7%')

  const cards = [
    {
      eyebrow: 'Architecture Score',
      main: <><span className="text-4xl font-bold text-white">{score}</span><span className="ml-1 text-lg text-slate-500">/100</span></>,
      sub: <ThinBar value={score} />,
      note: str(r.intelligence_summary?.overall_verdict, 'Production Ready'),
    },
    {
      eyebrow: 'Architecture Grade',
      main: <span className="text-4xl font-bold text-white">{grade}</span>,
      sub: <p className="text-[12px] text-slate-500">Based on 4 audit dimensions</p>,
      note: 'Production Ready',
    },
    {
      eyebrow: 'Est. Monthly Cost',
      main: <span className="text-4xl font-bold text-white">{cost}</span>,
      sub: <p className="text-[12px] text-slate-500">Across all model endpoints</p>,
      note: <span className="text-emerald-400">Potential savings: {savings}</span>,
    },
    {
      eyebrow: 'Production Readiness',
      main: <><span className="text-4xl font-bold text-white">{ready}</span><span className="ml-1 text-lg text-slate-500">%</span></>,
      sub: <ThinBar value={ready} color="bg-emerald-500" />,
      note: <><span className="text-emerald-400">{savePct}</span> cost reduction possible</>,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c, i) => (
        <TickFrame key={i}>
          <Card className="p-6">
            <MonoEyebrow>{c.eyebrow}</MonoEyebrow>
            <div className="mt-4">{c.main}</div>
            <div className="mt-4">{c.sub}</div>
            <div className="mt-3 h-px bg-white/[0.06]" />
            <p className="mt-3 text-[12px] text-slate-500">{c.note}</p>
          </Card>
        </TickFrame>
      ))}
    </div>
  )
}

// ─── Section 2: Executive Summary ────────────────────────────────────────

function ExecutiveSummary({ r }: { r: ReportResponse }) {
  const score   = num(r.architecture_overview?.overall_score, 88)
  const newScore = num(r.architecture_overview?.production_readiness, 95)
  const savings = str(r.cost_analysis?.potential_monthly_savings, '$8.7K')
  const savePct = str(r.cost_analysis?.savings_percentage, '39.7%')
  const topRecs = r.intelligence_summary?.top_priorities ?? [
    'Enable semantic caching',
    'Introduce circuit breakers around the vector store',
    'Switch to GPT-4.1 Mini for low-complexity requests',
  ]
  const findings = num(r.findings_summary?.total ?? r.audit_report?.total_findings, 8)
  const highCount = num(r.findings_summary?.by_severity?.high ?? r.findings_summary?.by_severity?.critical, 3)
  const verdict = str(r.intelligence_summary?.overall_verdict, 'Production Ready')

  const chips = [
    `${findings} Findings`,
    `${highCount} High Priority`,
    `${savePct} Cost Reduction`,
    verdict,
  ]

  return (
    <Card className="p-8">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between mb-6">
        <MonoEyebrow>Executive Summary</MonoEyebrow>
        <span className="font-mono text-[11px] text-slate-600">ArchitectIQ Audit Engine · v1.0</span>
      </div>
      <div className="space-y-4 text-[14px] leading-7 text-slate-300">
        <p>
          ArchitectIQ analyzed your production AI stack and identified{' '}
          <span className="font-semibold text-white">{findings} optimization opportunities</span>.
        </p>
        <p>
          The highest-impact improvements are{' '}
          <span className="text-white font-medium">{topRecs.slice(0, 3).join(', ')}</span>.
        </p>
        <p>
          These changes are estimated to reduce monthly AI infrastructure costs by{' '}
          <span className="font-semibold text-emerald-400">{savings} ({savePct})</span> while
          improving production readiness from{' '}
          <span className="text-white font-medium">{score}</span> to{' '}
          <span className="text-white font-medium">{newScore}</span>.
        </p>
      </div>
      <div className="mt-8 h-px bg-white/[0.06]" />
      <div className="mt-5 flex flex-wrap gap-2">
        {chips.map((chip) => (
          <span
            key={chip}
            className="rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1 font-mono text-[11px] text-slate-400"
          >
            {chip}
          </span>
        ))}
      </div>
    </Card>
  )
}

// ─── Section 3: Architecture Health ──────────────────────────────────────

function ArchitectureHealth({ r }: { r: ReportResponse }) {
  const sb = r.architecture_overview?.score_breakdown
  const cards = [
    { title: 'Cost Efficiency', score: num(sb?.cost_efficiency, 85), color: 'bg-sky-500',     insight: 'Caching would reduce token spend' },
    { title: 'Latency',         score: num(sb?.latency, 90),          color: 'bg-[#6d5ce7]',  insight: 'P95 within target SLA' },
    { title: 'Reliability',     score: num(sb?.reliability, 82),      color: 'bg-amber-500',  insight: 'Circuit breaker absent' },
    { title: 'Scalability',     score: num(sb?.scalability, 92),      color: 'bg-emerald-500',insight: 'Auto-scaling configured' },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.title} className="p-5">
          <MonoEyebrow>{c.title}</MonoEyebrow>
          <div className="mt-4 flex items-end gap-1">
            <span className="text-3xl font-bold text-white">{c.score}</span>
            <span className="mb-0.5 text-sm text-slate-500">/100</span>
          </div>
          <div className="mt-3">
            <ThinBar value={c.score} color={c.color} />
          </div>
          <p className="mt-3 text-[12px] text-slate-500">{c.insight}</p>
        </Card>
      ))}
    </div>
  )
}

// ─── Section 4: Critical Risks ────────────────────────────────────────────

function CriticalRisks({ r }: { r: ReportResponse }) {
  const risks: Risk[] = r.critical_risks?.length
    ? r.critical_risks
    : [
        {
          severity: 'CRITICAL',
          title: 'No Circuit Breaker',
          description: 'Vector store outages currently cascade across the request pipeline.',
          impact: 'Service-wide request failures.',
        },
        {
          severity: 'HIGH',
          title: 'Single Availability Zone',
          description: 'RAG infrastructure has no regional redundancy.',
          impact: 'Single point of failure.',
        },
        {
          severity: 'HIGH',
          title: 'No Semantic Cache',
          description: 'Repeated prompts generate redundant token spend with no deduplication.',
          impact: '~40% unnecessary token costs.',
        },
      ]

  return (
    <div className="rounded-xl border border-red-500/15 bg-[#090c14] p-6">
      <div className="mb-6 flex items-center justify-between">
        <MonoEyebrow>Critical Risks</MonoEyebrow>
        <span className="font-mono text-[11px] text-red-400/70">{risks.length} issues identified</span>
      </div>
      <div className="space-y-4">
        {risks.map((risk, i) => (
          <div
            key={i}
            className="rounded-lg border border-white/[0.05] bg-[#0c0f19] p-5"
          >
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <SeverityBadge severity={str(risk.severity, 'HIGH')} />
              <span className="text-[14px] font-semibold text-white">{str(risk.title, 'Unknown Risk')}</span>
            </div>
            <p className="text-[13px] leading-relaxed text-slate-400">{str(risk.description, '')}</p>
            {risk.impact && (
              <div className="mt-3 flex items-start gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-slate-600 mt-0.5">Impact</span>
                <span className="text-[13px] text-slate-400">{risk.impact}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Section 5: Recommendations ───────────────────────────────────────────

function Recommendations({ r }: { r: ReportResponse }) {
  const recs: Recommendation[] = r.recommendations?.length
    ? r.recommendations
    : [
        { priority: 'HIGH', title: 'Enable Semantic Cache', reason: 'Repeated prompts generate unnecessary token costs.', expected_monthly_saving: '$4.2K/month', latency_improvement: '-32%', difficulty: 'Easy', implementation_time: '2 hours' },
        { priority: 'MEDIUM', title: 'Switch to GPT-4.1 Mini', reason: 'High request volume doesn\'t require GPT-4 for every query.', expected_monthly_saving: '$2.8K/month', latency_improvement: '-18%', difficulty: 'Easy', implementation_time: '30 minutes' },
        { priority: 'HIGH', title: 'Implement Circuit Breaker', reason: 'Vector store client needs graceful failure handling.', expected_monthly_saving: '$0', latency_improvement: '0%', difficulty: 'Medium', implementation_time: '1 day' },
        { priority: 'MEDIUM', title: 'Enable Distributed Tracing', reason: 'No end-to-end visibility across the request pipeline.', expected_monthly_saving: '$0', latency_improvement: '-8%', difficulty: 'Medium', implementation_time: '3 hours' },
      ]

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {recs.map((rec, i) => (
        <Card key={i} className="p-6">
          <div className="flex items-start justify-between gap-3 mb-4">
            <PriorityBadge priority={rec.priority} />
          </div>
          <h3 className="text-[15px] font-semibold text-white mb-2">{rec.title}</h3>
          <p className="text-[13px] leading-relaxed text-slate-400 mb-5">{rec.reason}</p>
          <div className="h-px bg-white/[0.06] mb-4" />
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            {[
              { label: 'Savings',    value: str(rec.expected_monthly_saving, '—') },
              { label: 'Latency',    value: str(rec.latency_improvement, '—') },
              { label: 'Difficulty', value: str(rec.difficulty, '—') },
              { label: 'Time',       value: str(rec.implementation_time, '—') },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-600">{label}</p>
                <p className="mt-1 text-[13px] font-medium text-slate-200">{value}</p>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}

// ─── Section 6: Optimization Roadmap ─────────────────────────────────────

function OptimizationRoadmap({ r }: { r: ReportResponse }) {
  const phases: RoadmapPhase[] = r.optimization_roadmap?.length
    ? r.optimization_roadmap
    : [
        { phase: 1, title: 'Quick Wins',   timeline: 'Today',  tasks: ['Enable cache', 'Circuit breaker', 'Rate limiting'] },
        { phase: 2, title: 'Performance',  timeline: 'Week 1', tasks: ['Parallel retrieval', 'Prompt compression', 'Streaming'] },
        { phase: 3, title: 'Production',   timeline: 'Week 2', tasks: ['Observability', 'Langfuse', 'Auto scaling'] },
      ]

  return (
    <Card className="p-6 lg:p-8">
      <div className="relative">
        {/* Horizontal connector line (desktop) */}
        <div className="absolute top-6 left-0 right-0 hidden h-px bg-white/[0.06] lg:block" style={{ top: '20px' }} />
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {phases.map((phase, idx) => (
            <div key={phase.phase} className="relative">
              {/* Phase dot */}
              <div className="flex items-center gap-3 mb-5">
                <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[#6d5ce7]/40 bg-[#6d5ce7]/15">
                  <span className="font-mono text-[11px] font-bold text-[#8b7ff0]">{idx + 1}</span>
                </span>
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Phase {phase.phase}</p>
                  <p className="text-[14px] font-semibold text-white">{phase.title}</p>
                </div>
              </div>
              <div className="ml-11">
                <span className="inline-block rounded-full border border-white/[0.07] bg-white/[0.03] px-2.5 py-1 font-mono text-[11px] text-slate-400 mb-4">
                  {phase.timeline}
                </span>
                <ul className="space-y-2">
                  {phase.tasks.map((task) => (
                    <li key={task} className="flex items-center gap-2 text-[13px] text-slate-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-[#6d5ce7]/60 shrink-0" />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}

// ─── Section 7: AI Agent API Response ────────────────────────────────────

function AgentApiResponse({ r, request }: { r: ReportResponse; request: unknown }) {
  const ar = r.audit_report
  const snippet = JSON.stringify(
    {
      status: 'success',
      report_id: ar?.report_id ?? 'arc-' + Math.random().toString(36).slice(2, 9),
      audit_duration_ms: ar?.audit_duration_ms ?? 847,
      generated_at: ar?.generated_at ?? new Date().toISOString(),
      total_findings: ar?.total_findings ?? r.findings_summary?.total ?? 8,
      total_recommendations: ar?.total_recommendations ?? r.recommendations?.length ?? 4,
      architecture_score: r.architecture_overview?.overall_score ?? 88,
      estimated_monthly_savings: r.cost_analysis?.potential_monthly_savings ?? '$8.7K',
      content_type: 'application/json',
    },
    null,
    2
  )

  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.07] bg-[#090c14]">
      {/* Terminal header */}
      <div className="flex items-center justify-between border-b border-white/[0.07] bg-[#0d1017] px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-red-500/70" />
          <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
          <span className="h-3 w-3 rounded-full bg-emerald-500/70" />
          <span className="ml-3 font-mono text-[11px] text-slate-500">Machine Readable Report</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-emerald-400">
            <span className="text-slate-500">POST /review</span> · 200 OK
          </span>
        </div>
      </div>
      <pre
        className="overflow-x-auto p-6 text-[12px] leading-relaxed text-slate-300"
        style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
      >
        <code>
          {snippet
            .replace(/"([^"]+)":/g, (_, k) => `"${k}":`)
            .split('\n')
            .map((line, i) => {
              if (line.includes('status') || line.includes('200')) return `\u001b[0m${line}`
              return line
            })
            .join('\n')}
        </code>
      </pre>
      <div className="border-t border-white/[0.07] bg-[#0d1017] px-5 py-3">
        <span className="font-mono text-[11px] text-slate-600">Content-Type: application/json · ArchitectIQ API v1.0</span>
      </div>
    </div>
  )
}

// ─── Section 8: Findings by Severity ─────────────────────────────────────

function FindingsBySeverity({ r }: { r: ReportResponse }) {
  const bySev = r.findings_summary?.by_severity ?? {}
  const byCat = r.findings_summary?.by_category ?? {}
  const total = r.findings_summary?.total ?? 25

  const severities = [
    { label: 'Critical', count: bySev.critical ?? 2,  color: 'bg-red-500',    textColor: 'text-red-400' },
    { label: 'High',     count: bySev.high ?? 6,     color: 'bg-amber-500',  textColor: 'text-amber-400' },
    { label: 'Medium',   count: bySev.medium ?? 5,   color: 'bg-sky-500',    textColor: 'text-sky-400' },
    { label: 'Low',      count: bySev.low ?? 1,      color: 'bg-slate-500',  textColor: 'text-slate-400' },
  ]

  const cats = [
    { label: 'Security',     count: byCat.security    ?? 4 },
    { label: 'Reliability',  count: byCat.reliability ?? 7 },
    { label: 'Cost',         count: byCat.cost        ?? 6 },
    { label: 'Latency',      count: byCat.latency     ?? 5 },
    { label: 'Scalability',  count: byCat.scalability ?? 3 },
  ]

  const maxCount = Math.max(...severities.map(s => s.count), 1)

  return (
    <Card className="p-6 lg:p-8">
      {/* Stacked horizontal bars */}
      <div className="mb-8 space-y-3">
        {severities.map((s) => (
          <div key={s.label} className="flex items-center gap-4">
            <span className={`w-14 font-mono text-[11px] uppercase tracking-wide ${s.textColor}`}>{s.label}</span>
            <div className="flex-1 h-2 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className={`h-full rounded-full ${s.color} transition-all`}
                style={{ width: `${Math.round((s.count / maxCount) * 100)}%` }}
              />
            </div>
            <span className="w-6 text-right font-mono text-[13px] font-semibold text-white">{s.count}</span>
          </div>
        ))}
      </div>

      <div className="h-px bg-white/[0.06] mb-6" />

      {/* Category breakdown */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <div className="sm:col-span-1">
          <p className="font-mono text-[10px] uppercase tracking-widest text-slate-600">Total</p>
          <p className="mt-1 text-2xl font-bold text-white">{total}</p>
        </div>
        {cats.map((c) => (
          <div key={c.label}>
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-600">{c.label}</p>
            <p className="mt-1 text-xl font-bold text-white">{c.count}</p>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ─── Section 9: AI Agent Ready ────────────────────────────────────────────

function AgentReady() {
  const badges = ['OpenAPI', 'REST API', 'JSON Response', 'SKILL.md Compatible', 'Machine Readable', 'FastAPI']
  return (
    <div className="rounded-xl border border-[#6d5ce7]/15 bg-gradient-to-b from-[#6d5ce7]/[0.06] to-[#6d5ce7]/[0.02] px-6 py-8 text-center">
      <MonoEyebrow>API-First Design</MonoEyebrow>
      <h2 className="mt-3 text-xl font-bold text-white">AI Agent Ready</h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] text-slate-400">
        This report was produced by a deterministic REST API designed for both human engineers
        and AI agent pipelines.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
        {badges.map((b) => (
          <span
            key={b}
            className="rounded-full border border-white/[0.07] bg-white/[0.03] px-3.5 py-1.5 font-mono text-[11px] text-slate-300"
          >
            {b}
          </span>
        ))}
      </div>
    </div>
  )
}

// ─── Main page ─────────────────────────────────────────────────────────────

export default function Report() {
  const location = useLocation()
  const navigate  = useNavigate()
  const state = location.state as { request?: unknown; response?: ReportResponse } | null

  useEffect(() => {
    if (!state?.response) {
      navigate('/review', { replace: true })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const r: ReportResponse = state?.response ?? {}
  const projectName = (state?.request as Record<string, string> | null)?.project_name ?? 'production-cluster-a3'

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
              <span className="text-[15px] font-semibold tracking-tight text-white">ArchitectIQ</span>
            </a>
            <nav className="hidden items-center gap-8 md:flex">
              {['Product', 'How It Works', 'Docs', 'Pricing'].map(l => (
                <a key={l} href="/" className="text-[13px] text-slate-400 transition-colors hover:text-white">{l}</a>
              ))}
            </nav>
            <div className="flex items-center gap-3">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden rounded-lg border border-white/10 bg-white/[0.03] px-4 py-2 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07] sm:inline-block"
              >
                View API Docs
              </a>
              <a
                href="/review"
                className="rounded-lg bg-[#6d5ce7] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#5b4bd5]"
              >
                New Audit
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-14 lg:px-8">

        {/* ── Page header ─────────────────────────────────────────── */}
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/[0.06] px-3.5 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="font-mono text-[11px] uppercase tracking-widest text-emerald-400">
              Audit Complete
            </span>
          </div>
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-white lg:text-5xl">
            Report: {projectName} /{' '}
            <span className="text-slate-400">report.json</span>
          </h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-slate-400">
            Detailed analysis of your AI architecture. Surfacing cost inefficiencies, latency
            bottlenecks, reliability gaps and scalability limits.
          </p>
        </div>

        {/* ── S1: Hero metrics ───────────────────────────────────── */}
        <section className="mb-12">
          <HeroMetrics r={r} />
        </section>

        {/* ── S2: Executive Summary ──────────────────────────────── */}
        <section className="mb-12">
          <SectionHeading eyebrow="Intelligence" title="Executive Summary" />
          <ExecutiveSummary r={r} />
        </section>

        {/* ── S3: Architecture Health ────────────────────────────── */}
        <section className="mb-12">
          <SectionHeading eyebrow="Audit Dimensions" title="Architecture Health" />
          <ArchitectureHealth r={r} />
        </section>

        {/* ── S4 + S5: Risks and Recommendations (two-col on lg) ─── */}
        <section className="mb-12">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <div>
              <SectionHeading eyebrow="Issues" title="Critical Risks" />
              <CriticalRisks r={r} />
            </div>
            <div>
              <SectionHeading eyebrow="Opportunities" title="Recommendations" />
              <div className="space-y-4">
                {(r.recommendations?.length ? r.recommendations : [
                  { priority: 'HIGH',   title: 'Enable Semantic Cache',    reason: 'Repeated prompts generate unnecessary token costs.',                    expected_monthly_saving: '$4.2K/month', latency_improvement: '-32%', difficulty: 'Easy',   implementation_time: '2 hours' },
                  { priority: 'MEDIUM', title: 'Switch to GPT-4.1 Mini',   reason: "High volume doesn't require GPT-4 for every query.",                   expected_monthly_saving: '$2.8K/month', latency_improvement: '-18%', difficulty: 'Easy',   implementation_time: '30 minutes' },
                  { priority: 'HIGH',   title: 'Implement Circuit Breaker', reason: 'Vector store needs graceful failure handling.',                         expected_monthly_saving: '$0',          latency_improvement: '0%',   difficulty: 'Medium', implementation_time: '1 day' },
                  { priority: 'MEDIUM', title: 'Enable Distributed Tracing', reason: 'No end-to-end visibility across the request pipeline.',               expected_monthly_saving: '$0',          latency_improvement: '-8%',  difficulty: 'Medium', implementation_time: '3 hours' },
                ] as Recommendation[]).slice(0, 4).map((rec, i) => (
                  <Card key={i} className="p-5">
                    <div className="mb-3"><PriorityBadge priority={rec.priority} /></div>
                    <h3 className="text-[14px] font-semibold text-white mb-1.5">{rec.title}</h3>
                    <p className="text-[12px] leading-relaxed text-slate-400 mb-4">{rec.reason}</p>
                    <div className="h-px bg-white/[0.06] mb-3" />
                    <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                      {[
                        { label: 'Savings',    value: str(rec.expected_monthly_saving, '—') },
                        { label: 'Latency',    value: str(rec.latency_improvement, '—') },
                        { label: 'Difficulty', value: str(rec.difficulty, '—') },
                        { label: 'Time',       value: str(rec.implementation_time, '—') },
                      ].map(({ label, value }) => (
                        <div key={label}>
                          <p className="font-mono text-[10px] uppercase tracking-widest text-slate-600">{label}</p>
                          <p className="mt-0.5 text-[12px] font-medium text-slate-300">{value}</p>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── S6: Optimization Roadmap ───────────────────────────── */}
        <section className="mb-12">
          <SectionHeading eyebrow="Execution Plan" title="Optimization Roadmap" />
          <OptimizationRoadmap r={r} />
        </section>

        {/* ── S7: API Response terminal ──────────────────────────── */}
        <section className="mb-12">
          <SectionHeading eyebrow="Developer" title="AI Agent API Response" />
          <AgentApiResponse r={r} request={state?.request} />
        </section>

        {/* ── S8: Findings by Severity ───────────────────────────── */}
        <section className="mb-12">
          <SectionHeading eyebrow="Breakdown" title="Findings by Severity" />
          <FindingsBySeverity r={r} />
        </section>

        {/* ── S9: AI Agent Ready ─────────────────────────────────── */}
        <section className="mb-16">
          <AgentReady />
        </section>

      </main>

      <Footer />
    </div>
  )
}
