const API_URL = import.meta.env.VITE_API_URL || 'https://previewbackendagro-os.onrender.com'
const FETCH_TIMEOUT_MS = 10000

export async function fetchTransactions(cooperativeId = null) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  const token = localStorage.getItem('agro_os_token')
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
  const fetchOptions = { signal: controller.signal, headers }

  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''

  try {
    const response = await fetch(`${API_URL}/transactions/${qs}`, fetchOptions)
    if (!response.ok) {
      throw new Error('Transactions API unavailable')
    }
    return await response.json()
  } catch (error) {
    console.error('Failed to fetch transactions:', error)
    return []
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function collectDues(farmerId, amount, channel, description, otpCode = null, externalRef = null) {
  const token = localStorage.getItem('agro_os_token')
  const res = await fetch(`${API_URL}/transactions/dues/collect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
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
