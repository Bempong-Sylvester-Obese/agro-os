import { API_URL, apiFetch, authHeaders } from './config'

export async function fetchTasks(cooperativeId, status) {
  if (!cooperativeId) return []
  let url = `${API_URL}/tasks/?cooperative_id=${cooperativeId}`
  if (status) url += `&status=${status}`
  const res = await apiFetch(url, { headers: authHeaders() })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to load tasks') }
  return res.json()
}

export async function createTask(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/tasks/?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to create task') }
  return res.json()
}

export async function updateTask(cooperativeId, taskId, data) {
  const res = await apiFetch(`${API_URL}/tasks/${taskId}?cooperative_id=${cooperativeId}`, {
    method: 'PATCH', headers: authHeaders(true), body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to update task') }
  return res.json()
}

export async function assignWorkers(cooperativeId, taskId, workerIds) {
  const res = await apiFetch(`${API_URL}/tasks/${taskId}/assign?cooperative_id=${cooperativeId}`, {
    method: 'POST', headers: authHeaders(true), body: JSON.stringify({ worker_ids: workerIds }),
  })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to assign workers') }
  return res.json()
}
