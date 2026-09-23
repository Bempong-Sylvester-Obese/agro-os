import { API_URL, apiErrorFromBody, apiFetch, authHeaders, fetchJson } from './config'

/**
 * Fetch all farmers, optionally filtered to a specific cooperative.
 */
export async function fetchFarmers(
  cooperativeId = null,
  productionFocus = null,
  skip = 0,
  limit = 100,
) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
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
    throw apiErrorFromBody(err, res.status, 'Failed to create farmer')
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

/** Recent meeting attendance records for one member (`GET /farmers/{id}/attendance`). */
export async function fetchFarmerAttendance(farmerId, cooperativeId, { limit = 5 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cooperativeId != null) params.set('cooperative_id', String(cooperativeId))
  return fetchJson(`${API_URL}/farmers/${farmerId}/attendance?${params}`, { headers: authHeaders() })
}

/**
 * Recent attendance across a set of members, newest first. One request per
 * member (the API is per-farmer); failures for an individual member surface as
 * a rejected promise so the caller can show a real error state.
 */
export async function fetchCooperativeAttendance(cooperativeId, farmerIds, { limit = 5 } = {}) {
  const ids = (farmerIds || []).filter((id) => id != null)
  if (ids.length === 0) return []
  const perMember = await Promise.all(ids.map((id) => fetchFarmerAttendance(id, cooperativeId, { limit })))
  return perMember.flat().sort((a, b) => {
    const dateA = a.event_date || a.date || ''
    const dateB = b.event_date || b.date || ''
    return dateB.localeCompare(dateA)
  })
}

/**
 * Record one member's attendance for a meeting
 * (`POST /farmers/{id}/attendance`). Feeds the Trust Score attendance factor.
 */
export async function recordFarmerAttendance(farmerId, cooperativeId, { eventName, eventDate, attended }) {
  const params = cooperativeId != null ? `?cooperative_id=${encodeURIComponent(cooperativeId)}` : ''
  return fetchJson(`${API_URL}/farmers/${farmerId}/attendance${params}`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      cooperative_id: cooperativeId,
      farmer_id: farmerId,
      event_name: eventName,
      event_date: eventDate,
      attended,
    }),
  })
}

/**
 * Record a whole meeting: one attendance row per member in `attendanceMap`
 * (`{ [farmerId]: attended }`). Returns `{ recorded, present }` counts.
 */
export async function recordMeetingAttendance(cooperativeId, attendanceMap, { eventName, eventDate }) {
  const entries = Object.entries(attendanceMap || {})
  await Promise.all(entries.map(([farmerId, attended]) =>
    recordFarmerAttendance(Number(farmerId), cooperativeId, { eventName, eventDate, attended: Boolean(attended) }),
  ))
  return {
    recorded: entries.length,
    present: entries.filter(([, attended]) => attended).length,
  }
}
