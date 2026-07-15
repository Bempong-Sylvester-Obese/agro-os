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

export function fetchCooperativeUsers() {
  return fetchJson(`${API_URL}/auth/users`, {
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
