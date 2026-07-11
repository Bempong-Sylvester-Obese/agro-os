const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

function authHeaders(json = false) {
  const token = localStorage.getItem('agro_os_token')
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/**
 * Fetch sent SMS logs, optionally scoped to a cooperative.
 */
export async function fetchSMSLogs(cooperativeId = null) {
  const controller = new AbortController()
  const timeoutId  = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}&limit=50` : '?limit=50'
  try {
    const res = await fetch(`${API_URL}/communications/logs${qs}`, {
      headers: authHeaders(),
      signal: controller.signal,
    })
    if (!res.ok) throw new Error('Communications API unavailable')
    return await res.json()
  } catch (error) {
    console.error('Failed to fetch SMS logs:', error)
    return []
  } finally {
    clearTimeout(timeoutId)
  }
}

/**
 * Send a bulk SMS broadcast to all active members of a cooperative.
 * @param {number} cooperativeId
 * @param {string} message  - max 160 chars
 */
export async function sendBroadcast(cooperativeId, message) {
  const res = await fetch(`${API_URL}/communications/sms/broadcast`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ cooperative_id: cooperativeId, message }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to send broadcast')
  }
  return res.json()
}
