import { API_URL, AUTH_FETCH_TIMEOUT_MS, authHeaders, formatTransportError, fetchJson } from './config'

export const TOKEN_KEY = 'agro_os_token'
const USER_KEY = 'agro_os_user'
const AVATAR_PREFIX = 'agro_os_avatar_'
const MAX_AVATAR_BYTES = 500 * 1024

function avatarKey(email) {
  return `${AVATAR_PREFIX}${(email || '').toLowerCase()}`
}

export function getProfileAvatar(email) {
  if (!email) return null
  return localStorage.getItem(avatarKey(email))
}

export function storeProfileAvatar(email, dataUrl) {
  if (!email) return
  if (dataUrl) localStorage.setItem(avatarKey(email), dataUrl)
  else localStorage.removeItem(avatarKey(email))
}

export function clearProfileAvatar(email) {
  if (!email) return
  localStorage.removeItem(avatarKey(email))
}

export { MAX_AVATAR_BYTES }

export async function requestPasswordReset(email) {
  await fetchJson(`${API_URL}/auth/password-reset-request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
}

export async function confirmPasswordReset(resetToken, newPassword) {
  await fetchJson(`${API_URL}/auth/password-reset-confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
  })
}

export async function acceptInvite(inviteToken, password) {
  await fetchJson(`${API_URL}/auth/accept-invite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ invite_token: inviteToken, password }),
  })
}

export async function changePassword(accessToken, newPassword) {
  await fetchJson(`${API_URL}/auth/change-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ new_password: newPassword }),
  })
}

async function authFetch(path, body, { retries = 2 } = {}) {
  let lastError
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), AUTH_FETCH_TIMEOUT_MS)
    try {
      const response = await fetch(`${API_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Request failed (${response.status})`)
      }

      return response.json()
    } catch (err) {
      lastError = err
      const isRetryable = err?.name === 'AbortError' || err instanceof TypeError
      if (!isRetryable || attempt >= retries) break
    } finally {
      clearTimeout(timeoutId)
    }
  }
  throw new Error(formatTransportError(lastError))
}

export async function signupAdmin({
  email,
  password,
  cooperative_name,
  location,
  member_count,
  subscription_plan,
  onboarding_role,
  organization_type,
  checkout_ref,
  subscription_band,
}) {
  return authFetch('/auth/signup', {
    email,
    password,
    cooperative_name,
    location: location || null,
    member_count: member_count ?? null,
    subscription_plan: subscription_plan || 'starter',
    onboarding_role: onboarding_role || null,
    organization_type: organization_type || 'cooperative',
    checkout_ref: checkout_ref || null,
    subscription_band: subscription_band || null,
  }, { retries: 0 })
}

export async function loginAdmin(email, password) {
  return authFetch('/auth/login', { email, password })
}

export async function login(email, password) {
  return loginAdmin(email, password)
}

export async function signup({
  email,
  password,
  cooperativeName,
  location,
  memberCount,
  subscriptionPlan,
  onboardingRole,
  organizationType,
  checkoutRef,
  subscriptionBand,
}) {
  const data = await signupAdmin({
    email,
    password,
    cooperative_name: cooperativeName,
    location,
    member_count: memberCount ? parseInt(memberCount, 10) : null,
    subscription_plan: subscriptionPlan,
    onboarding_role: onboardingRole,
    organization_type: organizationType || 'cooperative',
    checkout_ref: checkoutRef,
    subscription_band: subscriptionBand,
  })
  return {
    ...data,
    user: userFromSignupResponse(data, email),
  }
}

export function userFromSignupResponse(data, email) {
  const resolvedEmail = data.user?.email || email?.trim() || ''
  return {
    id: data.user?.id ?? data.user_id ?? null,
    email: resolvedEmail,
    role: data.user?.role || 'admin',
    cooperative_id: data.cooperative_id ?? data.user?.cooperative_id ?? null,
    organization_id: data.user?.organization_id ?? null,
    cooperative: data.cooperative_name ?? null,
    organization_type: data.organization_type || 'cooperative',
  }
}

/**
 * Build the session user from a login/token response. Only values the API
 * actually returned are used; nothing is invented for display (#251).
 */
export function userFromLoginResponse(data, fallbackEmail = '') {
  const claims = userFromAuthToken(data?.access_token) || {}
  const apiUser = data?.user || {}
  return {
    ...claims,
    ...apiUser,
    email: apiUser.email || claims.email || fallbackEmail?.trim() || '',
    cooperative_id: apiUser.cooperative_id ?? claims.cooperative_id ?? null,
    organization_id: apiUser.organization_id ?? claims.organization_id ?? null,
    cooperative: data?.cooperative_name ?? null,
    organization_type: data?.organization_type || claims.organization_type || 'cooperative',
  }
}

/** Authoritative profile for the signed-in user (`GET /auth/me`). */
export async function fetchCurrentUser() {
  return fetchJson(`${API_URL}/auth/me`, { headers: authHeaders() })
}

export function userFromMeResponse(me) {
  if (!me) return null
  return {
    id: me.id ?? null,
    email: me.email,
    role: me.role,
    is_active: me.is_active,
    onboarding_role: me.onboarding_role ?? null,
    cooperative_id: me.cooperative_id ?? null,
    organization_id: me.organization_id ?? null,
    cooperative: me.cooperative_name ?? null,
    organization_type: me.organization_type || 'cooperative',
    password_change_required: Boolean(me.password_change_required),
  }
}

export async function register(email, password, cooperativeId = null) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, cooperative_id: cooperativeId }),
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Registration failed')
  }
  return response.json()
}

/** Wake Render/free-tier backends before login/signup (no-op if already warm). */
export async function warmAuthBackend() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), AUTH_FETCH_TIMEOUT_MS)
  try {
    await fetch(`${API_URL}/health`, { signal: controller.signal })
  } catch {
    // Best-effort; auth retry handles cold starts.
  } finally {
    clearTimeout(timeoutId)
  }
}

export function storeAuthToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function isAuthTokenUsable(token = getAuthToken()) {
  if (!token) return false
  try {
    const segment = token.split('.')[1]
    if (!segment) return false
    const payload = JSON.parse(decodeJwtPayloadSegment(segment))
    return typeof payload.exp === 'number' && payload.exp > Date.now() / 1000
  } catch {
    return false
  }
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function storeAuthUser(user) {
  if (!user) return
  const safe = { ...user }
  delete safe.password
  localStorage.setItem(USER_KEY, JSON.stringify(safe))
}

export function getAuthUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearAuthUser() {
  localStorage.removeItem(USER_KEY)
}

export function clearAuthSession() {
  clearAuthToken()
  clearAuthUser()
}

function decodeJwtPayloadSegment(segment) {
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  return atob(padded)
}

/**
 * Minimal session user from JWT claims only. This is a *bootstrap* value used
 * until `GET /auth/me` answers; it carries no display strings (no fake name or
 * cooperative), so nothing fabricated can reach the UI (#251).
 */
export function userFromAuthToken(token) {
  try {
    if (!token) return null
    const segment = token.split('.')[1]
    if (!segment) return null
    const payload = JSON.parse(decodeJwtPayloadSegment(segment))
    const email = payload.sub
    if (!email) return null
    return {
      id: payload.user_id ?? null,
      email,
      role: payload.role ?? null,
      cooperative_id: payload.cooperative_id ?? null,
      organization_id: payload.organization_id ?? null,
      cooperative: null,
      organization_type: payload.organization_type || 'cooperative',
    }
  } catch {
    return null
  }
}
