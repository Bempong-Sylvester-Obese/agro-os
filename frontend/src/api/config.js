/**
 * API client configuration.
 *
 * Policy: prefer live backend data when the API is reachable. Demo fallback applies
 * only to transport-level failures (network errors, timeouts). HTTP 4xx/5xx from
 * a reachable backend are surfaced to callers as ApiError.
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const FETCH_TIMEOUT_MS = 10000
export const DEFAULT_COOP_ID = import.meta.env.VITE_COOPERATIVE_ID

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function isTransportFailure(err) {
  if (err instanceof ApiError) return false
  if (err?.name === 'AbortError') return true
  if (err instanceof TypeError) return true
  return false
}

export function apiResult(source, data) {
  return { ...data, source: source === 'api' ? 'api' : 'demo' }
}

export function createFetchSignal() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  return {
    signal: controller.signal,
    clear: () => clearTimeout(timeoutId),
  }
}

export async function parseResponseError(response) {
  let detail = response.statusText || `Request failed (${response.status})`
  try {
    const text = await response.text()
    if (text) {
      try {
        const body = JSON.parse(text)
        if (typeof body.detail === 'string') detail = body.detail
        else if (body.detail != null) detail = JSON.stringify(body.detail)
        else detail = text
      } catch {
        detail = text
      }
    }
  } catch {
    // Keep statusText fallback.
  }
  return new ApiError(detail, response.status)
}

export async function fetchJson(url, options = {}) {
  const { signal, clear } = createFetchSignal()
  try {
    const response = await fetch(url, { ...options, signal })
    if (!response.ok) throw await parseResponseError(response)
    if (response.status === 204) return null
    return response.json()
  } finally {
    clear()
  }
}

/**
 * Run a live fetch; return demo payload only on transport-level failure.
 */
export async function withDemoFallback(fetchLive, getDemo, { fallback = true } = {}) {
  try {
    return await fetchLive()
  } catch (err) {
    if (!fallback || !isTransportFailure(err)) throw err
    return getDemo()
  }
}
