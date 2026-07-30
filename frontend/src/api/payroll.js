import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchPayrollSummary(cooperativeId, periodStart, periodEnd) {
  if (!cooperativeId) return null
  const res = await apiFetch(
    `${API_URL}/payroll/summary?cooperative_id=${cooperativeId}&period_start=${periodStart}&period_end=${periodEnd}`,
    { headers: authHeaders() },
  )
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load payroll summary') }
  return res.json()
}

export async function approvePayroll(cooperativeId, periodStart, periodEnd) {
  const res = await apiFetch(`${API_URL}/payroll/approve?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify({ period_start: periodStart, period_end: periodEnd }),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to approve payroll') }
  return res.json()
}

export async function disbursePayroll(cooperativeId, periodStart, periodEnd) {
  const res = await apiFetch(`${API_URL}/payroll/disburse?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify({ period_start: periodStart, period_end: periodEnd }),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to disburse payroll') }
  return res.json()
}

export async function fetchPayrollHistory(cooperativeId) {
  if (!cooperativeId) return []
  const res = await apiFetch(`${API_URL}/payroll/history?cooperative_id=${cooperativeId}`, { headers: authHeaders() })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load payroll history') }
  return res.json()
}
