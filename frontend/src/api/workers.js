import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchWorkers(cooperativeId) {
  if (!cooperativeId) return []
  const res = await apiFetch(`${API_URL}/workers/?cooperative_id=${cooperativeId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to load workers')
  }
  return res.json()
}

export async function createWorker(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/workers/?cooperative_id=${cooperativeId}`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to create worker')
  }
  return res.json()
}

export async function updateWorker(cooperativeId, workerId, data) {
  const res = await apiFetch(`${API_URL}/workers/${workerId}?cooperative_id=${cooperativeId}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to update worker')
  }
  return res.json()
}

export async function deleteWorker(cooperativeId, workerId) {
  const res = await apiFetch(`${API_URL}/workers/${workerId}?cooperative_id=${cooperativeId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to deactivate worker')
  }
  return true
}
