import { MEMBERS_SEED } from '../data/payments'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

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
