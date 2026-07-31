import { API_URL, apiFetch, authHeaders, fetchJson } from './config'

export async function fetchProductions(cooperativeId = null, productionKind = null) {
  const params = new URLSearchParams({ limit: '100' })
  if (cooperativeId) params.set('cooperative_id', cooperativeId)
  if (productionKind) params.set('production_kind', productionKind)
  const qs = `?${params.toString()}`
  return fetchJson(`${API_URL}/production/${qs}`, {
    headers: authHeaders(),
  })
}

export function buildProductionPayload(values) {
  return {
    farmer_id: parseInt(values.farmerId, 10),
    production_kind: values.productionKind,
    product_name: values.productName.trim(),
    activity: values.activity,
    unit: values.unit,
    expected_quantity: parseFloat(values.expectedQuantity),
    quantity: parseFloat(values.quantity),
    production_date: values.productionDate,
  }
}

export async function logProduction(values) {
  const res = await apiFetch(`${API_URL}/production/`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(buildProductionPayload(values)),
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to log production')
  }

  return res.json()
}
