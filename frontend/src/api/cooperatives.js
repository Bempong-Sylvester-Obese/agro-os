const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

export async function fetchCooperatives() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/cooperatives/`, { signal: controller.signal })
    if (!response.ok) throw new Error('cooperatives API unavailable')
    return { cooperatives: await response.json(), source: 'api' }
  } catch {
    return {
      cooperatives: [{
        id: 1,
        name: 'Kuapa Kokoo Demo Cooperative',
        location: 'Kumasi, Ashanti Region',
        currency: 'GHS',
        moolre_account_number: 'DEMO-WALLET-001',
      }],
      source: 'demo',
    }
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function fetchCooperative(id) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/cooperatives/${id}`, { signal: controller.signal })
    if (!response.ok) throw new Error('cooperative not found')
    return { cooperative: await response.json(), source: 'api' }
  } catch {
    const fallback = (await fetchCooperatives()).cooperatives[0]
    return { cooperative: fallback, source: 'demo' }
  } finally {
    clearTimeout(timeoutId)
  }
}
