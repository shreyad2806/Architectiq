import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Loader2, AlertCircle, RefreshCw, Code2 } from 'lucide-react'
import { api } from '../services/api'

// ─── Default form state ────────────────────────────────────────────────────

const DEFAULTS = {
  project_name: '',
  llm: 'gpt-4o',
  embedding_model: 'text-embedding-3-small',
  vector_db: 'Pinecone',
  framework: 'FastAPI',
  prompt_strategy: 'few-shot',
  monthly_requests: 100000,
  average_prompt_tokens: 1400,
  average_completion_tokens: 500,
  context_window: 128000,
  concurrent_users: 5000,
  rag_enabled: false,
  cache_enabled: false,
  memory: false,
  authentication: false,
  rate_limiting: false,
  retry_strategy: false,
  logging: false,
  monitoring: false,
  tracing: false,
  metrics: false,
  health_endpoint: false,
  observability: false,
  prompt_injection_protection: false,
  input_validation: false,
}

type FormState = typeof DEFAULTS

// ─── Re-usable primitives ─────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="block font-mono text-[11px] uppercase tracking-widest text-slate-500 mb-1.5">
      {children}
    </label>
  )
}

function TextInput({ value, onChange, placeholder = '' }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-lg border border-white/[0.07] bg-[#0c0f19] px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600
                 outline-none transition-colors focus:border-[#6d5ce7]/50 focus:ring-1 focus:ring-[#6d5ce7]/30"
    />
  )
}

function NumberInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <input
      type="number"
      value={value}
      onChange={e => onChange(Number(e.target.value))}
      className="w-full rounded-lg border border-white/[0.07] bg-[#0c0f19] px-3.5 py-2.5 text-[13px] text-white
                 outline-none transition-colors focus:border-[#6d5ce7]/50 focus:ring-1 focus:ring-[#6d5ce7]/30"
    />
  )
}

function SelectInput({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full rounded-lg border border-white/[0.07] bg-[#0c0f19] px-3.5 py-2.5 text-[13px] text-white
                 outline-none transition-colors focus:border-[#6d5ce7]/50 focus:ring-1 focus:ring-[#6d5ce7]/30
                 appearance-none"
    >
      {options.map(o => (
        <option key={o} value={o} className="bg-[#0c0f19]">{o}</option>
      ))}
    </select>
  )
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between rounded-lg border border-white/[0.07] bg-[#0c0f19] px-4 py-3 transition-colors hover:border-white/[0.14]">
      <span className="text-[13px] text-slate-300">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors
          ${checked ? 'border-[#6d5ce7]/60 bg-[#6d5ce7]' : 'border-white/10 bg-white/[0.06]'}`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform
            ${checked ? 'translate-x-[18px]' : 'translate-x-[2px]'}`}
        />
      </button>
    </label>
  )
}

function SectionTitle({ label, title }: { label: string; title: string }) {
  return (
    <div className="mb-6">
      <p className="font-mono text-[10px] uppercase tracking-widest text-[#8b7ff0]">{label}</p>
      <h2 className="mt-1.5 text-[17px] font-semibold text-white">{title}</h2>
    </div>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-white/[0.07] bg-[#090c14] p-6 ${className}`}>
      {children}
    </div>
  )
}

// ─── Live Preview Panel ───────────────────────────────────────────────────

function PreviewPanel({ form }: { form: FormState }) {
  const preview = {
    project_name: form.project_name || '—',
    llm: form.llm,
    embedding_model: form.embedding_model,
    vector_db: form.vector_db,
    framework: form.framework,
    rag_enabled: form.rag_enabled,
    cache_enabled: form.cache_enabled,
    monthly_requests: form.monthly_requests,
    average_prompt_tokens: form.average_prompt_tokens,
    context_window: form.context_window,
    concurrent_users: form.concurrent_users,
    authentication: form.authentication,
    rate_limiting: form.rate_limiting,
    retry_strategy: form.retry_strategy,
    observability: form.observability,
    logging: form.logging,
    monitoring: form.monitoring,
  }

  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.07] bg-[#090c14]">
      <div className="flex items-center gap-2 border-b border-white/[0.07] bg-[#0d1017] px-5 py-3">
        <span className="h-3 w-3 rounded-full bg-red-500/70" />
        <span className="h-3 w-3 rounded-full bg-yellow-500/70" />
        <span className="h-3 w-3 rounded-full bg-emerald-500/70" />
        <span className="ml-3 font-mono text-[11px] text-slate-500">
          POST /api/v1/review · preview
        </span>
      </div>
      <pre
        className="overflow-x-auto p-5 text-[12px] leading-relaxed text-slate-300"
        style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
      >
        <code>{JSON.stringify(preview, null, 2)}</code>
      </pre>
    </div>
  )
}

// ─── Error card ───────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-xl border border-red-500/20 bg-red-500/[0.06] p-5">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
        <div className="flex-1">
          <p className="text-[13px] font-semibold text-red-300">Unable to analyze architecture</p>
          {message && (
            <p className="mt-1 text-[12px] text-red-400/80">{message}</p>
          )}
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/[0.08] px-3 py-1.5 text-[12px] font-medium text-red-300 transition-colors hover:bg-red-500/[0.14]"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────

export default function Review() {
  const navigate = useNavigate()
  const [form, setForm] = useState(DEFAULTS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function set(key: keyof FormState) {
    return (value: FormState[typeof key]) => setForm(prev => ({ ...prev, [key]: value }))
  }

  async function submit() {
    setError(null)
    setLoading(true)
    try {
      const data = await api.review(form as Record<string, unknown>)
      navigate('/loading', { state: { request: form, response: data } })
    } catch (err) {
      setError((err as Error)?.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    submit()
  }

  const canSubmit = !loading && form.project_name.trim().length > 0

  const SubmitButton = ({ fullWidth = false }: { fullWidth?: boolean }) => (
    <button
      type="submit"
      disabled={!canSubmit}
      className={`${fullWidth ? 'w-full' : ''} rounded-lg bg-[#6d5ce7] px-5 py-3 text-[14px] font-medium text-white
                 transition-colors hover:bg-[#5b4bd5] disabled:cursor-not-allowed disabled:opacity-50
                 flex items-center justify-center gap-2`}
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Analyzing…
        </>
      ) : (
        'Analyze Architecture'
      )}
    </button>
  )

  return (
    <div className="min-h-screen bg-[#05070d] antialiased">
      {/* Minimal header */}
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
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden rounded-lg border border-white/10 bg-white/[0.03] px-4 py-2 text-[13px] font-medium text-slate-200 transition-colors hover:bg-white/[0.07] sm:inline-block"
            >
              View API Docs
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12 lg:px-8">
        {/* Page heading */}
        <div className="mb-10">
          <p className="font-mono text-[11px] uppercase tracking-widest text-[#8b7ff0]">
            Architecture Review
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-white lg:text-4xl">
            Analyze Your AI Architecture
          </h1>
          <p className="mt-3 max-w-xl text-[14px] leading-relaxed text-slate-400">
            Fill in your stack details. The preview updates live. When ready,
            submit for a full audit — scores, risks, and a phased optimization roadmap.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_420px]">

            {/* ── LEFT COLUMN ─────────────────────────────────────── */}
            <div className="space-y-6">

              {/* 01 Project Information */}
              <Card>
                <SectionTitle label="01" title="Project Information" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <Label>Project Name *</Label>
                    <TextInput
                      value={form.project_name}
                      onChange={set('project_name')}
                      placeholder="e.g. TalentLens"
                    />
                  </div>
                  <div>
                    <Label>Framework</Label>
                    <SelectInput
                      value={form.framework}
                      onChange={set('framework')}
                      options={['FastAPI', 'Express', 'NestJS', 'Flask', 'Go', 'Django', 'Rails']}
                    />
                  </div>
                  <div>
                    <Label>Prompt Strategy</Label>
                    <SelectInput
                      value={form.prompt_strategy}
                      onChange={set('prompt_strategy')}
                      options={['few-shot', 'zero-shot', 'chain-of-thought', 'react', 'system-prompt']}
                    />
                  </div>
                </div>
              </Card>

              {/* 02 AI Stack */}
              <Card>
                <SectionTitle label="02" title="AI Stack" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <Label>Primary LLM</Label>
                    <SelectInput
                      value={form.llm}
                      onChange={set('llm')}
                      options={[
                        'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo',
                        'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307',
                        'gemini-1.5-pro', 'gemini-1.5-flash',
                        'llama-3.1-70b', 'mistral-large',
                      ]}
                    />
                  </div>
                  <div>
                    <Label>Embedding Model</Label>
                    <SelectInput
                      value={form.embedding_model}
                      onChange={set('embedding_model')}
                      options={[
                        'text-embedding-3-small', 'text-embedding-3-large',
                        'text-embedding-ada-002', 'bge-large', 'bge-m3',
                        'e5-large', 'nomic-embed-text',
                      ]}
                    />
                  </div>
                  <div>
                    <Label>Vector Database</Label>
                    <SelectInput
                      value={form.vector_db}
                      onChange={set('vector_db')}
                      options={['Pinecone', 'Weaviate', 'Qdrant', 'Milvus', 'Chroma', 'pgvector', 'Redis']}
                    />
                  </div>
                  <div>
                    <Label>Context Window (tokens)</Label>
                    <NumberInput value={form.context_window} onChange={set('context_window')} />
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <Toggle label="RAG Enabled"    checked={form.rag_enabled}    onChange={set('rag_enabled')} />
                  <Toggle label="Cache Enabled"  checked={form.cache_enabled}  onChange={set('cache_enabled')} />
                  <Toggle label="Memory / State" checked={form.memory}         onChange={set('memory')} />
                </div>
              </Card>

              {/* 03 Production Scale */}
              <Card>
                <SectionTitle label="03" title="Production Scale" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <Label>Monthly Requests</Label>
                    <NumberInput value={form.monthly_requests} onChange={set('monthly_requests')} />
                  </div>
                  <div>
                    <Label>Concurrent Users</Label>
                    <NumberInput value={form.concurrent_users} onChange={set('concurrent_users')} />
                  </div>
                  <div>
                    <Label>Avg. Prompt Tokens</Label>
                    <NumberInput value={form.average_prompt_tokens} onChange={set('average_prompt_tokens')} />
                  </div>
                  <div>
                    <Label>Avg. Completion Tokens</Label>
                    <NumberInput value={form.average_completion_tokens} onChange={set('average_completion_tokens')} />
                  </div>
                </div>

                <div className="mt-6">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500 mb-3">
                    Security &amp; Reliability
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <Toggle label="Authentication"            checked={form.authentication}               onChange={set('authentication')} />
                    <Toggle label="Rate Limiting"             checked={form.rate_limiting}                onChange={set('rate_limiting')} />
                    <Toggle label="Retry Strategy"            checked={form.retry_strategy}               onChange={set('retry_strategy')} />
                    <Toggle label="Input Validation"          checked={form.input_validation}             onChange={set('input_validation')} />
                    <Toggle label="Prompt Injection Guard"    checked={form.prompt_injection_protection}  onChange={set('prompt_injection_protection')} />
                    <Toggle label="Health Endpoint"           checked={form.health_endpoint}              onChange={set('health_endpoint')} />
                  </div>
                </div>

                <div className="mt-6">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500 mb-3">
                    Observability
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <Toggle label="Logging"             checked={form.logging}       onChange={set('logging')} />
                    <Toggle label="Monitoring"          checked={form.monitoring}    onChange={set('monitoring')} />
                    <Toggle label="Tracing"             checked={form.tracing}       onChange={set('tracing')} />
                    <Toggle label="Metrics"             checked={form.metrics}       onChange={set('metrics')} />
                    <Toggle label="Observability Stack" checked={form.observability} onChange={set('observability')} />
                  </div>
                </div>
              </Card>

              {/* Error */}
              {error && <ErrorCard message={error} onRetry={submit} />}

              {/* Submit — mobile only */}
              <div className="lg:hidden">
                <SubmitButton fullWidth />
              </div>
            </div>

            {/* ── RIGHT COLUMN (sticky) ────────────────────────────── */}
            <div className="hidden lg:block">
              <div className="sticky top-24 space-y-4">
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                  Architecture Preview
                </p>
                <PreviewPanel form={form} />
                <SubmitButton fullWidth />
                <div className="mt-2 flex flex-col items-center gap-0.5 opacity-75" style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace", letterSpacing: '0.08em' }}>
                  <span className="flex items-center gap-1.5 text-[11px] text-[#8b93a7]">
                    <Code2 className="h-3 w-3 shrink-0" />
                    POST /api/v1/review
                  </span>
                  <span className="text-[11px] text-[#8b93a7]">Returns JSON Audit Report</span>
                </div>
              </div>
            </div>

          </div>
        </form>
      </main>
    </div>
  )
}
