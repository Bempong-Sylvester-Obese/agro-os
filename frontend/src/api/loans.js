import { API_URL, apiFetch, authHeaders, createFetchSignal, fetchJson, formatTransportError, MUTATION_TIMEOUT_MS } from './config'

export async function fetchLoans(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''
  return fetchJson(`${API_URL}/loans/${qs}`, {
    headers: authHeaders(),
  })
}

export async function approveLoan(loanId) {
  const res = await apiFetch(`${API_URL}/loans/${loanId}/approve`, {
    method: 'POST',
    headers: authHeaders()
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
  const { signal, clear } = createFetchSignal(MUTATION_TIMEOUT_MS)
  try {
    const res = await apiFetch(`${API_URL}/loans/${loanId}/cancel`, {
      method: 'POST',
      headers: authHeaders(true),
      body: JSON.stringify({ reason: reason.trim() }),
      signal,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to cancel loan')
    }
    return res.json()
  } catch (err) {
    throw new Error(formatTransportError(err))
  } finally {
    clear()
  }
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

export async function repayLoan(loanId) {
  const { signal, clear } = createFetchSignal(MUTATION_TIMEOUT_MS)
  try {
    const res = await apiFetch(`${API_URL}/loans/${loanId}/repay`, {
      method: 'POST',
      headers: authHeaders(),
      signal,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to start repayment')
    }
    return data
  } catch (err) {
    throw new Error(formatTransportError(err))
  } finally {
    clear()
  }
}
