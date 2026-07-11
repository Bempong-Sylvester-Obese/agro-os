import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchLoans(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''

  try {
    const res = await apiFetch(`${API_URL}/loans/${qs}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Loans API unavailable')
    return await res.json()
  } catch (error) {
    console.error('Failed to fetch loans:', error)
    return []
  }
}

export async function createLoan(farmerId, amount, purpose, repaymentDate) {
  const res = await apiFetch(`${API_URL}/loans/`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      farmer_id: parseInt(farmerId, 10),
      amount: parseFloat(amount),
      purpose,
      repayment_date: repaymentDate
    })
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to request loan')
  }
  return res.json()
}

export async function approveLoan(loanId) {
  const email = localStorage.getItem('agro_os_email') || 'admin'
  const res = await apiFetch(`${API_URL}/loans/${loanId}/approve`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ approved_by: email })
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to approve loan')
  }
  return res.json()
}

export async function rejectLoan(loanId) {
  const res = await apiFetch(`${API_URL}/loans/${loanId}/reject`, {
    method: 'POST',
    headers: authHeaders()
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to reject loan')
  }
  return res.json()
}

export async function disburseLoan(loanId) {
  const res = await apiFetch(`${API_URL}/loans/${loanId}/disburse`, {
    method: 'POST',
    headers: authHeaders()
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to disburse loan')
  }
  return res.json()
}
