import { CREDIT_SUMMARY, FARMER_ASSESSMENTS } from '../data/payments'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

export async function fetchAgroAiDashboard() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  const fetchOptions = { signal: controller.signal }

  try {
    const [farmersResponse, summaryResponse] = await Promise.all([
      fetch(`${API_URL}/api/farmers`, fetchOptions),
      fetch(`${API_URL}/api/agro-ai/credit-summary`, fetchOptions),
    ])

    if (!farmersResponse.ok || !summaryResponse.ok) {
      throw new Error('agro-ai API unavailable')
    }

    return {
      farmers: await farmersResponse.json(),
      summary: await summaryResponse.json(),
      source: 'api',
    }
  } catch {
    return {
      farmers: FARMER_ASSESSMENTS,
      summary: CREDIT_SUMMARY,
      source: 'demo',
    }
  } finally {
    clearTimeout(timeoutId)
  }
}
