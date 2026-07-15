import { API_URL, AUTH_FETCH_TIMEOUT_MS, formatTransportError } from './config'

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
}) {
  return authFetch('/auth/signup', {
    email,
    password,
    cooperative_name,
    location: location || null,
    member_count: member_count ?? null,
    subscription_plan: subscription_plan || 'starter',
    onboarding_role: onboarding_role || null,
  })
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
}) {
  const data = await signupAdmin({
    email,
    password,
    cooperative_name: cooperativeName,
    location,
    member_count: memberCount ? parseInt(memberCount, 10) : null,
    subscription_plan: subscriptionPlan,
    onboarding_role: onboardingRole,
  })
  return {
    ...data,
    user: userFromSignupResponse(data, email),
  }
}

export function userFromSignupResponse(data, email) {
  const cooperativeName = data.cooperative_name || 'My Cooperative'
  const resolvedEmail = data.user?.email || email?.trim() || ''
  const name = data.user?.name || 'Cooperative Admin'
  return {
    id: data.user?.id ?? data.user_id ?? null,
    email: resolvedEmail,
    name,
    initials: name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'CA',
    role: data.user?.role || 'admin',
    cooperative_id: data.cooperative_id ?? data.user?.cooperative_id ?? null,
    cooperative: cooperativeName,
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

export function userFromAuthToken(token) {
  try {
    const segment = token.split('.')[1]
    if (!segment) return null
    const payload = JSON.parse(decodeJwtPayloadSegment(segment))
    const email = payload.sub
    if (!email) return null
    return {
      email,
      name: 'Cooperative Admin',
      initials: 'CA',
      role: 'admin',
      cooperative_id: payload.cooperative_id ?? null,
      cooperative: 'Kuapa Kokoo Demo Cooperative',
    }
  } catch {
    return null
  }
}
