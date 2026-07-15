import { API_URL, apiFetch, authHeaders, createFetchSignal, fetchJson, formatTransportError, MUTATION_TIMEOUT_MS } from './config'

export async function fetchLoans(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''
  return fetchJson(`${API_URL}/loans/${qs}`, {
    headers: authHeaders(),
  })
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
  const { signal, clear } = createFetchSignal(MUTATION_TIMEOUT_MS)
  try {
    const res = await apiFetch(`${API_URL}/loans/${loanId}/disburse`, {
      method: 'POST',
      headers: authHeaders(),
      signal,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      const detail = typeof data.detail === 'string' ? data.detail : null
      throw new Error(detail || 'Failed to disburse loan')
    }
    return res.json()
  } catch (err) {
    throw new Error(formatTransportError(err))
  } finally {
    clear()
  }
}

export async function cancelLoan(loanId, reason) {
  const res = await apiFetch(`${API_URL}/loans/${loanId}/cancel`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ reason: reason.trim() }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to cancel loan')
  }
  return res.json()
}

export async function fetchDisbursementStatus(loanId) {
  const res = await apiFetch(`${API_URL}/loans/${loanId}/disbursement-status`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to reconcile payout status')
  }
  return res.json()
}

export class RepaymentVerificationRequiredError extends Error {
  constructor(detail) {
    super(detail?.message || 'Enter the OTP sent to the member to verify repayment.')
    this.name = 'RepaymentVerificationRequiredError'
    this.transactionId = detail?.transaction_id
    this.loanId = detail?.loan_id
  }
}

export async function repayLoan(loanId) {
  const { signal, clear } = createFetchSignal(MUTATION_TIMEOUT_MS)
  try {
    const res = await apiFetch(`${API_URL}/loans/${loanId}/repay`, {
      method: 'POST',
      headers: authHeaders(),
      signal,
    })
    const data = await res.json().catch(() => ({}))
    if (res.status === 428 && data.detail && typeof data.detail === 'object') {
      throw new RepaymentVerificationRequiredError(data.detail)
    }
    if (!res.ok) {
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to start repayment')
    }
    return data
  } catch (err) {
    if (err instanceof RepaymentVerificationRequiredError) throw err
    throw new Error(formatTransportError(err))
  } finally {
    clear()
  }
}

export async function verifyLoanRepayment(loanId, otpCode) {
  const { signal, clear } = createFetchSignal(MUTATION_TIMEOUT_MS)
  try {
    const res = await apiFetch(`${API_URL}/loans/${loanId}/repay/verify`, {
      method: 'POST',
      headers: authHeaders(true),
      body: JSON.stringify({ otp_code: otpCode.trim() }),
      signal,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to verify repayment')
    }
    return res.json()
  } catch (err) {
    throw new Error(formatTransportError(err))
  } finally {
    clear()
  }
}
