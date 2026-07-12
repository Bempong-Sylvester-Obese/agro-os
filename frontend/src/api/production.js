import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchProductions(cooperativeId = null) {
  const qs = cooperativeId ? `?cooperative_id=${cooperativeId}&limit=100` : '?limit=100'

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

export async function logProduction(farmerId, cropType, expectedKg, quantityKg, harvestDate) {
  const res = await apiFetch(`${API_URL}/production/`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      farmer_id: parseInt(farmerId, 10),
      crop_type: cropType,
      expected_kg: parseFloat(expectedKg),
      quantity_kg: parseFloat(quantityKg),
    }),
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to log production')
  }

  const record = await res.json()

  if (harvestDate) {
    const updateRes = await apiFetch(`${API_URL}/production/${record.id}`, {
      method: 'PUT',
      headers: authHeaders(true),
      body: JSON.stringify({ harvest_date: harvestDate }),
    })
    if (!updateRes.ok) {
      const data = await updateRes.json().catch(() => ({}))
      throw new Error(data.detail || 'Production saved but harvest date could not be set')
    }
    return updateRes.json()
  }

  return record
}
