import { API_URL, apiFetch, authHeaders, fetchJson } from './config'

/**
 * Fetch a cooperative by ID. Returns null on any error.
 */
export async function fetchCooperative(cooperativeId) {
  if (!cooperativeId) return null
  const res = await apiFetch(`${API_URL}/cooperatives/${cooperativeId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) return null
  return res.json()
}

/**
 * Usage vs plan limits for the dashboard (members, workers, SMS) and the
 * feature flags of the *effective* plan. Throws ApiError on failure.
 */
export async function fetchCooperativeUsage(cooperativeId) {
  return fetchJson(`${API_URL}/cooperatives/${cooperativeId}/usage`, {
    headers: authHeaders(),
  })
}

export async function updateCooperative(cooperativeId, data) {
  const res = await apiFetch(`${API_URL}/cooperatives/${cooperativeId}`, {
    method: 'PUT',
    headers: authHeaders(true),
    body: JSON.stringify(data)
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to update cooperative')
  }
  return res.json()
}

export async function provisionWallet(cooperativeId) {
  const res = await apiFetch(`${API_URL}/cooperatives/${cooperativeId}/wallet/provision`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to provision wallet')
  }
  return res.json()
}

export async function createSubscriptionCheckout(cooperativeId, planKey, band = null) {
  const res = await apiFetch(`${API_URL}/subscriptions/checkout`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      cooperative_id: cooperativeId,
      plan_key: planKey,
      band,
    })
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to generate checkout link')
  }
  return res.json()
}

/** Lifecycle view: status, effective plan, days remaining (applies pending transitions). */
export async function fetchSubscriptionStatus(cooperativeId) {
  return fetchJson(`${API_URL}/subscriptions/status?cooperative_id=${cooperativeId}`, {
    headers: authHeaders(),
  })
}

/** Payment history built from subscription intents (admin). */
export async function fetchSubscriptionHistory(cooperativeId) {
  return fetchJson(`${API_URL}/subscriptions/history?cooperative_id=${cooperativeId}`, {
    headers: authHeaders(),
  })
}

function lifecycleAction(path) {
  return (cooperativeId, extra = {}) =>
    fetchJson(`${API_URL}/subscriptions/${path}`, {
      method: 'POST',
      headers: authHeaders(true),
      body: JSON.stringify({ cooperative_id: cooperativeId, ...extra }),
    })
}

/** Create a renewal payment intent for the plan on record; returns `{authorization_url, ...}`. */
export const renewSubscription = lifecycleAction('renew')
/** Cancel at period end (default) or immediately: `cancelSubscription(id, { immediately: true })`. */
export const cancelSubscription = lifecycleAction('cancel')
/** Undo a pending cancellation before the period ends. */
export const resumeSubscription = lifecycleAction('resume')

export { createPreCheckout } from './plans'
