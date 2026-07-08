/**
 * API client configuration.
 *
 * Policy: prefer live backend data when the API is reachable. On timeout, network
 * errors, or non-2xx responses, API modules return demo fallback payloads with
 * source: 'demo' so the dashboard stays usable offline or during outages.
 * We do not fail closed in production.
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const FETCH_TIMEOUT_MS = 10000
export const DEFAULT_COOP_ID = import.meta.env.VITE_COOPERATIVE_ID

export function apiResult(source, data) {
  return { ...data, source: source === 'api' ? 'api' : 'demo' }
}

/**
 * Resolve a fetch attempt with optional demo fallback (default: always fallback).
 */
export async function withDemoFallback(fetchLive, getDemo, { fallback = true } = {}) {
  try {
    return await fetchLive()
  } catch (err) {
    if (!fallback) throw err
    return getDemo()
  }
}
