const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const FETCH_TIMEOUT_MS = 10000

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

export function authHeaders() {
  const token = getAuthToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
