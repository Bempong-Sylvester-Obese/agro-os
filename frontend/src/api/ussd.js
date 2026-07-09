import { API_URL, apiResult, fetchJson, withDemoFallback } from './config'

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

export function fetchUssdLogs() {
  return withDemoFallback(
    async () => apiResult('api', { logs: await fetchJson(`${API_URL}/webhooks/ussd/logs`) }),
    () => apiResult('demo', { logs: DEMO_USSD }),
  )
}

export function simulatePaymentWebhook({ transactionId, moolreReference }) {
  return fetchJson(`${API_URL}/webhooks/moolre/payment/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      transaction_id: transactionId ?? undefined,
      moolre_reference: moolreReference ?? undefined,
    }),
  })
}
