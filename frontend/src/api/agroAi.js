import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchAgroAiDashboard() {
  const fetchOptions = { headers: authHeaders() }

  try {
    const [farmersResponse, summaryResponse] = await Promise.all([
      apiFetch(`${API_URL}/api/farmers`, fetchOptions),
      apiFetch(`${API_URL}/api/agro-ai/credit-summary`, fetchOptions),
    ])

    if (!farmersResponse.ok || !summaryResponse.ok) {
      throw new Error('agro-ai API unavailable')
    }

    return {
      farmers: await farmersResponse.json(),
      summary: await summaryResponse.json(),
      source: 'api',
    }
  } catch (error) {
    console.error('Failed to fetch from real API:', error)
    throw error
  }
}
