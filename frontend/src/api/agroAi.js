import { CREDIT_SUMMARY, FARMER_ASSESSMENTS } from '../data/payments'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchAgroAiDashboard() {
  try {
    const [farmersResponse, summaryResponse] = await Promise.all([
      fetch(`${API_URL}/api/farmers`),
      fetch(`${API_URL}/api/agro-ai/credit-summary`),
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
  }
}
