const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000
const DEFAULT_COOP_ID = import.meta.env.VITE_COOPERATIVE_ID

async function apiFetch(path, options = {}) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || `Request failed: ${response.status}`)
    }

    if (response.status === 204) return null
    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function resolveCooperativeId() {
  if (DEFAULT_COOP_ID) return Number(DEFAULT_COOP_ID)

  const coops = await apiFetch('/cooperatives/')
  if (!coops?.length) throw new Error('No cooperative found')
  return coops[0].id
}

export async function fetchFarmers(cooperativeId) {
  const params = new URLSearchParams()
  if (cooperativeId) params.set('cooperative_id', cooperativeId)
  const qs = params.toString()
  return apiFetch(`/farmers/${qs ? `?${qs}` : ''}`)
}

export async function fetchCommunicationLogs(cooperativeId) {
  const params = new URLSearchParams()
  if (cooperativeId) params.set('cooperative_id', cooperativeId)
  const qs = params.toString()
  return apiFetch(`/communications/logs${qs ? `?${qs}` : ''}`)
}

export async function sendSmsBroadcast({ cooperativeId, message, sentBy }) {
  return apiFetch('/communications/sms/broadcast', {
    method: 'POST',
    body: JSON.stringify({
      cooperative_id: cooperativeId,
      message,
      sent_by: sentBy ?? undefined,
    }),
  })
}

export async function sendDuesReminder({ cooperativeId, amount, dueDate, sentBy }) {
  return apiFetch('/communications/sms/dues-reminder', {
    method: 'POST',
    body: JSON.stringify({
      cooperative_id: cooperativeId,
      amount,
      due_date: dueDate,
      sent_by: sentBy ?? undefined,
    }),
  })
}
