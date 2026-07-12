import { API_URL, apiFetch, authHeaders } from './config'

/**
 * Fetch sent SMS logs, optionally scoped to a cooperative.
 */
export async function fetchSMSLogs(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}&limit=50` : '?limit=50'
  try {
    const res = await apiFetch(`${API_URL}/communications/logs${qs}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Communications API unavailable')
    return await res.json()
  } catch (error) {
    console.error('Failed to fetch SMS logs:', error)
    return []
  }
}

/**
 * Send a bulk SMS broadcast to all active members of a cooperative.
 * @param {number} cooperativeId
 * @param {string} message  - max 160 chars
 */
export async function sendBroadcast(cooperativeId, message) {
  const res = await apiFetch(`${API_URL}/communications/sms/broadcast`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ cooperative_id: cooperativeId, message }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail
    throw new Error(
      typeof detail === 'string' ? detail : 'Failed to send broadcast'
    )
  }
  const data = await res.json()
  if (data.status !== 'success') {
    throw new Error(data.message || 'Failed to send broadcast')
  }
  return data
}
