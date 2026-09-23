/**
 * API client configuration.
 *
 * Policy: the dashboard renders live backend data only. There is no static demo
 * dataset; transport failures (network errors, timeouts) and HTTP 4xx/5xx are
 * surfaced to callers as errors so the UI shows a real error state (#251).
 */
import { clearAuthSession, getAuthToken } from './auth'

export const API_URL = import.meta.env.VITE_API_URL || 'https://api-agroos-company.onrender.com'
/** General API calls (dashboard data). Render cold starts can exceed 10s. */
export const FETCH_TIMEOUT_MS = 45000
/** Login/signup — allow time for free-tier backend wake + DB connect. */
export const AUTH_FETCH_TIMEOUT_MS = 90000
/** Moolre disburse/collect can take 60s+ (validate + transfer + status). */
export const MUTATION_TIMEOUT_MS = 120000
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
  constructor(message, status, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    // Structured `detail` from the API when present, e.g. entitlement errors:
    // { code: 'plan_limit_reached', limit_key, limit, used, plan, message }
    this.detail = detail
  }
}

/** Entitlement error codes returned with HTTP 403 by the plan gates. */
export const ENTITLEMENT_CODES = new Set([
  'plan_limit_reached',
  'sms_quota_exceeded',
  'feature_not_in_plan',
])

/**
 * Turn a FastAPI `detail` (string or structured object) into a user-facing
 * message. Entitlement details carry their own `message`.
 */
export function detailToMessage(detail, fallback = 'Request failed') {
  if (typeof detail === 'string' && detail) return detail
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message
    if (typeof detail.msg === 'string') return detail.msg
    return JSON.stringify(detail)
  }
  return fallback
}

/** True when an error was raised by a plan entitlement gate (upgrade prompt). */
export function isEntitlementError(err) {
  return Boolean(err?.detail && ENTITLEMENT_CODES.has(err.detail.code))
}

/**
 * Build an ApiError from a non-OK response whose body has already been read
 * as JSON (or failed to parse). Keeps the structured detail on `err.detail`.
 */
export function apiErrorFromBody(body, status, fallback) {
  const detail = body?.detail
  return new ApiError(detailToMessage(detail, fallback), status, typeof detail === 'object' ? detail : null)
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

export function createFetchSignal(timeoutMs = FETCH_TIMEOUT_MS) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  return {
    signal: controller.signal,
    clear: () => clearTimeout(timeoutId),
  }
}

export async function parseResponseError(response) {
  let detail = response.statusText || `Request failed (${response.status})`
  let structured = null
  try {
    const text = await response.text()
    if (text) {
      try {
        const body = JSON.parse(text)
        if (body.detail != null) {
          detail = detailToMessage(body.detail, detail)
          if (typeof body.detail === 'object') structured = body.detail
        } else detail = text
      } catch {
        detail = text
      }
    }
  } catch {
    // Keep statusText fallback.
  }
  return new ApiError(detail, response.status, structured)
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

