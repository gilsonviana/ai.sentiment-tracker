// All requests go through /api which Vite proxies to http://localhost:8000 in dev.
// In production, set VITE_API_URL and update this base accordingly.
const BASE = '/api'

async function handleResponse<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {}
    throw new Error(`${label}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  return handleResponse<T>(res, `GET ${path}`)
}

export async function apiPost<TBody, TResponse>(
  path: string,
  body: TBody,
  params?: Record<string, string>,
): Promise<TResponse> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse<TResponse>(res, `POST ${path}`)
}
