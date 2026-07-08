import { CREDIT_SUMMARY, FARMER_ASSESSMENTS } from '../data/payments'
import { API_URL, apiResult, fetchJson, withDemoFallback } from './config'

export function fetchAgroAiDashboard() {
  return withDemoFallback(
    async () => {
      const [farmers, summary] = await Promise.all([
        fetchJson(`${API_URL}/api/farmers`),
        fetchJson(`${API_URL}/api/agro-ai/credit-summary`),
      ])
      return apiResult('api', { farmers, summary })
    },
    () => apiResult('demo', { farmers: FARMER_ASSESSMENTS, summary: CREDIT_SUMMARY }),
  )
}
