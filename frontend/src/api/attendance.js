import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchAttendance(cooperativeId, filters = {}) {
  if (!cooperativeId) return []
  let url = `${API_URL}/attendance/?cooperative_id=${cooperativeId}`
  if (filters.worker_id) url += `&worker_id=${filters.worker_id}`
  if (filters.date_from) url += `&date_from=${filters.date_from}`
  if (filters.date_to) url += `&date_to=${filters.date_to}`
  const res = await apiFetch(url, { headers: authHeaders() })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load attendance') }
  return res.json()
}

export async function logAttendance(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/attendance/?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to log attendance') }
  return res.json()
}

export async function fetchAttendanceSummary(cooperativeId, periodStart, periodEnd) {
  const res = await apiFetch(
    `${API_URL}/attendance/summary?cooperative_id=${cooperativeId}&period_start=${periodStart}&period_end=${periodEnd}`,
    { headers: authHeaders() },
  )
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load summary') }
  return res.json()
}
