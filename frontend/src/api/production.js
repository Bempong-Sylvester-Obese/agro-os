import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchProductions(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''

  try {
    const res = await apiFetch(`${API_URL}/production/${qs}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Production API unavailable')
    return await res.json()
  } catch (error) {
    console.error('Failed to fetch production logs:', error)
    return []
  }
}

export async function logProduction(farmerId, cropType, acreage, yieldAmount, harvestDate) {
  const res = await apiFetch(`${API_URL}/production/`, {
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
