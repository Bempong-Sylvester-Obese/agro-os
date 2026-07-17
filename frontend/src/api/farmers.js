import { API_URL, apiFetch, authHeaders } from './config'

/**
 * Fetch all farmers, optionally filtered to a specific cooperative.
 */
export async function fetchFarmers(cooperativeId = null, productionFocus = null) {
  const params = new URLSearchParams({ limit: '100' })
  if (cooperativeId) params.set('cooperative_id', cooperativeId)
  if (productionFocus) params.set('production_focus', productionFocus)
  const qs = `?${params.toString()}`
  const res = await apiFetch(`${API_URL}/farmers/${qs}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch farmers')
  return res.json()
}

/**
 * Create a farmer identity or attach an existing identity to a cooperative.
 * The returned `id` is the cooperative membership ID; `farmer_id` is global.
 * @param {object} data - Member identity plus crop/animal production profile.
 */
export async function createFarmer(data) {
  const res = await apiFetch(`${API_URL}/farmers/`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to create farmer')
  }
  return res.json()
}

export async function updateFarmer(farmerId, updates) {
  const res = await apiFetch(`${API_URL}/farmers/${farmerId}`, {
    method: 'PUT',
    headers: authHeaders(true),
    body: JSON.stringify(updates),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to update member')
  }
  return res.json()
}

export async function deactivateFarmer(farmerId) {
  const res = await apiFetch(`${API_URL}/farmers/${farmerId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to deactivate member')
  }
}

/**
 * Fetch the most recent trust score breakdown for a farmer.
 * Returns null if no score has been calculated yet.
 */
export async function fetchFarmerTrustScore(farmerId) {
  const res = await apiFetch(`${API_URL}/farmers/${farmerId}/trust-score`, {
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}

/**
 * Trigger a server-side trust score recalculation for a farmer.
 */
export async function recalculateTrustScore(farmerId) {
  const res = await apiFetch(`${API_URL}/farmers/${farmerId}/recalculate-trust-score`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}
