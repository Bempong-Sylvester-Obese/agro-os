import { MEMBERS_SEED } from '../data/payments'
import { authHeaders } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000
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

export async function fetchFarmers() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/farmers/`, { signal: controller.signal })

    if (!response.ok) {
      throw new Error('farmers API unavailable')
    }

    return {
      farmers: await response.json(),
      source: 'api',
    }
  } catch {
    return {
      farmers: DB_FARMERS_FALLBACK,
      source: 'demo',
    }
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function createFarmer(payload) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/farmers/`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || 'Failed to create farmer')
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function recalculateTrustScore(farmerId) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/farmers/${farmerId}/recalculate-trust-score`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || 'Could not recalculate trust score')
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function resolveCooperativeIdForFarmers() {
  if (DEFAULT_COOP_ID) return Number(DEFAULT_COOP_ID)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_URL}/cooperatives/`, { signal: controller.signal })
    if (!response.ok) throw new Error('No cooperative found')
    const coops = await response.json()
    if (!coops?.length) throw new Error('No cooperative found')
    return coops[0].id
  } catch {
    return 1
  } finally {
    clearTimeout(timeoutId)
  }
}
