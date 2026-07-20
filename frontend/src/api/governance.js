import { API_URL, authHeaders, fetchJson } from './config'

export function fetchAdminAudit(limit = 100) {
  return fetchJson(`${API_URL}/admin/audit?limit=${limit}`, {
    headers: authHeaders(),
  })
}

export function fetchIntegrationHealth() {
  return fetchJson(`${API_URL}/admin/integration-health`, {
    headers: authHeaders(),
  })
}

export function fetchCooperativeUsers(cooperativeId) {
  const query = cooperativeId ? `?cooperative_id=${cooperativeId}` : ''
  return fetchJson(`${API_URL}/auth/users${query}`, {
    headers: authHeaders(),
  })
}

export function registerCooperativeUser(payload) {
  return fetchJson(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  })
}

export function updateCooperativeUser(userId, payload) {
  return fetchJson(`${API_URL}/auth/users/${userId}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  })
}
