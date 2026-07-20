import { API_URL, apiFetch, authHeaders } from './config'

/**
 * Fetch a cooperative by ID. Returns null on any error.
 */
export async function fetchCooperative(cooperativeId) {
  if (!cooperativeId) return null
  const res = await apiFetch(`${API_URL}/cooperatives/${cooperativeId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}

export async function updateCooperative(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/cooperatives/${cooperativeId}`, {
    method: 'PUT',
    headers: authHeaders(true),
    body: JSON.stringify(data)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to update cooperative')
  }
  return res.json()
}

export async function provisionWallet(cooperativeId) {
  const res = await apiFetch(`${API_URL}/cooperatives/${cooperativeId}/wallet/provision`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to provision wallet')
  }
  return res.json()
}

export async function createSubscriptionCheckout(cooperativeId, planKey) {
  const res = await apiFetch(`${API_URL}/subscriptions/checkout`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      cooperative_id: cooperativeId,
      plan_key: planKey
    })
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to generate checkout link')
  }
  return res.json()
}
