import { getAuthUser, storeAuthSession, storeAuthUser } from './auth'
import { API_URL, authHeaders, fetchJson } from './config'

/** The caller's organization with its cooperatives; rejects with 404 when none. */
export async function fetchMyOrganization() {
  return fetchJson(`${API_URL}/organizations/me`, { headers: authHeaders() })
}

/** Create an organization from the caller's cooperative (caller becomes org admin). */
export async function createOrganization(payload) {
  return fetchJson(`${API_URL}/organizations`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  })
}

export async function updateOrganization(organizationId, payload) {
  return fetchJson(`${API_URL}/organizations/${organizationId}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  })
}

/** Create a new cooperative inside the organization. */
export async function createOrganizationCooperative(organizationId, payload) {
  return fetchJson(`${API_URL}/organizations/${organizationId}/cooperatives`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  })
}

/** Consolidated billing across member cooperatives. */
export async function fetchOrganizationBilling(organizationId) {
  return fetchJson(`${API_URL}/organizations/${organizationId}/billing`, { headers: authHeaders() })
}

/**
 * Make another member cooperative the active scope. The API re-issues the
 * JWT; we persist it and the updated user so every subsequent request and
 * the cached user agree on the new scope.
 */
export async function switchOrganizationCooperative(organizationId, cooperativeId) {
  const token = await fetchJson(`${API_URL}/organizations/${organizationId}/switch`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ cooperative_id: cooperativeId }),
  })
  storeAuthSession(token)
  const current = getAuthUser() || {}
  storeAuthUser({
    ...current,
    ...(token.user || {}),
    cooperative_id: token.user?.cooperative_id ?? cooperativeId,
    organization_id: token.user?.organization_id ?? organizationId,
    organization_type: token.organization_type || current.organization_type,
  })
  return token
}
