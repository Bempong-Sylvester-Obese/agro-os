import { API_URL, authHeaders, fetchJson, formatTransportError } from './config'

export function formatUssdTime(isoDate) {
  if (!isoDate) return '—'
  const date = new Date(isoDate)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('en-GH', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Live USSD session log from the backend (no demo substitution in production). */
export async function fetchUssdLogs() {
  try {
    const logs = await fetchJson(`${API_URL}/webhooks/ussd/logs`, {
      headers: authHeaders(),
    })
    return { logs: logs || [], source: 'api' }
  } catch (err) {
    throw new Error(formatTransportError(err))
  }
}
