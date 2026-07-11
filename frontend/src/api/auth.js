const API_URL = import.meta.env.VITE_API_URL || 'https://previewbackendagro-os.onrender.com'
const FETCH_TIMEOUT_MS = 10000
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

export async function signupAdmin({ email, password, cooperative_name, location, member_count }) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        email,
        password,
        cooperative_name,
        location: location || null,
        member_count: member_count ?? null,
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Could not create account')
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function loginAdmin(email, password) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Invalid email or password')
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function login(email, password) {
  return loginAdmin(email, password)
}

export async function signup({ email, password, cooperativeName, location, memberCount }) {
  return signupAdmin({
    email,
    password,
    cooperative_name: cooperativeName,
    location,
    member_count: memberCount ? parseInt(memberCount, 10) : null,
  })
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

export function storeAuthToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function storeAuthUser(user) {
  if (!user) return
  const { password, ...safe } = user
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
      role: 'Finance Officer',
      cooperative_id: payload.cooperative_id ?? null,
      cooperative: 'Kuapa Kokoo Demo Cooperative',
    }
  } catch {
    return null
  }
}

