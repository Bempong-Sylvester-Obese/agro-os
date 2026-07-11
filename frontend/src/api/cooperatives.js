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
