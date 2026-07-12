/**
 * API client configuration.
 *
 * Policy: prefer live backend data when the API is reachable. Demo fallback applies
 * only to transport-level failures (network errors, timeouts). HTTP 4xx/5xx from
 * a reachable backend are surfaced to callers as ApiError.
 */
import { clearAuthSession, getAuthToken } from './auth'

export const API_URL = import.meta.env.VITE_API_URL || 'https://previewbackendagro-os.onrender.com'
/** General API calls (dashboard data). Render cold starts can exceed 10s. */
export const FETCH_TIMEOUT_MS = 45000
/** Login/signup — allow time for free-tier backend wake + DB connect. */
export const AUTH_FETCH_TIMEOUT_MS = 90000
/** Production builds never silently substitute demo data. */
export const LIVE_API_ONLY = import.meta.env.PROD && import.meta.env.VITE_ALLOW_DEMO_FALLBACK !== 'true'
export const DEFAULT_COOP_ID = import.meta.env.VITE_COOPERATIVE_ID

export function authHeaders(json = false) {
  const token = getAuthToken()
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  if (json) headers['Content-Type'] = 'application/json'
  return headers
}

let unauthorizedHandled = false

export function handleUnauthorized() {
  if (unauthorizedHandled) return
  unauthorizedHandled = true
  clearAuthSession()
  if (window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
  window.setTimeout(() => {
    unauthorizedHandled = false
  }, 1000)
}

async function handleAuthResponse(response) {
  if (response.status === 401) {
    handleUnauthorized()
    return response
  }
  return response
}

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

/** User-facing message for network timeouts (avoids raw AbortError text). */
export function formatTransportError(err) {
  if (err?.name === 'AbortError') {
    return 'The server is still starting up or the connection timed out. Wait a moment and try again.'
  }
  if (err instanceof TypeError) {
    return 'Could not reach the AgroOS API. Check your connection and try again.'
  }
  return err?.message || 'Network request failed'
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

export async function apiFetch(url, options = {}) {
  const hasExternalSignal = options.signal != null
  const { signal, clear } = hasExternalSignal
    ? { signal: options.signal, clear: () => {} }
    : createFetchSignal()
  try {
    const response = await fetch(url, { ...options, signal })
    await handleAuthResponse(response)
    return response
  } finally {
    clear()
  }
}

export async function fetchJson(url, options = {}) {
  const response = await apiFetch(url, options)
  if (!response.ok) throw await parseResponseError(response)
  if (response.status === 204) return null
  return response.json()
}

/**
 * Run a live fetch; return demo payload only on transport-level failure.
 */
export async function withDemoFallback(fetchLive, getDemo, { fallback = !LIVE_API_ONLY } = {}) {
  try {
    return await fetchLive()
  } catch (err) {
    if (!fallback || !isTransportFailure(err)) throw err
    return getDemo()
  }
}
