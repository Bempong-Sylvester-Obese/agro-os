const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

function authHeaders(json = false) {
  const token = localStorage.getItem('agro_os_token')
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  }
}

export async function fetchProductions(cooperativeId = null) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''

  try {
    const res = await fetch(`${API_URL}/production/${qs}`, {
      headers: authHeaders(),
      signal: controller.signal
    })
    if (!res.ok) throw new Error('Production API unavailable')
    return await res.json()
  } catch (error) {
    console.error('Failed to fetch production logs:', error)
    return []
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function logProduction(farmerId, cropType, acreage, yieldAmount, harvestDate) {
  const res = await fetch(`${API_URL}/production/`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      farmer_id: parseInt(farmerId, 10),
      crop_type: cropType,
      acreage: parseFloat(acreage),
      yield_amount: parseFloat(yieldAmount),
      harvest_date: harvestDate
    })
  })
  
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to log production')
  }
  return res.json()
}
