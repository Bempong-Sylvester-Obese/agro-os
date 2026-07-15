import { API_URL, apiFetch, authHeaders, fetchJson } from './config'

export async function fetchTransactions(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''
  return fetchJson(`${API_URL}/transactions/${qs}`, {
    headers: authHeaders(),
  })
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
