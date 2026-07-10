const BASE_URL =
  import.meta.env.VITE_API_URL ||
  "https://architectiq.onrender.com/api/v1";

// ─── Shared helper ────────────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = ''
    try {
      const err = await res.json()
      detail = err?.detail ?? err?.message ?? JSON.stringify(err)
    } catch {
      detail = await res.text()
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

// ─── Public API ───────────────────────────────────────────────────────────

export const api = {
  review(payload: Record<string, unknown>) {
    return post<Record<string, unknown>>('/review', payload)
  },

  estimate(payload: Record<string, unknown>) {
    return post<Record<string, unknown>>('/estimate', payload)
  },

  recommend(payload: Record<string, unknown>) {
    return post<Record<string, unknown>>('/recommend', payload)
  },
}
