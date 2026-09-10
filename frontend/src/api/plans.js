import { API_URL, apiFetch } from './config'

export async function fetchPlans() {
  const res = await apiFetch(`${API_URL}/plans`)
  if (!res.ok) throw new Error('plans fetch failed')
  const data = await res.json()
  return data.plans
}

export async function createPreCheckout(payload) {
  const res = await apiFetch(`${API_URL}/subscriptions/pre-checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to create checkout')
  }
  return res.json()
}
