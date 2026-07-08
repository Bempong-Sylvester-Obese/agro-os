const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

const DEMO_USSD = [
  {
    id: 1,
    phone: '+233552341234',
    input_path: '2',
    response_text: 'Dial *203*AgroOS# to pay your dues via mobile money. Thank you!',
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    phone: '+233552341234',
    input_path: '5',
    response_text: 'Farmer: Abena Mensah\nTrust Score: 58.0/100\nStatus: Active',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
]

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

export async function fetchUssdLogs() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/webhooks/ussd/logs`, {
      signal: controller.signal,
    })
    if (!response.ok) throw new Error('USSD logs unavailable')
    return { logs: await response.json(), source: 'api' }
  } catch {
    return { logs: DEMO_USSD, source: 'demo' }
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function simulatePaymentWebhook({ transactionId, moolreReference }) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/webhooks/moolre/payment/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        transaction_id: transactionId ?? undefined,
        moolre_reference: moolreReference ?? undefined,
      }),
    })
    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || 'Simulation failed')
    }
    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}
