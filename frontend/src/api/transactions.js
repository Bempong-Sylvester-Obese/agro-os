import { API_URL, apiFetch, authHeaders, fetchJson } from './config'

export async function fetchTransactions(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''
  return fetchJson(`${API_URL}/transactions/${qs}`, {
    headers: authHeaders(),
  })
}

export async function collectDues(farmerId, amount, channel, description, otpCode = null, externalRef = null) {
  const res = await apiFetch(`${API_URL}/transactions/dues/collect`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      farmer_id: parseInt(farmerId, 10),
      amount: parseFloat(amount),
      channel,
      description,
      otp_code: otpCode,
      external_ref: externalRef
    })
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to initiate payment')
  }
  return res.json()
}

export async function verifyDuesCollect(transactionId, otpCode) {
  const res = await apiFetch(`${API_URL}/transactions/dues/collect/verify`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      transaction_id: parseInt(transactionId, 10),
      otp_code: otpCode,
    }),
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to verify OTP')
  }
  return res.json()
}

export async function reconcileTransaction(transactionId) {
  const res = await apiFetch(`${API_URL}/transactions/${transactionId}/reconcile`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to reconcile payment')
  }
  return res.json()
}

export async function fetchTransactionReceipt(transactionId) {
  const res = await apiFetch(`${API_URL}/transactions/${transactionId}/receipt`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to generate receipt')
  }
  return res.json()
}
