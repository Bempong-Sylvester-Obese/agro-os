

const API_URL = import.meta.env.VITE_API_URL || 'https://previewbackendagro-os.onrender.com'
const FETCH_TIMEOUT_MS = 10000

export async function fetchAgroAiDashboard() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  const token = localStorage.getItem('agro_os_token')
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
  const fetchOptions = { signal: controller.signal, headers }

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
  } catch (error) {
    console.error('Failed to fetch from real API:', error)
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}
