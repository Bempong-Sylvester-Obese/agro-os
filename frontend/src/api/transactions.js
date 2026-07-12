import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchTransactions(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''

  try {
    const response = await apiFetch(`${API_URL}/transactions/${qs}`, {
      headers: authHeaders(),
    })
    if (!response.ok) {
      throw new Error('Transactions API unavailable')
    }
    return await response.json()
  } catch (error) {
    console.error('Failed to fetch transactions:', error)
    return []
  }
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
