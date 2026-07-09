const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

export async function signupAdmin({ name, email, password, cooperative_name }) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({ name, email, password, cooperative_name }),
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || 'Could not create account')
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
      throw new Error('Invalid email or password')
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export function storeAuthToken(token) {
  if (token) sessionStorage.setItem('agroos_token', token)
}

export function getAuthToken() {
  return sessionStorage.getItem('agroos_token')
}

export function clearAuthToken() {
  sessionStorage.removeItem('agroos_token')
}

const USER_KEY = 'agroos_user'

export function storeAuthUser(user) {
  if (!user) return
  const { password, ...safe } = user
  sessionStorage.setItem(USER_KEY, JSON.stringify(safe))
}

export function getAuthUser() {
  const raw = sessionStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearAuthUser() {
  sessionStorage.removeItem(USER_KEY)
}

export function clearAuthSession() {
  clearAuthToken()
  clearAuthUser()
}

/** Decode a JWT payload segment (base64url, possibly unpadded) to a UTF-8 string. */
function decodeJwtPayloadSegment(segment) {
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  return atob(padded)
}

/** Rebuild a minimal dashboard user when only a JWT is present (pre-persistence sessions). */
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
      cooperative: 'Kuapa Kokoo Demo Cooperative',
    }
  } catch {
    return null
  }
}

export function authHeaders() {
  const token = getAuthToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
