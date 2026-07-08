import { MEMBERS_SEED } from '../data/payments'
import { authHeaders } from './auth'
import { API_URL, ApiError, apiResult, fetchJson, withDemoFallback } from './config'

const DEFAULT_COOP_ID = import.meta.env.VITE_COOPERATIVE_ID

export const DB_FARMERS_FALLBACK = MEMBERS_SEED.map((member, index) => ({
  id: index + 1,
  name: member.name,
  phone: member.phone,
  location: member.region,
  crop_type: null,
  cooperative_id: 1,
  membership_status: 'active',
  trust_score: parseFloat(member.score, 10),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}))

export function fetchFarmers() {
  return withDemoFallback(
    async () => apiResult('api', { farmers: await fetchJson(`${API_URL}/farmers/`) }),
    () => apiResult('demo', { farmers: DB_FARMERS_FALLBACK }),
  )
}

export async function createFarmer(payload) {
  return fetchJson(`${API_URL}/farmers/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  })
}

export async function recalculateTrustScore(farmerId) {
  return fetchJson(`${API_URL}/farmers/${farmerId}/recalculate-trust-score`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
  })
}

export function resolveCooperativeIdForFarmers() {
  if (DEFAULT_COOP_ID) return Promise.resolve(Number(DEFAULT_COOP_ID))

  return withDemoFallback(
    async () => {
      const coops = await fetchJson(`${API_URL}/cooperatives/`)
      if (!coops?.length) throw new ApiError('No cooperative found', 404)
      return coops[0].id
    },
    () => 1,
  )
}
