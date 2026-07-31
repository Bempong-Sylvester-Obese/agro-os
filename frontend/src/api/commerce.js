import { API_URL, apiFetch, authHeaders, fetchJson, parseResponseError } from './config'

const RESOURCE_KEYS = ['items', 'results', 'records', 'data']

export function commerceRecords(payload, resource) {
  if (Array.isArray(payload)) return payload
  if (!payload || typeof payload !== 'object') return []
  const queue = [payload]
  const visited = new Set()
  while (queue.length) {
    const current = queue.shift()
    if (!current || typeof current !== 'object' || visited.has(current)) continue
    visited.add(current)
    for (const key of [resource, ...RESOURCE_KEYS]) {
      if (Array.isArray(current[key])) return current[key]
      if (current[key] && typeof current[key] === 'object') queue.push(current[key])
    }
  }
  return []
}

function query(cooperativeId) {
  const params = new URLSearchParams({ limit: '100' })
  if (cooperativeId) params.set('cooperative_id', cooperativeId)
  return `?${params}`
}

async function list(resource, cooperativeId) {
  const payload = await fetchJson(`${API_URL}/${resource}/${query(cooperativeId)}`, {
    headers: authHeaders(),
  })
  return commerceRecords(payload, resource)
}

async function mutate(resource, { method = 'POST', body } = {}) {
  const response = await apiFetch(`${API_URL}/${resource}`, {
    method,
    headers: authHeaders(body !== undefined),
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  })
  if (!response.ok) throw await parseResponseError(response)
  if (response.status === 204) return null
  return response.json()
}

export const fetchIntake = cooperativeId => list('intakes', cooperativeId)
export const createIntake = values => mutate('intakes/', { body: values })
export const cancelIntake = id => mutate(`intakes/${id}/cancel`)
export const acceptIntake = (id, values) => mutate(`intakes/${id}/accept`, { body: values })
export const rejectIntake = (id, reason) => mutate(`intakes/${id}/reject`, {
  body: { reason },
})
export const assignIntake = (id, aggregationBatchId) => mutate(`aggregation-batches/${aggregationBatchId}/intakes`, {
  body: { intake_ids: [Number(id)] },
})

export const fetchAggregation = cooperativeId => list('aggregation-batches', cooperativeId)
export const createAggregation = values => mutate('aggregation-batches/', { body: values })
export const closeAggregation = id => mutate(`aggregation-batches/${id}/close`)

export const fetchBuyers = cooperativeId => list('buyers', cooperativeId)
export const createBuyer = values => mutate('buyers/', { body: values })

export async function fetchSaleReceipts(saleId) {
  const payload = await fetchJson(`${API_URL}/sales/${saleId}/receipts`, { headers: authHeaders() })
  return commerceRecords(payload, 'receipts')
}

export async function fetchSales(cooperativeId) {
  const sales = await list('sales', cooperativeId)
  return Promise.all(sales.map(async sale => ({
    ...sale,
    receipts: await fetchSaleReceipts(sale.id),
  })))
}
export const createSale = values => mutate('sales/', { body: values })
export const confirmSale = id => mutate(`sales/${id}/confirm`)
export const recordSaleReceipt = (id, values) => mutate(`sales/${id}/receipts`, { body: values })
export const verifySaleReceipt = (saleId, receiptId) => mutate(`sales/${saleId}/receipts/${receiptId}/verify`)

export const fetchSettlements = cooperativeId => list('settlements', cooperativeId)
export const calculateSettlement = (saleId, values = {}) => mutate(`settlements/sales/${saleId}/calculate`, { body: values })
export const reviewSettlement = id => mutate(`settlements/${id}/submit`)
export const approveSettlement = id => mutate(`settlements/${id}/approve`)
export const paySettlement = id => mutate(`settlements/${id}/disburse`)
export const retrySettlement = id => mutate(`settlements/${id}/retry-failed`)
