import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchFarmProductions(cooperativeId) {
  if (!cooperativeId) return []
  const url = `${API_URL}/production/farm/?cooperative_id=${cooperativeId}`
  const res = await apiFetch(url, { headers: authHeaders() })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load farm productions') }
  return res.json()
}

export async function createFarmProduction(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/production/farm/?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to create farm production') }
  return res.json()
}

export async function updateFarmProduction(cooperativeId, id, data) {
  const res = await apiFetch(`${API_URL}/production/farm/${id}?cooperative_id=${cooperativeId}`, {
    method: 'PATCH', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to update farm production') }
  return res.json()
}
