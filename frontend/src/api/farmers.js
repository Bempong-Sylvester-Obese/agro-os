const API_URL = import.meta.env.VITE_API_URL || 'https://previewbackendagro-os.onrender.com'

function authHeaders() {
  const token = localStorage.getItem('agro_os_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/**
 * Fetch all farmers, optionally filtered to a specific cooperative.
 */
export async function fetchFarmers(cooperativeId = null) {
  const qs = cooperativeId
    ? `?cooperative_id=${cooperativeId}&limit=500`
    : '?limit=500'
  const res = await fetch(`${API_URL}/farmers/${qs}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch farmers')
  return res.json()
}

/**
 * Register a new farmer / cooperative member.
 * @param {object} data - { name, phone, cooperative_id, email?, location?, crop_type?, acreage? }
 */
export async function createFarmer(data) {
  const res = await fetch(`${API_URL}/farmers/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to create farmer')
  }
  return res.json()
}

/**
 * Fetch the most recent trust score breakdown for a farmer.
 * Returns null if no score has been calculated yet.
 */
export async function fetchFarmerTrustScore(farmerId) {
  const res = await fetch(`${API_URL}/farmers/${farmerId}/trust-score`, {
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}

/**
 * Trigger a server-side trust score recalculation for a farmer.
 */
export async function recalculateTrustScore(farmerId) {
  const res = await fetch(`${API_URL}/farmers/${farmerId}/recalculate-trust-score`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}
