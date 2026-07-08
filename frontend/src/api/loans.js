import { API_URL, apiResult, fetchJson, withDemoFallback } from './config'

const DEMO_LOANS = [
  {
    id: 1,
    farmer_id: 1,
    amount: 500,
    currency: 'GHS',
    purpose: 'Fertiliser for cocoa farm',
    status: 'requested',
    approved_by: null,
    approved_at: null,
    moolre_transfer_ref: null,
    disbursed_at: null,
    repaid_at: null,
    created_at: '2026-06-01T10:00:00',
    updated_at: '2026-06-01T10:00:00',
  },
  {
    id: 2,
    farmer_id: 2,
    amount: 1200,
    currency: 'GHS',
    purpose: 'Seed inputs',
    status: 'approved',
    approved_by: 'Admin Kwame',
    approved_at: '2026-06-02T14:30:00',
    moolre_transfer_ref: null,
    disbursed_at: null,
    repaid_at: null,
    created_at: '2026-05-28T09:00:00',
    updated_at: '2026-06-02T14:30:00',
  },
  {
    id: 3,
    farmer_id: 3,
    amount: 800,
    currency: 'GHS',
    purpose: 'Harvest labour',
    status: 'disbursed',
    approved_by: 'Admin Kwame',
    approved_at: '2026-05-20T11:00:00',
    moolre_transfer_ref: 'DEMO-TRANSFER-001',
    disbursed_at: '2026-05-21T08:15:00',
    repaid_at: null,
    created_at: '2026-05-18T16:00:00',
    updated_at: '2026-05-21T08:15:00',
  },
]

const DEMO_FARMERS = [
  { id: 1, name: 'Abena Mensah', phone: '0552340001', location: 'Ashanti' },
  { id: 2, name: 'Kwame Asante', phone: '0248910002', location: 'Northern' },
  { id: 3, name: 'Ama Osei', phone: '0594410003', location: 'Gr. Accra' },
]

function apiFetch(path, options = {}) {
  return fetchJson(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
}

export function fetchLoansDashboard() {
  return withDemoFallback(
    async () => {
      const [loans, farmers] = await Promise.all([
        apiFetch('/loans/'),
        apiFetch('/farmers/'),
      ])
      return apiResult('api', { loans, farmers })
    },
    () => apiResult('demo', { loans: DEMO_LOANS, farmers: DEMO_FARMERS }),
  )
}

export function createLoan(payload) {
  return apiFetch('/loans/', { method: 'POST', body: JSON.stringify(payload) })
}

export function approveLoan(loanId, approvedBy) {
  return apiFetch(`/loans/${loanId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved_by: approvedBy }),
  })
}

export function rejectLoan(loanId) {
  return apiFetch(`/loans/${loanId}/reject`, { method: 'POST' })
}

export function disburseLoan(loanId) {
  return apiFetch(`/loans/${loanId}/disburse`, { method: 'POST' })
}

export function repayLoan(loanId) {
  return apiFetch(`/loans/${loanId}/repay`, { method: 'POST' })
}
