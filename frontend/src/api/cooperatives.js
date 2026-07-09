import { API_URL, apiResult, fetchJson, withDemoFallback } from './config'

const DEMO_COOPERATIVE = {
  id: 1,
  name: 'Kuapa Kokoo Demo Cooperative',
  location: 'Kumasi, Ashanti Region',
  currency: 'GHS',
  moolre_account_number: 'DEMO-WALLET-001',
}

export function fetchCooperatives() {
  return withDemoFallback(
    async () => apiResult('api', { cooperatives: await fetchJson(`${API_URL}/cooperatives/`) }),
    () => apiResult('demo', { cooperatives: [DEMO_COOPERATIVE] }),
  )
}

export function fetchCooperative(id) {
  return withDemoFallback(
    async () => apiResult('api', { cooperative: await fetchJson(`${API_URL}/cooperatives/${id}`) }),
    () => apiResult('demo', { cooperative: DEMO_COOPERATIVE }),
  )
}
